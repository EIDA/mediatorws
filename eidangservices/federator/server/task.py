# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <task.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-federator).
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
# 2018/03/28        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA federator task facilities
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import collections
import datetime
import json
import logging
import os

from multiprocessing.pool import ThreadPool

import ijson

from lxml import etree

from eidangservices import settings
from eidangservices.federator.server.misc import get_temp_filepath
from eidangservices.federator.server.request import GranularFdsnRequestHandler
from eidangservices.utils.request import (binary_request, raw_request,
                                          stream_request, RequestsError)
from eidangservices.utils.error import Error


# -----------------------------------------------------------------------------
def catch_default_task_exception(func):
    """
    Method decorator catching default task exceptions.
    """
    def decorator(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as err:
            try:
                if self._pool is not None:
                    # TODO(damb): Shutdown tasks.
                    pass
            except AttributeError:
                pass

            msg = 'TaskError ({}): {}:{}.'.format(type(self).__name__,
                                                  type(err), err)
            return Result.error(
                status='TaskError-{}'.format(type(self).__name__),
                status_code=500, data=msg,
                warning='Caught in default task exception handler.')

    return decorator

# catch_default_task_exception ()

# -----------------------------------------------------------------------------
class Result(collections.namedtuple('Result', ['status',
                                               'status_code',
                                               'data',
                                               'length',
                                               'warning'])):
    """
    General purpose task result.
    """
    @classmethod
    def ok(cls, data, length=None):
        if length is None:
            length = len(data)
        return cls(data=data, length=length, status='Ok', status_code=200,
                   warning=None)

    @classmethod
    def error(cls, status, status_code, data=None, length=None,
              warning=None):
        if length is None:
            try:
                length = len(data)
            except Exception:
                length = None
        return cls(status=status, status_code=status_code, warning=warning,
                   data=data, length=length)

    @classmethod
    def nocontent(cls, status='NoContent', status_code=204, data=None,
                  warning=None):
        return cls.error(status=status, status_code=status_code, data=data,
                         warning=warning)

# class Result


# -----------------------------------------------------------------------------
class TaskBase(object):
    """
    Base class for tasks.
    """

    class TaskError(Error):
        """Base task error ({})."""

    def __init__(self, logger):
        self.logger = logging.getLogger(logger)

    def __getstate__(self):
        # prevent pickling errors for loggers
        d = dict(self.__dict__)
        if 'logger' in d.keys():
            d['logger'] = d['logger'].name
        return d

    # __getstate__ ()

    def __setstate__(self, d):
        if 'logger' in d.keys():
            d['logger'] = logging.getLogger(d['logger'])
            self.__dict__.update(d)

    # __setstate__ ()

    def __call__(self):
        raise NotImplementedError

# class TaskBase


class CombinerTask(TaskBase):
    """
    Task downloading and combining the information for a network. Downloading
    is performed in parallel.
    """

    LOGGER = 'flask.app.federator.task_combiner_raw'

    MAX_THREADS_DOWNLOADING = 5

    def __init__(self, routes, query_params, **kwargs):
        super().__init__((kwargs['logger'] if kwargs.get('logger') else
                          self.LOGGER))

        self._routes = routes
        self.query_params = query_params
        self.name = ('{}-{}'.format(type(self).__name__, kwargs.get('name')) if
                     kwargs.get('name') else type(self).__name__)

        if not self.query_params.get('format'):
            raise KeyError("Missing keyword parameter: 'format'.")

        self._num_workers = (
            len(routes) if len(routes) <
            kwargs.get('max_threads', self.MAX_THREADS_DOWNLOADING)
            else
            kwargs.get('max_threads', self.MAX_THREADS_DOWNLOADING))
        self._pool = None

        self._results = []
        self._sizes = []

    # __init__ ()

    def _handle_error(self, err):
        self.logger.warning(str(err))

    def _run(self):
        """
        Template method for CombinerTask declarations. Must be reimplemented.
        """
        return Result.nocontent()

    @catch_default_task_exception
    def __call__(self):
        return self._run()

    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, self.name)


# class CombinerTask


