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
import uuid

from flask import current_app, stream_with_context, Response

from eidangservices import utils, settings
from eidangservices.federator import __version__
from eidangservices.federator.server.misc import (
    Context, ContextLoggerAdapter, KeepTempfiles)
from eidangservices.federator.server.request import (
    RoutingRequestHandler, GranularFdsnRequestHandler,
    BulkFdsnRequestHandler)
from eidangservices.federator.server.task import (
    ETask, RawDownloadTask, RawSplitAndAlignTask, StationTextDownloadTask,
    StationXMLDownloadTask, StationXMLNetworkCombinerTask,
    WFCatalogSplitAndAlignTask)
from eidangservices.utils.error import ErrorWithTraceback
from eidangservices.utils.httperrors import FDSNHTTPError
from eidangservices.utils.request import (binary_request, RequestsError,
                                          NoContent)
from eidangservices.utils.sncl import StreamEpoch


# TODO(damb): This is a note regarding the federator-registered mode.
# Processors using exclusively DownloadTask objects must perform a detailed
# logging to the log DB. Processors using Combiners delegate logging to the
# corresponding combiner tasks.
# For bulk requests no detailed logging can be provided.

def demux_routes(routes):
    return [utils.Route(route.url, streams=[se]) for route in routes
            for se in route.streams]

# demux_routes ()

