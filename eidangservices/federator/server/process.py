# -*- coding: utf-8 -*-
"""
federator processing facilities
"""

import datetime
import logging
import multiprocessing as mp
import os
import time
import uuid

from flask import current_app, stream_with_context, Response

from eidangservices import settings
from eidangservices.federator import __version__
from eidangservices.federator.server.misc import (
    Context, ContextLoggerAdapter, KeepTempfiles)
from eidangservices.federator.server.mixin import ClientRetryBudgetMixin
from eidangservices.federator.server.request import RoutingRequestHandler
from eidangservices.federator.server.strategy import (  # noqa
    GranularRequestStrategy, NetworkBulkRequestStrategy,
    NetworkCombiningRequestStrategy, AdaptiveNetworkBulkRequestStrategy)
from eidangservices.federator.server.task import (
    RawDownloadTask, RawSplitAndAlignTask, StationTextDownloadTask,
    StationXMLDownloadTask, StationXMLNetworkCombinerTask,
    WFCatalogSplitAndAlignTask)
from eidangservices.utils.error import ErrorWithTraceback
from eidangservices.utils.httperrors import FDSNHTTPError


# TODO(damb): This is a note regarding the federator-registered mode.
# Processors using exclusively DownloadTask objects must perform a detailed
# logging to the log DB. Processors using Combiners delegate logging to the
# corresponding combiner tasks.
# For bulk requests no detailed logging can be provided.


class RequestProcessorError(ErrorWithTraceback):
    """Base RequestProcessor error ({})."""


class ConfigurationError(RequestProcessorError):
    """Configuration error ({})."""


class RoutingError(RequestProcessorError):
    """Error while routing ({})."""


class StreamingError(RequestProcessorError):
    """Error while streaming ({})."""