class StationXMLNetworkCombinerTask(CombinerTask):
    """
    Task downloading and combining StationXML information for a network
    element. Downloading is performed in parallel.

    :param routes: Routes to combine. Must belong to exclusively one network
    code.
    """
    # TODO(damb): The combiner has to write metadata to the log database.
    # Also in case of errors.
    # Besides of processors this combiner has to log since it is the instance
    # collecting and analyzing DownloadTask results.

    MAX_THREADS_DOWNLOADING = settings.EIDA_FEDERATOR_THREADS_STATION_XML
    LOGGER = 'flask.app.federator.task_combiner_stationxml'

    NETWORK_TAG = settings.STATIONXML_ELEMENT_NETWORK
    STATION_TAG = settings.STATIONXML_ELEMENT_STATION
    CHANNEL_TAG = settings.STATIONXML_ELEMENT_CHANNEL

    def __init__(self, routes, query_params, **kwargs):

        nets = set([se.network for route in routes for se in route.streams])
        if len(nets) != 1:
            raise ValueError(
                'Routes must belong exclusively to only a single '
                'network code.')

        super().__init__(routes, query_params, logger=self.LOGGER, **kwargs)
        self._level = self.query_params.get('level', 'station')
        self.path_tempfile = None

    # __init__ ()

    def _clean(self, result):
        self.logger.debug(
            'Removing temporary file {!r} ...'.format(
                result.data))
        try:
            os.remove(result.data)
        except OSError as err:
            pass

    # _clean ()

    def _run(self):
        """
        Combine StationXML <Network></Network> information.
        """
        self.logger.info('Executing task {!r}.'.format(self))
        self._pool = ThreadPool(processes=self._num_workers)

        for route in self._routes:
            self.logger.debug(
                'Creating DownloadTask for route {!r} ...'.format(route))
            t = StationXMLDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params),
                network_tag=self.NETWORK_TAG)

            # apply DownloadTask asynchronoulsy to the worker pool
            result = self._pool.apply_async(t)

            self._results.append(result)

        self._pool.close()

        _root = None
        # fetch results ready
        while True:
            ready = []
            for result in self._results:
                if result.ready():
                    _result = result.get()
                    if _result.status_code == 200:
                        if self._level == 'channel':
                            # merge <Channel></Channel> elements into
                            # <Station></Station>
                            if _root is None:
                                _root = self._extract_net_element(_result.data)
                            else:
                                for sta_element in self._extract_sta_elements(
                                        _result.data):
                                    self._merge_sta_element(_root, sta_element)

                            self._clean(_result)

                        elif self._level == 'station':
                            # append <Station></Station> elements to
                            # <Network></Network>
                            if _root is None:
                                _root = self._extract_net_element(_result.data)
                            else:
                                for sta_element in self._extract_sta_elements(
                                        _result.data):
                                    _root.append(sta_element)

                            self._clean(_result)

                        elif self._level == 'network':
                            # do not merge; do not remove temporary files;
                            # simply return the downloading task's result
                            self.path_tempfile = _result.data

                        self._sizes.append(_result.length)

                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)

                    ready.append(result)

            for result in ready:
                self._results.remove(result)

            if not self._results:
                break

        self._pool.join()

        if not sum(self._sizes):
            self.logger.warning(
                'Task {!r} terminates with no valid result.'.format(self))
            return Result.nocontent()

        _length = sum(self._sizes)
        # dump xml tree for <Network></Network> to temporary file
        if self._level in ('station', 'channel'):
            self.path_tempfile = get_temp_filepath()
            with open(self.path_tempfile, 'wb') as ofd:
                s = etree.tostring(_root)
                _length = len(s)
                ofd.write(s)

        self.logger.info(
            ('Task {!r} sucessfully finished '
             '(total bytes processed: {}).').format(self, sum(self._sizes)))

        return Result.ok(data=self.path_tempfile, length=_length)

    # _run ()

    def _extract_net_element(self, path_xml):
        with open(path_xml, 'rb') as ifd:
            return etree.parse(ifd).getroot()

    # _extract_net_element ()

    def _extract_sta_elements(self, path_xml,
                              namespaces=settings.STATIONXML_NAMESPACES):
        """
        Extract <Station><Station> elements from <Network></Network> tree.
        """
        station_tags = ['{}{}'.format(ns, self.STATION_TAG)
                        for ns in namespaces]
        with open(path_xml, 'rb') as ifd:
            root = etree.parse(ifd).getroot()
            for tag in station_tags:
                sta_elements = root.findall(tag)
                if not sta_elements:
                    continue
                return sta_elements

        raise self.TaskError(
            'Missing XML element for tags {!r}.'.format(
                station_tags))

    # _extract_sta_elements ()

    def _extract_cha_elements(self, sta_element,
                              namespaces=settings.STATIONXML_NAMESPACES):
        """
        Extract all <Channel><Channel> elements from <Station></Station> tree.
        """
        channel_tags = ['{}{}'.format(ns, self.CHANNEL_TAG)
                        for ns in namespaces]
        for tag in channel_tags:
            cha_elements = sta_element.findall(tag)
            if not cha_elements:
                continue
            return cha_elements

        raise self.TaskError(
            'Missing XML element for tags {!r}.'.format(
                channel_tags))

    # _extract_cha_elements ()

    def _merge_sta_element(self, root, sta_element,
                           namespaces=settings.STATIONXML_NAMESPACES):

        def equals_attrib(_sta_element, attrib):
            return (_sta_element.get(attrib) and
                    sta_element.get(attrib) and
                    _sta_element.get(attrib) == sta_element.get(attrib))

        # XXX(damb): check if station already available - if not, then append
        for _sta_element in root.iterfind(sta_element.tag):
            if (equals_attrib(_sta_element, 'code') and
                    equals_attrib(_sta_element, 'startDate')):
                for _cha_element in self._extract_cha_elements(sta_element,
                                                               namespaces):
                    _sta_element.append(_cha_element)

                break
        else:
            root.append(sta_element)

    # _merge_sta_element ()