def group_routes_by(routes, key='network'):
    """
    Group routes by a certain :py:class:`eidangservices.sncl.Stream` keyword.
    Combined keywords are also possible e.g. network.station. When combining
    keys the seperating character is `.`. Routes are demultiplexed.

    :param list routes: List of :py:class:`eidangservices.utils.Route` objects
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


class RequestProcessorError(ErrorWithTraceback):
    """Base RequestProcessor error ({})."""

class RoutingError(RequestProcessorError):
    """Error while routing ({})."""

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
    TIMEOUT_STREAMING = settings.EIDA_FEDERATOR_STREAMING_TIMEOUT

    def __init__(self, mimetype, query_params={}, stream_epochs=[], post=True,
                 **kwargs):
        self.mimetype = mimetype
        self.content_type = (
            '{}; {}'.format(self.mimetype, settings.CHARSET_TEXT)
            if self.mimetype == settings.MIMETYPE_TEXT else self.mimetype)
        self.query_params = query_params
        self.stream_epochs = stream_epochs
        self.post = post

        # TODO(damb): Pass as ctor arg.
        self._routing_service = current_app.config['ROUTING_SERVICE']

        self._logger = logging.getLogger(
            self.LOGGER if kwargs.get('logger') is None
            else kwargs.get('logger'))

        self._ctx = kwargs.get('context', Context(uuid.uuid4()))
        if not self._ctx.locked:
            self._ctx.acquire()

        self.logger = ContextLoggerAdapter(self._logger, {'ctx': self._ctx})

        self._keep_tempfiles = kwargs.get('keep_tempfiles', KeepTempfiles.NONE)

        self._pool = None
        self._results = []
        self._sizes = []

        self._default_endtime = datetime.datetime.utcnow()

    # __init__ ()

    @staticmethod
    def create(service, *args, **kwargs):
        """Factory method for RequestProcessor object instances.

        :param str service: Service identifier.
        :param dict kwargs: A dictionary passed to the combiner constructors.
        :return: A concrete :py:class:`RequestProcessor` implementation
        :rtype: :py:class:`RequestProcessor`
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

    @property
    def DEFAULT_ENDTIME(self):
        return self._default_endtime

    @property
    def streamed_response(self):
        """
        Return a streamed :py:class:`flask.Response`.
        """
        self._request()

        # XXX(damb): Only return a streamed response as soon as valid data
        # is available. Use a timeout and process errors here.
        self._wait()

        resp = Response(stream_with_context(self), mimetype=self.mimetype,
                        content_type=self.content_type)

        resp.call_on_close(self._call_on_close)

        return resp

    # streamed_response ()

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
            raise FDSNHTTPError.create(500, service_version=__version__)
        else:
            self.logger.debug(
                'Number of routes received: {}'.format(len(routing_table)))

        return routing_table

    # _route ()

    def _handle_error(self, err):
        self.logger.warning(str(err))

        if self._keep_tempfiles not in (KeepTempfiles.ALL,
                                        KeepTempfiles.ON_ERRORS):
            try:
                os.remove(err.data)
            except OSError as err:
                pass

    # _handle_error ()

    def _handle_413(self, result):
        self.logger.warning(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        raise FDSNHTTPError.create(413, service_version=__version__)

    # _handle_413 ()

    def _handle_teapot(self, result):
        self.logger.debug('Teapot: {}'.format(result))

    # _handle_teapot ()

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
                        break
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
                self.logger.warning(
                    'No valid results to be federated. ({})'.format(
                        ('No valid results.' if not self._results else
                         'Timeout ({}).'.format(timeout))))
                raise FDSNHTTPError.create(
                    int(self.query_params.get(
                        'nodata',
                        settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE)))

    # _wait ()

    def _terminate(self):
        """
        Terminate the processor.

        Implies both shutting down the processor's pool and removing temporary
        files of already successfully returned tasks.
        """
        try:
            self._ctx.release()
        except (AttributeError, ErrorWithTraceback):
            pass
        self._pool.terminate()
        self._pool.join()

        if (self._keep_tempfiles not in (KeepTempfiles.ALL,
                                         KeepTempfiles.ON_ERRORS)):
            for result in self._results:
                if result.ready():
                    _result = result.get()
                    try:
                        os.remove(_result.data)
                    except (TypeError, OSError) as err:
                        pass

        self._pool = None

    # _terminate ()

    def _request(self):
        """
        Template method.
        """
        raise NotImplementedError

    def _call_on_close(self):
        """
        Template method which will be called when :py:class:`flask.Response` is
        closed. By default pending tasks are terminated.

        When using `mod_wsgi <http://modwsgi.readthedocs.io/en/latest/>`_ the
        method is called either in case the request successfully was responded
        or an exception occurred while sending the response. `Graham Dumpleton
        <https://github.com/GrahamDumpleton>`_ describes the situation in this
        `thread post:
        <https://groups.google.com/forum/#!topic/modwsgi/jr2ayp0xesk>`_ very
        detailed.
        """
        self.logger.debug("Finalize response (closing) ...")

        try:
            self._pool.terminate()
            self._pool.join()
        except AttributeError:
            pass

        self._pool = None

    # _call_on_close ()

    def __iter__(self):
        raise NotImplementedError

# class RequestProcessor


class RawRequestProcessor(RequestProcessor):
    """
    Federating request processor implementation controlling both the federated
    downloading process and the merging afterwards.
    """

    LOGGER = "flask.app.federator.request_processor_raw"

    CHUNK_SIZE = 1024

    @property
    def POOL_SIZE(self):
        return current_app.config['FED_THREAD_CONFIG']['fdsnws-dataselect']

    def _request(self):
        """
        process a federated request
        """
        routes = demux_routes(self._route())

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
            ctx = Context(root_only=True)
            self._ctx.append(ctx)
            t = RawDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params),
                context=ctx,
                keep_tempfiles=self._keep_tempfiles,)
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
        ctx = Context(root_only=True)
        self._ctx.append(ctx)

        t = RawSplitAndAlignTask(
            result.data.url, result.data.stream_epochs[0],
            query_params=self.query_params,
            endtime=self.DEFAULT_ENDTIME,
            context=ctx,
            keep_tempfiles=self._keep_tempfiles)

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

        try:
            while True:

                ready = []
                for result in self._results:

                    if result.ready():
                        _result = result.get()

                        if _result.status_code == 200:
                            self._sizes.append(_result.length)
                            self.logger.debug(
                                'Streaming from file {!r} (chunk_size={}).'.\
                                format(_result.data, self.CHUNK_SIZE))
                            try:
                                with open(_result.data, 'rb') as fd:
                                    for chunk in generate_chunks(fd):
                                        yield chunk
                            except Exception as err:
                                raise StreamingError(err)

                            if self._keep_tempfiles != KeepTempfiles.ALL:
                                self.logger.debug(
                                    'Removing temporary file {!r} ...'.format(
                                        _result.data))
                                try:
                                    os.remove(_result.data)
                                except OSError as err:
                                    RequestProcessorError(err)

                        elif _result.status_code == 413:
                            # TODO TODO TODO
                            # Check if file has to be removed
                            self._handle_413(_result)

                        else:
                            self._handle_error(_result)
                            self._sizes.append(0)

                        ready.append(result)

                    # NOTE(damb): We have to handle responses > 5MB. Blocking
                    # the processor by means of time.sleep makes executing
                    # *DownloadTasks* IO bound.
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
        except GeneratorExit as err:
            self.logger.debug('GeneratorExit: Terminate ...')
            self._terminate()

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
        """
        Multiplexed routing i.e. one route contains multiple stream epochs
        (for a unique network code). Allows bulk requests based on network
        codes.
        """
        # NOTE(damb): We group routes by network code, first. This later will
        # enable us to easier provide station metadata combination for
        # distributed physical networks. However, currently we exclusively
        # combine station-xml. For station-text we issue still granular
        # download tasks.
        # Afterwards, grouped routes are multiplex by network code, again.

        retval = collections.defaultdict(list)
        for net, _routes in group_routes_by(
                super()._route(), key='network').items():
            # sort by url
            mux_routes = collections.defaultdict(list)
            for r in _routes:
                mux_routes[r.url].append(r.streams[0])

            for url, ses in mux_routes.items():
                retval[net].append(utils.Route(url=url, streams=ses))

        return retval

    # _route ()