# -----------------------------------------------------------------------------
class RequestProcessor(ClientRetryBudgetMixin):
    """
    Abstract base class for request processors.
    """

    LOGGER = "flask.app.federator.request_processor"

    _STRATEGY_MAP = {
        'granular': GranularRequestStrategy,
        'bulk': NetworkBulkRequestStrategy,
        'adaptive-bulk': AdaptiveNetworkBulkRequestStrategy,
        'combining': NetworkCombiningRequestStrategy}

    ALLOWED_STRATEGIES = None
    DEFAULT_REQUEST_STRATEGY = None
    DEFAULT_RETRY_BUDGET_CLIENT = \
        settings.EIDA_FEDERATOR_DEFAULT_RETRY_BUDGET_CLIENT  # percent

    POOL_SIZE = 5
    # MAX_TASKS_PER_CHILD = 4
    TIMEOUT_STREAMING = settings.EIDA_FEDERATOR_STREAMING_TIMEOUT

    def __init__(self, mimetype, query_params={}, stream_epochs=[], **kwargs):
        """
        :param str mimetype: The response's mimetype
        :param dict query_params: Request query parameters
        :param stream_epochs: Stream epochs requested
        :type stream_epochs: List of :py:class:`StreamEpoch`

        :param str logger: Logger name (optional)
        :param request_strategy: Request strategy applied (optional)
        :type request_strategy: :py:class:`RequestStrategyBase`
        :param keep_tempfiles: Flag indicating how to treat temporary files
        :type keep_tempfiles: :py:class:`KeepTempfiles`
        :param str http_method: HTTP method used when issuing requests to
            endpoints
        :param float retry_budget_client: Per client retry-budget in percent.
            The value defines the cut-off error ratio above requests to
            datacenters (DC) are dropped.
        :param str proxy_netloc: Proxy netloc delegated to the routing service
            in use
        """

        self.mimetype = mimetype
        self.content_type = (
            '{}; {}'.format(self.mimetype, settings.CHARSET_TEXT)
            if self.mimetype == settings.MIMETYPE_TEXT else self.mimetype)
        self.query_params = query_params
        self.stream_epochs = stream_epochs

        # TODO(damb): Pass as ctor arg.
        self._routing_service = current_app.config['ROUTING_SERVICE']

        self._logger = logging.getLogger(kwargs.get('logger', self.LOGGER))

        self._ctx = kwargs.get('context', Context(uuid.uuid4()))
        if not self._ctx.locked:
            self._ctx.acquire()

        self.logger = ContextLoggerAdapter(self._logger, {'ctx': self._ctx})

        self._keep_tempfiles = kwargs.get('keep_tempfiles', KeepTempfiles.NONE)

        self._retry_budget_client = kwargs.get(
            'retry_budget_client', self.DEFAULT_RETRY_BUDGET_CLIENT)

        self._num_routes = 0
        self._pool = None
        self._results = []
        self._sizes = []

        self._default_endtime = datetime.datetime.utcnow()

        self._nodata = int(self.query_params.get(
            'nodata', settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE))

        # lookup resource configuration attributes
        req_strategy = kwargs.get('request_strategy',
                                  self.DEFAULT_REQUEST_STRATEGY)
        if req_strategy not in self.ALLOWED_STRATEGIES:
            raise ConfigurationError(
                'Invalid strategy: {!r}'.format(req_strategy))
        self._strategy = self._STRATEGY_MAP[req_strategy]
        self._strategy = self._strategy(
            context=self._ctx, default_endtime=self.DEFAULT_ENDTIME)

        self._http_method = kwargs.get(
            'request_method', settings.EIDA_FEDERATOR_DEFAULT_HTTP_METHOD)
        self._num_threads = kwargs.get('num_threads', self.POOL_SIZE)
        self._proxy_netloc = kwargs.get(
            'proxy_netloc', settings.EIDA_FEDERATOR_DEFAULT_NETLOC_PROXY)

        self._post = True

    @staticmethod
    def create(service, *args, **kwargs):
        """
        Factory method for RequestProcessor object instances.

        :param str service: Service identifier.
        :param dict kwargs: A dictionary passed to processor constructors.
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

    @property
    def post(self):
        return self._post

    @post.setter
    def post(self, val):
        self._post = bool(val)

    @property
    def DEFAULT_ENDTIME(self):
        return self._default_endtime

    @property
    def streamed_response(self):
        """
        Return a streamed :py:class:`flask.Response`.
        """
        self._route()

        if not self._num_routes:
            raise FDSNHTTPError.create(self._nodata)

        self._request()

        # XXX(damb): Only return a streamed response as soon as valid data
        # is available. Use a timeout and process errors here.
        self._wait()

        resp = Response(stream_with_context(self), mimetype=self.mimetype,
                        content_type=self.content_type)

        resp.call_on_close(self._call_on_close)

        return resp

    def _route(self):
        """
        Route a federating request.

        :retval: Number of routes received
        :rtype: int
        """
        # XXX(damb): Configure access=closed if routing restricted data is
        # required.
        routing_req = RoutingRequestHandler(
            self._routing_service, self.stream_epochs,
            self.query_params, proxy_netloc=self._proxy_netloc,
            access='open')

        self._num_routes = self._strategy.route(
            routing_req, post=self.post, nodata=self._nodata,
            retry_budget_client=self._retry_budget_client)

    def _handle_error(self, err):
        self.logger.warning(str(err))

        if self._keep_tempfiles not in (KeepTempfiles.ALL,
                                        KeepTempfiles.ON_ERRORS):
            try:
                os.remove(err.data)
            except (OSError, TypeError):
                pass

    def _handle_413(self, result):
        self.logger.warning(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        raise FDSNHTTPError.create(413, service_version=__version__)

    def _handle_teapot(self, result):
        self.logger.debug('Teapot: {}'.format(result))

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
                raise FDSNHTTPError.create(self._nodata)

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
                    except (TypeError, OSError):
                        pass

        self._pool = None

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
        `thread post
        <https://groups.google.com/forum/#!topic/modwsgi/jr2ayp0xesk>`_ very
        detailed.
        """
        self.logger.debug("Finalize response (closing) ...")

        self.logger.debug("Garbage collect response code stats ...")
        for url in self._strategy.routing_table.keys():
            self.gc_cretry_budget(url)

        try:
            self._pool.terminate()
            self._pool.join()
        except AttributeError:
            pass

        self._pool = None

    def __iter__(self):
        raise NotImplementedError