# class StationXMLNetworkCombinerTask

# -----------------------------------------------------------------------------
class SplitAndAlignTask(TaskBase):
    """
    Base class for splitting and aligning (SAA) tasks.

    Concrete implementations of this task type implement stream epoch splitting
    and merging facilities.

    Assuming FDSN webservice endpoints are able to return HTTP status code 413
    (i.e. Request too large) within `TIMEOUT_REQUEST_TOO_LARGE` there is no
    need to implement this task recursively.
    """
    LOGGER = 'flask.app.task_saa'

    DEFAULT_SPLITTING_CONST = 2

    def __init__(self, url, stream_epoch, query_params, **kwargs):
        super().__init__(self.LOGGER)
        self.query_params = query_params
        self.path_tempfile = get_temp_filepath()
        self._url = url
        self._stream_epoch_orig = stream_epoch
        self._endtime = kwargs.get('endtime', datetime.datetime.utcnow())

        self._splitting_const = self.DEFAULT_SPLITTING_CONST
        self._stream_epochs = []

        self._size = 0

    # __init__ ()

    @property
    def stream_epochs(self):
        return self._stream_epochs

    def split(self, stream_epoch, num):
        """
        Split a stream epoch's epoch into `num` epochs.

        :param :cls:`eidangservices.utils.sncl.StreamEpoch` stream_epoch:
        Stream epoch object to split
        :param int num: Number of resulting stream epoch objects
        :return: List of split stream epochs
        """
        stream_epochs = sorted(
            stream_epoch.slice(num=num, default_endtime=self._endtime))
        if not self._stream_epochs:
            self._stream_epochs = stream_epochs
        else:
            # insert at current position
            idx = self._stream_epochs.index(stream_epoch)
            self._stream_epochs = (self._stream_epochs[:idx] + stream_epochs +
                                   self._stream_epochs[idx+1:])

        return stream_epochs

    # split ()

    def _handle_error(self, err):
        os.remove(self.path_tempfile)

        return Result.error(status='EndpointError',
                            status_code=err.response.status_code,
                            warning=str(err), data=err.response.data)
    # _handle_error ()

    def _run(self, stream_epoch):
        """
        Template method.
        """
        raise NotImplementedError

    @catch_default_task_exception
    def __call__(self):
        return self._run(self._stream_epoch_orig)

# class SplitAndAlignTask