# class StationRequestProcessor


class StationXMLRequestProcessor(StationRequestProcessor):
    """
    `StationXML <http://www.fdsn.org/xml/station/>`_ federation processor.

    For networks located at a single endpoint simple bulk requests are send to
    the endpoint. Besides, for distributed physical networks this processor
    federates StationXML using a two-level approach:

    * On the first level the processor maintains a worker pool (implemented by
      means of the python multiprocessing module). Special *CombiningTask*
      object instances are mapped to the pool managing the download for a
      certain network code.
    * On a second level RawCombinerTask implementations demultiplex the routing
      information, again. Multiple DownloadTask object instances (implemented
      using multiprocessing.pool.ThreadPool) are executed requesting granular
      stream epoch information (i.e. one task per fully resolved stream epoch).

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

    def __init__(self, mimetype, query_params={}, stream_epochs=[], post=True,
                 **kwargs):
        super().__init__(mimetype, query_params, stream_epochs, post, **kwargs)

        self._level = query_params.get('level')
        if self._level is None:
            raise RequestProcessorError("Missing parameter: 'level'.")

        self._num_combiners = 0

    # __init__ ()

    def _terminate(self):
        """
        Terminate the processor.

        Implies both shutting down the processor's pool and removing temporary
        files of already successfully returned tasks.
        """
        # XXX(damb): Unfortunately, pools do not allow the cancellation of
        # ansynchronously applied tasks (Partly reimplementing Pool from the
        # Python stdlib would have been necessary.). Hence, I implemented this
        # quite pragmatic approach.
        try:
            self._ctx.release()
        except (AttributeError, ErrorWithTraceback):
            pass

        # wait until combiners return in order to allow them shutting down
        # gracefully
        self.logger.debug('Waiting for combiners to return ...')

        while self._num_combiners > 0:
            for result in self._results:
                if result.ready():
                    _result = result.get()

                    if _result.extras['type_task'] == ETask.COMBINER:
                        self._num_combiners -= 1

            time.sleep(0.1)

        self.logger.debug('Combiners returned.')

        self._pool.terminate()
        self._pool.join()

        # XXX(damb): Since the worker pool is implemented by means of
        # multiprocessing.Pool tasks are actually *killed* when calling
        # self._pool.terminate(). This may cause an abrupt interrupt such that
        # for certain (race) conditions orphaned temporary files may be
        # remaining. Though, waiting before performing a final cleanup might
        # solve the problem. However, there is a trade-off between waiting and
        # freeing resources, again.
        if (self._keep_tempfiles not in (KeepTempfiles.ALL,
                                         KeepTempfiles.ON_ERRORS)):

            # XXX(damb): Wait a second before performing a final cleanup.
            time.sleep(1)
            for result in self._results:
                if result.ready():
                    _result = result.get()
                    try:
                        os.remove(_result.data)
                    except (TypeError, OSError) as err:
                        pass

        self.logger.debug('Terminate ...')
        self._pool = None

    # _terminate ()

    def _route(self):
        """
        Demultiplexes immediately routes for distributed physical networks i.e.
        networks to be combined.
        """
        routes = {}
        for net, _routes in super()._route().items():
            if len(_routes) > 1:
                routes[net] = demux_routes(_routes)
                continue

            routes[net] = _routes

        return routes

    # _route ()

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
            # create subcontext
            ctx = Context(root_only=True, payload=net)
            self._ctx.append(ctx)

            if len(routes) == 1:
                self.logger.debug(
                    'Creating StationXMLDownloadTask for net={!r} ...'.format(
                        net))
                t = StationXMLDownloadTask(
                    BulkFdsnRequestHandler(
                        routes[0].url, stream_epochs=routes[0].streams,
                        query_params=self.query_params),
                    name=net,
                    context=ctx,
                    keep_tempfiles=self._keep_tempfiles)

            elif len(routes) > 1:
                self.logger.debug(
                    'Creating CombinerTask for net={!r} ...'.format(net))
                t = StationXMLNetworkCombinerTask(
                    routes, self.query_params, name=net, context=ctx,
                    keep_tempfiles=self._keep_tempfiles)
                self._num_combiners += 1
            else:
                raise RoutingError('Missing routes.')

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

        try:
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
                                'Streaming from file {!r} (chunk_size={}).'.\
                                format(_result.data, self.CHUNK_SIZE))
                            try:
                                with open(_result.data, 'r',
                                          encoding='utf-8') as fd:
                                    for chunk in generate_chunks(fd):
                                        yield chunk
                            except Exception as err:
                                raise StreamingError(err)

                            if self._keep_tempfiles != KeepTempfiles.ALL:
                                self.logger.debug(
                                    'Removing temporary file {!r} ...'.format(
                                        _result.data))
                                try:
                                    os.remove(_result.data)
                                except OSError as err:
                                    RequestProcessorError(err)

                        elif _result.status_code == 413:
                            self._handle_413(_result)

                        elif _result.status_code == 418:
                            self._handle_teapot(_result)

                        else:
                            self._handle_error(_result)
                            self._sizes.append(0)

                        ready.append(result)

                        if _result.extras['type_task'] == ETask.COMBINER:
                            self._num_combiners -= 1

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
                    sum(self._sizes) + len(self.HEADER) - 4 +
                    len(self.SOURCE) +
                    len(datetime.datetime.utcnow().isoformat()) +
                    len(self.FOOTER)))

        except GeneratorExit:
            self.logger.debug('GeneratorExit: Propagating close event ...')
            self._terminate()

    # __iter__ ()

# class StationXMLRequestProcessor


class StationTextRequestProcessor(StationRequestProcessor):
    """
    This processor implements fdsnws-station text  federation.

    Data is fetched multithreaded from endpoints by means of bulk requests.

    Data from distributed physical networks (networks hosted at multiple
    datacenters currently is not merged.)
    """
    HEADER_NETWORK = '#Network|Description|StartTime|EndTime|TotalStations'
    HEADER_STATION = (
        '#Network|Station|Latitude|Longitude|'
        'Elevation|SiteName|StartTime|EndTime')
    HEADER_CHANNEL = (
        '#Network|Station|Location|Channel|Latitude|'
        'Longitude|Elevation|Depth|Azimuth|Dip|SensorDescription|Scale|'
        'ScaleFreq|ScaleUnits|SampleRate|StartTime|EndTime')

    @property
    def POOL_SIZE(self):
        return current_app.config['FED_THREAD_CONFIG']['fdsnws-station-text']

    def _request(self):
        """
        Process a federated fdsnws-station text request
        """
        routes = self._route()

        pool_size = (len(routes) if
                     len(routes) < self.POOL_SIZE else self.POOL_SIZE)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)

        for net, bulk_routes in routes.items():
            self.logger.debug(
                'Creating DownloadTasks for network code {!r} ...'.format(
                    net))

            for bulk_route in bulk_routes:

                self.logger.debug(
                    'Creating DownloadTask for {!r} ...'.format(bulk_route))
                t = StationTextDownloadTask(
                    BulkFdsnRequestHandler(
                        bulk_route.url,
                        stream_epochs=bulk_route.streams,
                        query_params=self.query_params),
                    context=self._ctx,
                    keep_tempfiles=self._keep_tempfiles)
                result = self._pool.apply_async(t)
                self._results.append(result)

        self._pool.close()

    # _request ()

    def __iter__(self):
        """
        Make the processor *streamable*.
        """
        try:
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
                                'Streaming from file {!r}.'.format(
                                    _result.data))
                            try:
                                with open(_result.data, 'r',
                                          encoding='utf-8') as fd:
                                    for line in fd:
                                        yield line
                            except Exception as err:
                                raise StreamingError(err)

                            if self._keep_tempfiles != KeepTempfiles.ALL:
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

        except GeneratorExit as err:
            self.logger.debug('GeneratorExit: Terminate ...')
            self._terminate()

    # __iter__ ()

# class StationTextRequestProcessor


class WFCatalogRequestProcessor(RequestProcessor):
    """
    Process a WFCatalog request.
    """
    LOGGER = "flask.app.federator.request_processor_wfcatalog"

    CHUNK_SIZE = 1024

    JSON_LIST_START = '['
    JSON_LIST_END = ']'
    JSON_LIST_SEP = ','

    @property
    def POOL_SIZE(self):
        return current_app.config['FED_THREAD_CONFIG']['eidaws-wfcatalog']

    def _request(self):
        """
        process a federated fdsnws-station text request
        """
        routes = demux_routes(self._route())

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
            ctx = Context(root_only=True)
            self._ctx.append(ctx)

            t = RawDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params),
                context=ctx,
                keep_tempfiles=self._keep_tempfiles,)
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
        ctx = Context(root_only=True)
        self._ctx.append(ctx)

        t = WFCatalogSplitAndAlignTask(
            result.data.url, result.data.stream_epochs[0],
            query_params=self.query_params,
            endtime=self.DEFAULT_ENDTIME,
            context=ctx,
            keep_tempfiles=self._keep_tempfiles,)

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

        try:
            while True:
                ready = []
                for result in self._results:
                    if result.ready():
                        _result = result.get()
                        if _result.status_code == 200:
                            if not sum(self._sizes):
                                # add header
                                yield self.JSON_LIST_START
                            else:
                                # prepend comma if not first stream epoch data
                                yield self.JSON_LIST_SEP

                            self.logger.debug(
                                'Streaming from file {!r} (chunk_size={}).'.\
                                format(_result.data, self.CHUNK_SIZE))
                            try:
                                with open(_result.data, 'rb') as fd:
                                    # skip leading bracket (from JSON list)
                                    size = 0
                                    for chunk in generate_chunks(
                                            fd, self.CHUNK_SIZE):
                                        size += len(chunk)
                                        yield chunk

                                self._sizes.append(size)

                            except Exception as err:
                                raise StreamingError(err)

                            if self._keep_tempfiles != KeepTempfiles.ALL:
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

                    # NOTE(damb): We have to handle responses > 5MB. Blocking
                    # the processor by means of time.sleep makes executing
                    # DownloadTasks IO bound.
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
        except GeneratorExit as err:
            self.logger.debug('GeneratorExit: Terminate ...')
            self._terminate()

    # __iter__ ()

# class WFCatalogRequestProcessor


# ---- END OF <process.py> ----