class RawRequestProcessor(RequestProcessor):
    """
    Federating request processor implementation controlling both the federated
    downloading process and the merging afterwards.
    """

    LOGGER = "flask.app.federator.request_processor_raw"

    ALLOWED_STRATEGIES = ('granular', 'bulk')
    DEFAULT_DEFAULT_REQUEST_STRATEGY = 'granular'

    CHUNK_SIZE = 1024

    def _request(self):
        """
        Issue concurrent fdsnws-dataselect requests.
        """

        assert bool(self._num_routes), 'No routes available.'

        pool_size = min(self._num_routes, self._num_threads)
        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)
        # NOTE(damb): With pleasure I'd like to define the parameter
        # maxtasksperchild=self.MAX_TASKS_PER_CHILD)
        # However, using this parameter seems to lead to processes unexpectedly
        # terminated. Hence some tasks never return a *ready* result.

        self._results = self._strategy.request(
            self._pool, tasks={'default': RawDownloadTask},
            query_params=self.query_params,
            keep_tempfiles=self._keep_tempfiles,
            http_method=self._http_method,
            retry_budget_client=self._retry_budget_client)

    def _handle_413(self, result):
        self.logger.info(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        self.logger.debug(
            'Creating SAATask for (url={}, '
            'stream_epochs={}) ...'.format(result.data.url,
                                           result.data.stream_epochs))
        ctx = Context()
        self._ctx.append(ctx)

        t = RawSplitAndAlignTask(
            result.data.url, result.data.stream_epochs[0],
            query_params=self.query_params,
            endtime=self.DEFAULT_ENDTIME,
            context=ctx,
            keep_tempfiles=self._keep_tempfiles)

        result = self._pool.apply_async(t)
        self._results.append(result)

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
                                'Streaming from file {!r} (chunk_size={}).'.
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
        except GeneratorExit:
            self.logger.debug('GeneratorExit: Terminate ...')
            self._terminate()


class StationRequestProcessor(RequestProcessor):
    """
    Base class for federating fdsnws-station request processors.
    """

    LOGGER = "flask.app.federator.request_processor_station"

    @staticmethod
    def create(response_format, *args, **kwargs):
        if response_format == 'xml':
            return StationXMLRequestProcessor(*args, **kwargs)
        elif response_format == 'text':
            return StationTextRequestProcessor(*args, **kwargs)
        else:
            raise KeyError('Invalid RequestProcessor chosen.')


class StationXMLRequestProcessor(StationRequestProcessor):
    """
    `StationXML <http://www.fdsn.org/xml/station/>`_ federation processor.

    Due to the nature of the *StationXML* data format this processer performs
    routing, requesting and merging using a two-level hierarchical approach.

    The first level operates on network code level granularity. The
    second-level is implemented as part of the strategy actually performing the
    endpoint requests. Finally, the resulting network epoch tags are merged and
    wrapped into corresponding StationXML headers.
    """

    CHUNK_SIZE = 1024

    ALLOWED_STRATEGIES = ('combining', 'adaptive-bulk')
    DEFAULT_REQUEST_STRATEGY = 'combining'

    SOURCE = 'EIDA'
    HEADER = ('<?xml version="1.0" encoding="UTF-8"?>'
              '<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1" '
              'schemaVersion="1.0">'
              '<Source>{}</Source>'
              '<Created>{}</Created>')
    FOOTER = '</FDSNStationXML>'

    TIMEOUT_SHUTDOWN = settings.EIDA_FEDERATOR_SHUTDOWN_TIMEOUT

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

        # XXX(damb): Since the worker pool is implemented by means of
        # multiprocessing.Pool tasks are actually *killed* when calling
        # self._pool.terminate(). This may cause an abrupt interrupt such that
        # for certain (race) conditions orphaned temporary files may be
        # remaining. Though, waiting before performing a final cleanup might
        # solve the problem. However, there is a trade-off between waiting and
        # freeing resources, again.
        # Calling self._pool.close() relies on tasks returning immediately
        # if noting that no active context is available.
        if (self._keep_tempfiles not in (KeepTempfiles.ALL,
                                         KeepTempfiles.ON_ERRORS)):
            self.logger.debug(
                'Waiting for tasks (allowing them a graceful shutdown) ...')
            now = datetime.datetime.utcnow()
            while True:
                ready = []
                for result in self._results:
                    if result.ready():

                        _result = result.get()
                        try:
                            os.remove(_result.data)
                        except (TypeError, OSError):
                            pass

                        ready.append(result)

                for result in ready:
                    self._results.remove(result)

                if not self._results:
                    break

                if (datetime.datetime.utcnow() > now +
                        datetime.timedelta(seconds=self.TIMEOUT_SHUTDOWN)):
                    self.logger.warning('Timeout. Forced shutdown. '
                                        'Temporary files might remain.')
                    break

                time.sleep(0.1)

        self.logger.debug('Terminate ...')

    def _request(self):
        """
        Process a federated fdsnws-station format=xml request
        """

        assert bool(self._num_routes), 'No routes available.'

        pool_size = min(self._num_routes, self._num_threads)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.Pool(processes=pool_size)

        self._results = self._strategy.request(
            self._pool, tasks={'default': StationXMLDownloadTask,
                               'combining': StationXMLNetworkCombinerTask},
            query_params=self.query_params,
            keep_tempfiles=self._keep_tempfiles,
            http_method=self._http_method,
            pool_size=self.POOL_SIZE,
            retry_budget_client=self._retry_budget_client)

        self._pool.close()

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
                                'Streaming from file {!r} (chunk_size={}).'.
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


class StationTextRequestProcessor(StationRequestProcessor):
    """
    This processor implements fdsnws-station format=text data federation.
    """

    ALLOWED_STRATEGIES = ('granular', 'bulk')
    DEFAULT_REQUEST_STRATEGY = 'bulk'

    HEADER_NETWORK = '#Network|Description|StartTime|EndTime|TotalStations'
    HEADER_STATION = (
        '#Network|Station|Latitude|Longitude|'
        'Elevation|SiteName|StartTime|EndTime')
    HEADER_CHANNEL = (
        '#Network|Station|Location|Channel|Latitude|'
        'Longitude|Elevation|Depth|Azimuth|Dip|SensorDescription|Scale|'
        'ScaleFreq|ScaleUnits|SampleRate|StartTime|EndTime')

    def __init__(self, mimetype, query_params={}, stream_epochs=[], **kwargs):
        super().__init__(mimetype, query_params, stream_epochs, **kwargs)

        self._level = query_params.get('level')
        assert self._level, "Missing parameter: 'level'"

    def _request(self):
        """
        Process a federated fdsnws-station format=text request
        """

        assert bool(self._num_routes), 'No routes available.'

        pool_size = min(self._num_routes, self._num_threads)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)

        self._results = self._strategy.request(
            self._pool, tasks={'default': StationTextDownloadTask},
            query_params=self.query_params,
            keep_tempfiles=self._keep_tempfiles,
            http_method=self._http_method,
            retry_budget_client=self._retry_budget_client)

        self._pool.close()

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

        except GeneratorExit:
            self.logger.debug('GeneratorExit: Terminate ...')
            self._terminate()