class RawSplitAndAlignTask(SplitAndAlignTask):
    """
    SAA task implementation for a raw data stream. The task is implemented
    synchronously i.e. the task returns as soon as the last epoch segment is
    downloaded and aligned.
    """
    LOGGER = 'flask.app.task_saa_raw'

    MSEED_RECORD_SIZE = 512
    CHUNK_SIZE = MSEED_RECORD_SIZE

    def _run(self, stream_epoch):

        stream_epochs = self.split(stream_epoch, self._splitting_const)
        self.logger.debug(
            'Split stream epochs: {}.'.format(self.stream_epochs))

        # make a request for the first stream epoch
        for stream_epoch in stream_epochs:
            request_handler = GranularFdsnRequestHandler(
                self._url, stream_epoch, query_params=self.query_params)

            last_chunk = None
            try:
                with open(self.path_tempfile, 'rb') as ifd:
                    ifd.seek(-self.MSEED_RECORD_SIZE, 2)
                    last_chunk = ifd.read(self.MSEED_RECORD_SIZE)
            except (OSError, IOError, ValueError) as err:
                pass

            self.logger.debug(
                'Downloading (url={}, stream_epoch={}) ...'.format(
                    request_handler.url,
                    request_handler.stream_epochs))
            try:
                with open(self.path_tempfile, 'ab') as ofd:
                    for chunk in stream_request(
                        request_handler.post(),
                        chunk_size=self.CHUNK_SIZE,
                            method='raw'):
                        if last_chunk is not None and last_chunk == chunk:
                            continue
                        self._size += len(chunk)
                        ofd.write(chunk)

            except RequestsError as err:
                if err.response.status_code == 413:
                    self.logger.info(
                        'Download failed (url={}, stream_epoch={}).'.format(
                            request_handler.url,
                            request_handler.stream_epochs))
                    self._run(stream_epoch)
                else:
                    return self._handle_error(err)

            if stream_epoch in self.stream_epochs:
                self.logger.debug(
                    'Download (url={}, stream_epoch={}) finished.'.format(
                        request_handler.url,
                        request_handler.stream_epochs))

            if stream_epoch.endtime == self.stream_epochs[-1].endtime:
                return Result.ok(data=self.path_tempfile, length=self._size)

    # _run ()

# class RawSplitAndAlignTask


class WFCatalogSplitAndAlignTask(SplitAndAlignTask):
    """
    SAA task implementation for a WFCatalog data stream. The task is
    implemented synchronously i.e. the task returns as soon as the last epoch
    segment is downloaded and aligned.
    """
    LOGGER = 'flask.app.task_saa_wfcatalog'

    JSON_LIST_START = b'['
    JSON_LIST_END = b']'
    JSON_LIST_SEP = b','

    def __init__(self, url, stream_epoch, query_params, **kwargs):
        super().__init__(url, stream_epoch, query_params, **kwargs)
        self._last_obj = None

    def _run(self, stream_epoch):

        stream_epochs = self.split(stream_epoch, self._splitting_const)
        self.logger.debug(
            'Split stream epochs: {}.'.format(self.stream_epochs))

        # make a request for the first stream epoch
        for stream_epoch in stream_epochs:
            request_handler = GranularFdsnRequestHandler(
                self._url, stream_epoch, query_params=self.query_params)

            self.logger.debug(
                'Downloading (url={}, stream_epoch={}) ...'.format(
                    request_handler.url,
                    request_handler.stream_epochs))
            try:
                with open(self.path_tempfile, 'ab') as ofd:
                    with raw_request(request_handler.post()) as ifd:

                        if self._last_obj is None:
                            ofd.write(self.JSON_LIST_START)
                            self._size += 1

                        for obj in ijson.items(ifd, 'item'):
                            # NOTE(damb): A python object has to be created
                            # since else we cannot compare objects. (JSON is
                            # unorederd.)

                            if (self._last_obj is not None and
                                    self._last_obj == obj):
                                continue

                            if self._last_obj is not None:
                                ofd.write(self.JSON_LIST_SEP)
                                self._size += 1

                            self._last_obj = obj
                            # convert back to bytearray
                            obj = json.dumps(obj).encode('utf-8')

                            self._size += len(obj)
                            ofd.write(obj)

            except RequestsError as err:
                if err.response.status_code == 413:
                    self.logger.info(
                        'Download failed (url={}, stream_epoch={}).'.format(
                            request_handler.url,
                            request_handler.stream_epochs))
                    self._run(stream_epoch)
                else:
                    return self._handle_error(err)

            if stream_epoch in self.stream_epochs:
                self.logger.debug(
                    'Download (url={}, stream_epoch={}) finished.'.format(
                        request_handler.url,
                        request_handler.stream_epochs))

            if stream_epoch.endtime == self.stream_epochs[-1].endtime:

                with open(self.path_tempfile, 'ab') as ofd:
                    ofd.write(self.JSON_LIST_END)
                    self._size += 1

                return Result.ok(data=self.path_tempfile, length=self._size)

    # _run ()

# class WFCatalogSplitAndAlignTask

