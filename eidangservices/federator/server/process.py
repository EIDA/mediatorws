# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <process.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-federator)
#
# eida-federator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# eida-federator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----
#
# Copyright (c) Daniel Armbruster (ETH), Fabian Euchner (ETH)
#
# REVISION AND CHANGES
# 2018/03/29        V0.1    Daniel Armbruster
# =============================================================================
"""
federator processing facilities
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import collections
import datetime
import logging
import multiprocessing as mp
import os
import time

from flask import current_app, stream_with_context, Response

from eidangservices import utils, settings
from eidangservices.federator.server.request import (
    binary_request, RoutingRequestHandler, GranularFdsnRequestHandler,
    NoContent, RequestsError)
from eidangservices.federator.server.task import (
    RawDownloadTask, RawSplitAndAlignTask, StationTextDownloadTask,
    StationXMLNetworkCombinerTask, WFCatalogSplitAndAlignTask)
from eidangservices.utils.error import ErrorWithTraceback
from eidangservices.utils.httperrors import FDSNHTTPError
from eidangservices.utils.sncl import StreamEpoch


# TODO(damb): This is a note regarding the federator-registered mode.
# Processors using exclusively DownloadTask objects must perform a detailed
# logging to the log DB. Processors using Combiners delegate logging to the
# corresponding combiner tasks.

def demux_routes(routes):
    return [utils.Route(route.url, streams=[se]) for route in routes
            for se in route.streams]

# demux_routes ()

def group_routes_by(routes, key='network'):
    """
    Group routes by a certain :cls:`eidangservices.sncl.Stream` keyword.
    Combined keywords are also possible e.g. network.station. When combining
    keys the seperating character is `.`. Routes are demultiplexed.

    :param list routes: List of :cls:`eidangservices.utils.Route` objects
    :param str key: Key used for grouping.
    """
    SEP = '.'

    routes = demux_routes(routes)
    retval = collections.defaultdict(list)

    for route in routes:
        try:
            _key = getattr(route.streams[0].stream, key)
        except AttributeError as err:
            try:
                if SEP in key:
                    # combined key
                    _key = SEP.join(getattr(route.streams[0].stream, k)
                                    for k in key.split(SEP))
                else:
                    raise KeyError(
                        'Invalid separator. Must be {!r}.'.format(SEP))
            except (AttributeError, KeyError) as err:
                raise RequestProcessorError(err)

        retval[_key].append(route)

    return retval

# group_routes_by ()

def flatten_routes(grouped_routes):
    return [route for routes in grouped_routes.values() for route in routes]


class RequestProcessorError(ErrorWithTraceback):
    """Base RequestProcessor error ({})."""

class StreamingError(RequestProcessorError):
    """Error while streaming ({})."""

# -----------------------------------------------------------------------------
class RequestProcessor(object):
    """
    Abstract base class for request processors.
    """

    LOGGER = "flask.app.federator.request_processor"

    POOL_SIZE = 5
    # MAX_TASKS_PER_CHILD = 4
    DEFAULT_ENDTIME = datetime.datetime.utcnow()
    TIMEOUT_STREAMING = settings.EIDA_FEDERATOR_STREAMING_TIMEOUT

    def __init__(self, mimetype, query_params={}, stream_epochs=[], post=True,
                 **kwargs):
        self.mimetype = mimetype
        self.query_params = query_params
        self.stream_epochs = stream_epochs
        self.post = post

        self._routing_service = current_app.config['ROUTING_SERVICE']

        self.logger = logging.getLogger(
            self.LOGGER if kwargs.get('logger') is None
            else kwargs.get('logger'))

        self._pool = None
        self._results = []
        self._sizes = []

    # __init__ ()

    @staticmethod
    def create(service, *args, **kwargs):
        """Factory method for RequestProcessor object instances.

        :param str service: Service identifier.
        :param dict kwargs: A dictionary passed to the combiner constructors.
        :return: A concrete :cls:`RequestProcessor` implementation
        :rtype: :cls:`RequestProcessor`
        :raises KeyError: if an invalid format string was passed
        """
        if service == 'dataselect':
            return RawRequestProcessor(*args, **kwargs)
        elif service == 'station':
            return StationRequestProcessor.create(
                kwargs['query_params'].get('format', 'xml'), *args, **kwargs)
        elif service == 'wfcatalog':
            return WFCatalogRequestProcessor(*args, **kwargs)
        else:
            raise KeyError('Invalid RequestProcessor chosen.')

    # create ()

    def _route(self):
        """
        Create the routing table using the routing service provided.
        """
        routing_request = RoutingRequestHandler(
            self._routing_service, self.query_params,
            self.stream_epochs)

        req = (routing_request.post() if self.post else routing_request.get())
        self.logger.info("Fetching routes from %s" % routing_request.url)

        routing_table = []

        try:
            with binary_request(req) as fd:
                # parse the routing service's output stream; create a routing
                # table
                urlline = None
                stream_epochs = []

                while True:
                    line = fd.readline()

                    if not urlline:
                        urlline = line.strip()
                    elif not line.strip():
                        # set up the routing table
                        if stream_epochs:
                            routing_table.append(
                                utils.Route(url=urlline,
                                            streams=stream_epochs))
                        urlline = None
                        stream_epochs = []

                        if not line:
                            break
                    else:
                        stream_epochs.append(
                            StreamEpoch.from_snclline(
                                line, default_endtime=self.DEFAULT_ENDTIME))

        except NoContent as err:
            self.logger.warning(err)
            raise FDSNHTTPError.create(
                int(self.query_params.get(
                    'nodata',
                    settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE)))
        except RequestsError as err:
            self.logger.error(err)
            raise FDSNHTTPError.create(
                500, service_id=settings.EIDA_FEDERATOR_SERVICE_ID)

        return routing_table

    # _route ()

    @property
    def streamed_response(self):
        """
        Return a streamed :cls:`flask.Response`.
        """
        self._request()

        # XXX(damb): Only return a streamed response as soon as valid data
        # is available. Use a timeout and process errors here.
        self._wait()

        return Response(stream_with_context(self), mimetype=self.mimetype,
                        content_type=self.mimetype)

    # streamed_response ()

    def _handle_error(self, err):
        self.logger.warning(str(err))

    def _handle_413(self, result):
        self.logger.warning(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        raise FDSNHTTPError.create(
            413, service_id=settings.EIDA_FEDERATOR_SERVICE_ID)

    # _handle_413 ()

    def _wait(self, timeout=None):
        """
        Wait for a valid endpoint response.

        :param int timeout: Timeout in seconds
        """
        if timeout is None:
            timeout = self.TIMEOUT_STREAMING

        result_with_data = False
        while True:
            ready = []
            for result in self._results:
                if result.ready():
                    _result = result.get()
                    if _result.status_code == 200:
                        result_with_data = True
                    elif _result.status_code == 413:
                        self._handle_413(_result)
                        ready.append(result)
                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)
                        ready.append(result)

                # NOTE(damb): We have to handle responses > 5MB. Blocking the
                # processor by means of time.sleep makes executing
                # *DownloadTasks IO bound.
                time.sleep(0.01)

            for result in ready:
                self._results.remove(result)

            if result_with_data:
                break

            if (not self._results or datetime.datetime.utcnow() >
                self.DEFAULT_ENDTIME +
                    datetime.timedelta(seconds=timeout)):
                raise FDSNHTTPError.create(
                    int(self.query_params.get(
                        'nodata',
                        settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE)))

    # _wait ()

    def _request(self):
        """
        Template method.
        """
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

# class RequestProcessor


class RawRequestProcessor(RequestProcessor):
    """
    Federating request processor implementation controlling both the federated
    downloading process and the merging afterwards.
    """

    LOGGER = "flask.app.federator.request_processor_raw"

    POOL_SIZE = settings.EIDA_FEDERATOR_THREADS_DATASELECT
    CHUNK_SIZE = 1024

    def _request(self):
        """
        process a federated request
        """
        routes = self._route()
        self.logger.debug('Received routes: {}'.format(routes))
        routes = demux_routes(routes)

        pool_size = (len(routes) if
                     len(routes) < self.POOL_SIZE else self.POOL_SIZE)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)
        # NOTE(damb): With pleasure I'd like to define the parameter
        # maxtasksperchild=self.MAX_TASKS_PER_CHILD)
        # However, using this parameter seems to lead to processes unexpectedly
        # terminated. Hence some tasks never return a *ready* result.

        for route in routes:
            self.logger.debug(
                'Creating DownloadTask for {!r} ...'.format(
                    route))
            t = RawDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params))
            result = self._pool.apply_async(t)
            self._results.append(result)

    # _request ()

    def _handle_413(self, result):
        self.logger.info(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        self.logger.debug(
            'Creating SAATask for (url={}, '
            'stream_epochs={}) ...'.format(result.data.url,
                                           result.data.stream_epochs))
        t = RawSplitAndAlignTask(
            result.data.url, result.data.stream_epochs[0],
            query_params=self.query_params,
            endtime=self.DEFAULT_ENDTIME)

        result = self._pool.apply_async(t)
        self._results.append(result)

    # _handle_413 ()

    def __iter__(self):
        """
        Make the processor *streamable*.
        """
        # TODO(damb): The processor has to write metadata to the log database.
        # Also in case of errors.

        def generate_chunks(fd, chunk_size=self.CHUNK_SIZE):
            while True:
                data = fd.read(chunk_size)
                if not data:
                    break
                yield data

        while True:

            ready = []
            for result in self._results:

                if result.ready():
                    _result = result.get()

                    if _result.status_code == 200:
                        self._sizes.append(_result.length)
                        self.logger.debug(
                            'Streaming from file {!r} (chunk_size={}).'.format(
                                _result.data, self.CHUNK_SIZE))
                        try:
                            with open(_result.data, 'rb') as fd:
                                for chunk in generate_chunks(fd):
                                    yield chunk
                        except Exception as err:
                            raise StreamingError(err)

                        self.logger.debug(
                            'Removing temporary file {!r} ...'.format(
                                _result.data))
                        try:
                            os.remove(_result.data)
                        except OSError as err:
                            RequestProcessorError(err)

                    elif _result.status_code == 413:
                        self._handle_413(_result)

                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)

                    ready.append(result)

                # NOTE(damb): We have to handle responses > 5MB. Blocking the
                # processor by means of time.sleep makes executing
                # *DownloadTasks IO bound.
                time.sleep(0.01)

            # TODO(damb): Implement a timeout solution in case results are
            # never ready.
            for result in ready:
                self._results.remove(result)

            if not self._results:
                break

        self._pool.close()
        self._pool.join()
        self.logger.debug('Result sizes: {}.'.format(self._sizes))
        self.logger.info(
            'Results successfully processed (Total bytes: {}).'.format(
                sum(self._sizes)))

    # __iter__ ()

# class RawRequestProcessor


class StationRequestProcessor(RequestProcessor):
    """
    Base class for federating fdsnws.station request processor. While routing
    this processor interprets the `level` query parameter in order to reduce
    the number of endpoint requests.

    StationRequestProcessor implementations come along with a *reducing*
    `_route ()` implementation. Routes received from the *StationLite*
    webservice are reduced depending on the value of the `level` query
    parameter.
    """

    LOGGER = "flask.app.federator.request_processor_station"

    def __init__(self, mimetype, query_params={}, stream_epochs=[], post=True,
                 **kwargs):
        super().__init__(mimetype, query_params, stream_epochs, post, **kwargs)

        self._level = query_params.get('level')
        if self._level is None:
            raise RequestProcessorError("Missing parameter: 'level'.")

    # __init__ ()

    @staticmethod
    def create(response_format, *args, **kwargs):
        if response_format == 'xml':
            return StationXMLRequestProcessor(*args, **kwargs)
        elif response_format == 'text':
            return StationTextRequestProcessor(*args, **kwargs)
        else:
            raise KeyError('Invalid RequestProcessor chosen.')

    # create ()

    def _route(self):
        routes = super()._route()
        self.logger.debug('Received routes: {}'.format(routes))
        # group routes
        return group_routes_by(routes, key='network')

    # _route ()

# class StationRequestProcessor


class StationXMLRequestProcessor(StationRequestProcessor):
    """
    This processor implementation implements fdsnws-station XML federatation
    using a two-level approach.

    This processor implementation implements federatation using a two-level
    approach.
    On the first level the processor maintains a worker pool (implemented by
    means of the python multiprocessing module). Special *CombiningTask* object
    instances are mapped to the pool managing the download for a certain
    network code.
    On a second level RawCombinerTask implementations demultiplex the routing
    information, again. Multiple DownloadTask object instances (implemented
    using multiprocessing.pool.ThreadPool) are executed requesting granular
    stream epoch information (i.e. one task per fully resolved stream
    epoch).
    Combining tasks collect the information from their child downloading
    threads. As soon the information for an entire network code is fetched the
    resulting data is combined and temporarly saved. Finally
    StationRequestProcessor implementations merge the final result.
    """
    CHUNK_SIZE = 1024

    SOURCE = 'EIDA'
    HEADER = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1" '
              'schemaVersion="1.0">'
              '<Source>{}</Source>'
              '<Created>{}</Created>')
    FOOTER = '</FDSNStationXML>'

    def _request(self):
        """
        Process a federated fdsnws-station XML request.
        """
        routes = self._route()

        pool_size = (len(routes) if
                     len(routes) < self.POOL_SIZE else self.POOL_SIZE)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.Pool(processes=pool_size)
        # NOTE(damb): With pleasure I'd like to define the parameter
        # maxtasksperchild=self.MAX_TASKS_PER_CHILD)
        # However, using this parameter seems to lead to processes unexpectedly
        # terminated. Hence some tasks never return a *ready* result.

        for net, routes in routes.items():
            self.logger.debug(
                'Creating CombinerTask for {!r} ...'.format(net))
            t = StationXMLNetworkCombinerTask(
                routes, self.query_params, name=net)
            result = self._pool.apply_async(t)
            self._results.append(result)

        self._pool.close()

    # _request ()

    def __iter__(self):
        """
        Make the processor *streamable*.
        """
        def generate_chunks(fd, chunk_size=self.CHUNK_SIZE):
            while True:
                data = fd.read(chunk_size)
                if not data:
                    break
                yield data

        while True:
            ready = []
            for result in self._results:
                if result.ready():

                    _result = result.get()
                    if _result.status_code == 200:
                        if not sum(self._sizes):
                            yield self.HEADER.format(
                                self.SOURCE,
                                datetime.datetime.utcnow().isoformat())

                        self._sizes.append(_result.length)
                        self.logger.debug(
                            'Streaming from file {!r} (chunk_size={}).'.format(
                                _result.data, self.CHUNK_SIZE))
                        try:
                            with open(_result.data, 'r', encoding='utf-8') \
                                    as fd:
                                for chunk in generate_chunks(fd):
                                    yield chunk
                        except Exception as err:
                            raise StreamingError(err)

                        self.logger.debug(
                            'Removing temporary file {!r} ...'.format(
                                _result.data))
                        try:
                            os.remove(_result.data)
                        except OSError as err:
                            RequestProcessorError(err)

                    elif _result.status_code == 413:
                        self._handle_413(_result)

                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)

                    ready.append(result)

            # TODO(damb): Implement a timeout solution in case results are
            # never ready.
            for result in ready:
                self._results.remove(result)

            if not self._results:
                break

        yield self.FOOTER

        self._pool.join()
        self.logger.debug('Result sizes: {}.'.format(self._sizes))
        self.logger.info(
            'Results successfully processed (Total bytes: {}).'.format(
                sum(self._sizes) + len(self.HEADER) - 4 + len(self.SOURCE) +
                len(datetime.datetime.utcnow().isoformat()) +
                len(self.FOOTER)))

    # __iter__ ()

# class StationXMLRequestProcessor


class StationTextRequestProcessor(StationRequestProcessor):
    """
    This processor implementation implements fdsnws-station text federatation.
    Data is fetched multithreaded from endpoints.
    """
    POOL_SIZE = settings.EIDA_FEDERATOR_THREADS_STATION_TEXT

    HEADER_NETWORK = '#Network|Description|StartTime|EndTime|TotalStations'
    HEADER_STATION = (
        '#Network|Station|Latitude|Longitude|'
        'Elevation|SiteName|StartTime|EndTime')
    HEADER_CHANNEL = (
        '#Network|Station|Location|Channel|Latitude|'
        'Longitude|Elevation|Depth|Azimuth|Dip|SensorDescription|Scale|'
        'ScaleFreq|ScaleUnits|SampleRate|StartTime|EndTime')

    def _request(self):
        """
        Process a federated fdsnws-station text request
        """
        routes = flatten_routes(self._route())

        pool_size = (len(routes) if
                     len(routes) < self.POOL_SIZE else self.POOL_SIZE)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)

        for route in routes:
            self.logger.debug(
                'Creating DownloadTask for {!r} ...'.format(
                    route))
            t = StationTextDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params))
            result = self._pool.apply_async(t)
            self._results.append(result)

        self._pool.close()

    # _request ()

    def __iter__(self):
        """
        Make the processor *streamable*.
        """
        while True:
            ready = []
            for result in self._results:
                if result.ready():

                    _result = result.get()
                    if _result.status_code == 200:
                        if not sum(self._sizes):
                            # add header
                            if self._level == 'network':
                                yield '{}\n'.format(self.HEADER_NETWORK)
                            elif self._level == 'station':
                                yield '{}\n'.format(self.HEADER_STATION)
                            elif self._level == 'channel':
                                yield '{}\n'.format(self.HEADER_CHANNEL)

                        self._sizes.append(_result.length)
                        self.logger.debug(
                            'Streaming from file {!r}.'.format(_result.data))
                        try:
                            with open(_result.data, 'r', encoding='utf-8') \
                                    as fd:
                                for line in fd:
                                    yield line
                        except Exception as err:
                            raise StreamingError(err)

                        self.logger.debug(
                            'Removing temporary file {!r} ...'.format(
                                _result.data))
                        try:
                            os.remove(_result.data)
                        except OSError as err:
                            RequestProcessorError(err)

                    elif _result.status_code == 413:
                        self._handle_413(_result)

                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)

                    ready.append(result)

            # TODO(damb): Implement a timeout solution in case results are
            # never ready.
            for result in ready:
                self._results.remove(result)

            if not self._results:
                break

        self._pool.join()
        self.logger.debug('Result sizes: {}.'.format(self._sizes))
        self.logger.info(
            'Results successfully processed (Total bytes: {}).'.format(
                sum(self._sizes)))

    # __iter__ ()

# class StationTextRequestProcessor


class WFCatalogRequestProcessor(RequestProcessor):
    """
    Process a WFCatalog request.
    """
    LOGGER = "flask.app.federator.request_processor_wfcatalog"

    POOL_SIZE = settings.EIDA_FEDERATOR_THREADS_WFCATALOG
    CHUNK_SIZE = 1024

    JSON_LIST_START = '['
    JSON_LIST_END = ']'
    JSON_LIST_SEP = ','

    def _request(self):
        """
        process a federated fdsnws-station text request
        """
        routes = self._route()
        self.logger.debug('Received routes: {}'.format(routes))
        routes = demux_routes(routes)

        pool_size = (len(routes) if
                     len(routes) < self.POOL_SIZE else self.POOL_SIZE)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)
        # NOTE(damb): With pleasure I'd like to define the parameter
        # maxtasksperchild=self.MAX_TASKS_PER_CHILD)
        # However, using this parameter seems to lead to processes unexpectedly
        # terminated. Hence some tasks never return a *ready* result.

        for route in routes:
            self.logger.debug(
                'Creating DownloadTask for {!r} ...'.format(
                    route))
            t = RawDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params))
            result = self._pool.apply_async(t)
            self._results.append(result)

    # _request ()

    def _handle_413(self, result):
        self.logger.info(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        self.logger.debug(
            'Creating SAATask for (url={}, '
            'stream_epochs={}) ...'.format(result.data.url,
                                           result.data.stream_epochs))
        t = WFCatalogSplitAndAlignTask(
            result.data.url, result.data.stream_epochs[0],
            query_params=self.query_params,
            endtime=self.DEFAULT_ENDTIME)

        result = self._pool.apply_async(t)
        self._results.append(result)

    # _handle_413 ()

    def __iter__(self):
        """
        Make the processor *streamable*.
        """
        def generate_chunks(fd, chunk_size=self.CHUNK_SIZE):
            _size = os.fstat(fd.fileno()).st_size
            # skip leading bracket (from JSON list)
            fd.seek(1)
            while True:
                buf = fd.read(chunk_size)
                if not buf:
                    break

                if fd.tell() == _size:
                    # skip trailing bracket (from JSON list)
                    buf = buf[:-1]

                yield buf

        while True:
            ready = []
            for result in self._results:
                if result.ready():
                    _result = result.get()
                    if _result.status_code == 200:
                        if not sum(self._sizes):
                            # add header
                            yield self.JSON_LIST_START

                        self.logger.debug(
                            'Streaming from file {!r} (chunk_size={}).'.format(
                                _result.data, self.CHUNK_SIZE))
                        try:
                            with open(_result.data, 'rb') as fd:
                                # skip leading bracket (from JSON list)
                                size = 0
                                for chunk in generate_chunks(fd,
                                                             self.CHUNK_SIZE):
                                    size += len(chunk)
                                    yield chunk

                            self._sizes.append(size)

                        except Exception as err:
                            raise StreamingError(err)

                        if len(self._results) > 1:
                            # append comma if not last stream epoch data
                            yield self.JSON_LIST_SEP

                        self.logger.debug(
                            'Removing temporary file {!r} ...'.format(
                                _result.data))
                        try:
                            os.remove(_result.data)
                        except OSError as err:
                            RequestProcessorError(err)

                    elif _result.status_code == 413:
                        self._handle_413(_result)

                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)

                    ready.append(result)

                # NOTE(damb): We have to handle responses > 5MB. Blocking the
                # processor by means of time.sleep makes executing
                # *DownloadTasks IO bound.
                time.sleep(0.01)

            # TODO(damb): Implement a timeout solution in case results are
            # never ready.
            for result in ready:
                self._results.remove(result)

            if not self._results:
                break

        yield self.JSON_LIST_END

        self._pool.close()
        self._pool.join()
        self.logger.debug('Result sizes: {}.'.format(self._sizes))
        self.logger.info(
            'Results successfully processed (Total bytes: {}).'.format(
                sum(self._sizes) + 2 + len(self._sizes)-1))

    # __iter__ ()

# class WFCatalogRequestProcessor


# ---- END OF <process.py> ----