class WFCatalogRequestProcessor(RequestProcessor):
    """
    Process a WFCatalog request.
    """

    LOGGER = "flask.app.federator.request_processor_wfcatalog"

    ALLOWED_STRATEGIES = ('granular', 'bulk')
    DEFAULT_REQUEST_STRATEGY = 'granular'

    CHUNK_SIZE = 1024

    JSON_LIST_START = '['
    JSON_LIST_END = ']'
    JSON_LIST_SEP = ','

    def _request(self):
        """
        Issue concurrent eidaws-wfcatalog requests.
        """

        assert bool(self._num_routes), 'No routes available.'

        pool_size = min(self._num_routes, self._num_threads)

        self.logger.debug('Init worker pool (size={}).'.format(pool_size))
        self._pool = mp.pool.ThreadPool(processes=pool_size)
        # NOTE(damb): With pleasure I'd like to define the parameter
        # maxtasksperchild=self.MAX_TASKS_PER_CHILD)
        # However, using this parameter seems to lead to processes unexpectedly
        # terminated. Hence some tasks never return a *ready* result.

        self._results = self._strategy.request(
            self._pool, tasks={'default': RawDownloadTask},
            query_params=self.query_params,
            keep_tempfiles=self._keep_tempfiles,
            http_method=self._http_method,
            retry_budget_client=self._retry_budget_client)

    def _handle_413(self, result):
        self.logger.info(
            'Handle endpoint HTTP status code 413 (url={}, '
            'stream_epochs={}).'.format(result.data.url,
                                        result.data.stream_epochs))
        self.logger.debug(
            'Creating SAATask for (url={}, '
            'stream_epochs={}) ...'.format(result.data.url,
                                           result.data.stream_epochs))
        ctx = Context()
        self._ctx.append(ctx)

        t = WFCatalogSplitAndAlignTask(
            result.data.url, result.data.stream_epochs[0],
            query_params=self.query_params,
            endtime=self.DEFAULT_ENDTIME,
            context=ctx,
            keep_tempfiles=self._keep_tempfiles,)

        result = self._pool.apply_async(t)
        self._results.append(result)

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
                                'Streaming from file {!r} (chunk_size={}).'.
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
                    sum(self._sizes) + 2 + len(self._sizes) - 1))
        except GeneratorExit:
            self.logger.debug('GeneratorExit: Terminate ...')
            self._terminate()