# -----------------------------------------------------------------------------
class RawDownloadTask(TaskBase):
    """
    Task downloading the data for a single StreamEpoch by means of streaming.
    """

    LOGGER = 'flask.app.federator.task_download_raw'

    CHUNK_SIZE = 1024 * 1024

    def __init__(self, request_handler, **kwargs):
        super().__init__(self.LOGGER)
        self._request_handler = request_handler
        self.path_tempfile = get_temp_filepath()

        self.chunk_size = (self.CHUNK_SIZE
                           if kwargs.get('chunk_size') is None
                           else kwargs.get('chunk_size'))

        self._size = 0

    # __init__ ()

    @catch_default_task_exception
    def __call__(self):

        self.logger.debug(
            'Downloading (url={}, stream_epochs={}) ...'.format(
                self._request_handler.url,
                self._request_handler.stream_epochs))

        try:
            with open(self.path_tempfile, 'wb') as ofd:
                for chunk in stream_request(self._request_handler.post(),
                                            chunk_size=self.chunk_size,
                                            method='raw'):
                    self._size += len(chunk)
                    ofd.write(chunk)

        except RequestsError as err:
            return self._handle_error(err)
        else:
            self.logger.debug(
                'Download (url={}, stream_epochs={}) finished.'.format(
                    self._request_handler.url,
                    self._request_handler.stream_epochs))

        return Result.ok(data=self.path_tempfile, length=self._size)

    # __call__ ()

    def _handle_error(self, err):
        try:
            os.remove(self.path_tempfile)
        except OSError:
            pass

        try:
            resp = err.response
            try:
                data = err.response.text
            except AttributeError:
                return Result.error('RequestsError',
                                    status_code=503,
                                    warning=type(err),
                                    data=str(err))
        except Exception as err:
            return Result.error('InternalServerError',
                                status_code=500,
                                warning='Unhandled exception.',
                                data=str(err))
        else:
            if resp.status_code == 413:
                data = self._request_handler

            return Result.error(status='EndpointError',
                                status_code=resp.status_code,
                                warning=str(err), data=data)
    # _handle_error ()

# class RawDownloadTask


class StationTextDownloadTask(RawDownloadTask):
    """
    Download data from an endpoint. In addition this task removes header
    information from response.
    """

    @catch_default_task_exception
    def __call__(self):

        self.logger.debug(
            'Downloading (url={}, stream_epochs={}) ...'.format(
                self._request_handler.url,
                self._request_handler.stream_epochs))

        try:
            with open(self.path_tempfile, 'wb') as ofd:
                # NOTE(damb): For granular fdnsws-station-text request it seems
                # ok buffering the entire response in memory.
                with binary_request(self._request_handler.post()) as ifd:
                    for line in ifd:
                        self._size += len(line)
                        if line.startswith(b'#'):
                            continue
                        ofd.write(line.strip() + b'\n')

        except RequestsError as err:
            return self._handle_error(err)
        else:
            self.logger.debug(
                'Download (url={}, stream_epochs={}) finished.'.format(
                    self._request_handler.url,
                    self._request_handler.stream_epochs))

        return Result.ok(data=self.path_tempfile, length=self._size)

    # __call__ ()

# class StationTextDownloadTask


class StationXMLDownloadTask(RawDownloadTask):
    """
    Download StationXML from an endpoint. Emerge <Network></Network> specific
    data from StationXML.

    .. note:: This task temporarly loads the entire result into memory.
    However, for a granular endpoint request approach this seems doable.
    """
    NETWORK_TAG = settings.STATIONXML_ELEMENT_NETWORK

    def __init__(self, request_handler, **kwargs):
        super().__init__(request_handler, **kwargs)
        self.network_tag = kwargs.get('network_tag', self.NETWORK_TAG)

    @catch_default_task_exception
    def __call__(self):

        self.logger.debug(
            'Downloading (url={}, stream_epochs={}) ...'.format(
                self._request_handler.url,
                self._request_handler.stream_epochs))

        network_tags = ['{}{}'.format(ns, self.network_tag)
                        for ns in settings.STATIONXML_NAMESPACES]

        try:
            with open(self.path_tempfile, 'wb') as ofd:
                # XXX(damb): Load the entire result into memory.
                with binary_request(self._request_handler.post()) as ifd:
                    station_xml = etree.parse(ifd).getroot()
                    for net_element in station_xml.iter(*network_tags):
                        s = etree.tostring(net_element)
                        self._size += len(s)
                        ofd.write(s)

        except RequestsError as err:
            return self._handle_error(err)
        else:
            self.logger.debug(
                'Download (url={}, stream_epochs={}) finished.'.format(
                    self._request_handler.url,
                    self._request_handler.stream_epochs))

        return Result.ok(data=self.path_tempfile, length=self._size)

    # __call__ ()

# class StationXMLDownloadTask


# ---- END OF <task.py> ----
