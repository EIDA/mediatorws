# -*- coding: utf-8 -*-
"""
EIDA federator task facilities
"""

import collections
import datetime
import enum
import json
import logging
import os

from multiprocessing.pool import ThreadPool

import ijson

from lxml import etree

from eidangservices import settings
from eidangservices.federator.server.misc import (
    Context, ContextLoggerAdapter, KeepTempfiles, get_temp_filepath,
    elements_equal)
from eidangservices.federator.server.mixin import ClientRetryBudgetMixin
from eidangservices.federator.server.request import GranularFdsnRequestHandler
from eidangservices.utils.request import (binary_request, raw_request,
                                          stream_request, RequestsError)
from eidangservices.utils.error import Error, ErrorWithTraceback


class ETask(enum.Enum):
    DOWNLOAD = 0
    COMBINER = 1
    SPLITALIGN = 2


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

            msg = 'TaskError ({}): {}:{}'.format(type(self).__name__,
                                                 type(err), err)
            return Result.error(
                status='TaskError-{}'.format(type(self).__name__),
                status_code=500, data=msg,
                warning='Caught in default task exception handler.',
                extras={'type_task': self._TYPE})

    return decorator


def with_ctx_guard(func):
    """
    Method decorator acting as a context guard performing garbage collection.
    """
    def decorator(self, *args, **kwargs):
        try:
            if self._has_inactive_ctx():
                raise self.MissingContextLock

            retval = func(self, *args, **kwargs)

            if self._has_inactive_ctx():
                raise self.MissingContextLock

            return retval

        except TaskBase.MissingContextLock:
            try:
                self.logger.debug(
                    '{}: Teardown (stream_epochs={}) ...'.format(
                        type(self).__name__,
                        self._request_handler.stream_epochs))
            except AttributeError:
                self.logger.debug(
                    '{}: Teardown (type={}) ...'.format(
                        type(self).__name__, self._TYPE))
            else:
                self._teardown(self.path_tempfile)

            return Result.teardown(data=self._ctx,
                                   extras={'type_task': self._TYPE})

    return decorator


def with_client_retry_budget_validation(func):
    """
    Method decorator allowing tasks to perform a *per-client retry budget*
    validation.
    """

    def decorator(self, *args, **kwargs):

        e_ratio = self.get_cretry_budget_error_ratio(self.url)
        if (e_ratio > self._retry_budget_client):

            self.logger.debug(
                '{}: Teardown (type={}, error_ratio) ...'.format(
                    type(self).__name__, self._TYPE, e_ratio))
            self._teardown(self.path_tempfile)

            return Result.teardown(
                warning='Exceeded per client retry-budget: {}'.format(e_ratio),
                extras={'type_task': self._TYPE})

        return func(self, *args, **kwargs)

    return decorator


# -----------------------------------------------------------------------------
class Result(collections.namedtuple('Result', ['status',
                                               'status_code',
                                               'data',
                                               'length',
                                               'warning',
                                               'extras'])):
    """
    General purpose task result. Properties correspond to a tiny subset of
    HTTP.
    """
    @classmethod
    def ok(cls, data, length=None, extras=None):
        if length is None:
            length = len(data)
        return cls(data=data, length=length, status='Ok', status_code=200,
                   warning=None, extras=extras)

    @classmethod
    def error(cls, status, status_code, data=None, length=None,
              warning=None, extras=None):
        if length is None:
            try:
                length = len(data)
            except Exception:
                length = None
        return cls(status=status, status_code=status_code, warning=warning,
                   data=data, length=length, extras=extras)

    @classmethod
    def nocontent(cls, status='NoContent', status_code=204, data=None,
                  warning=None, extras=None):
        return cls.error(status=status, status_code=status_code, data=data,
                         warning=warning, extras=extras)

    @classmethod
    def teardown(cls, status="I'm a teapot", status_code=418, data=None,
                 warning=None, extras=None):
        return cls.error(status=status, status_code=status_code, data=data,
                         warning=warning, extras=extras)


# -----------------------------------------------------------------------------
class TaskBase:
    """
    Base class for tasks.

    :param str logger: Name of the logger to be acquired
    :param keep_tempfiles: Flag how temporary files should be treated
    :type keep_tempfiles: :py:class:`KeepTempfiles`
    """
    _TYPE = ETask.DOWNLOAD

    class TaskError(Error):
        """Base task error ({})."""

    class MissingContextLock(TaskError):
        """Context is not locked."""

    def __init__(self, logger, **kwargs):

        self._logger = logging.getLogger(logger)
        self._ctx = kwargs.get('context')
        self.logger = ContextLoggerAdapter(self._logger, {'ctx': self._ctx})

        self._http_method = kwargs.get(
            'http_method', settings.EIDA_FEDERATOR_DEFAULT_HTTP_METHOD)
        self._retry_budget_client = kwargs.get(
            'retry_budget_client',
            settings.EIDA_FEDERATOR_DEFAULT_RETRY_BUDGET_CLIENT)
        self._keep_tempfiles = kwargs.get(
            'keep_tempfiles', KeepTempfiles.NONE)

    def __getstate__(self):
        # prevent pickling errors for loggers
        d = dict(self.__dict__)
        if '_logger' in d.keys():
            d['_logger'] = d['_logger'].name
        if 'logger' in d.keys():
            del d['logger']
        return d

    def __setstate__(self, d):
        if '_logger' in d.keys():
            d['_logger'] = logging.getLogger(d['_logger'])
            try:
                d['logger'] = ContextLoggerAdapter(
                    d['_logger'], {'ctx': self._ctx})
            except AttributeError:
                if '_ctx' in d.keys():
                    d['logger'] = ContextLoggerAdapter(
                        d['_logger'], {'ctx': d['_ctx']})
                else:
                    d['logger'] = d['_logger']

        self.__dict__.update(d)

    def __call__(self):
        raise NotImplementedError

    def _has_inactive_ctx(self):
        return self._ctx and not self._ctx.locked

    def _teardown(self, paths_tempfiles=None):
        """
        Securely tear a task down and perform garbage collection.

        :param paths_tempfiles: Temporary files to be removed
        :type path_tempfiles: None or str or list
        """
        if isinstance(paths_tempfiles, str):
            paths_tempfiles = [paths_tempfiles]

        if (paths_tempfiles and
            self._keep_tempfiles not in (KeepTempfiles.ALL,
                                         KeepTempfiles.ON_ERRORS)):
            for p in paths_tempfiles:
                try:
                    os.remove(p)
                except OSError:
                    pass


class CombinerTask(TaskBase):
    """
    Task downloading and combining the information for a network. Downloading
    is performed concurrently.
    """
    _TYPE = ETask.COMBINER

    LOGGER = 'flask.app.federator.task_combiner_raw'

    MAX_THREADS_DOWNLOADING = 5

    def __init__(self, routes, query_params, **kwargs):
        super().__init__((kwargs.pop('logger') if kwargs.get('logger') else
                          self.LOGGER), **kwargs)

        self._routes = routes
        self.query_params = query_params
        self.name = ('{}-{}'.format(type(self).__name__, kwargs.get('name')) if
                     kwargs.get('name') else type(self).__name__)

        if not self.query_params.get('format'):
            raise KeyError("Missing keyword parameter: 'format'.")

        self._num_workers = min(
            len(routes),
            kwargs.get('pool_size', self.MAX_THREADS_DOWNLOADING))
        self._pool = None

        self._results = []
        self._sizes = []

    def _handle_error(self, err):
        self.logger.warning(str(err))

    def _terminate(self):
        """
        Terminate the combiner.

        Implies both shutting down the combiner's pool and removing temporary
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
                    except OSError:
                        pass

        self._pool = None

    def _run(self):
        """
        Template method for CombinerTask declarations. Must be reimplemented.
        """
        return Result.nocontent(extras={'type_task': self._TYPE})

    @catch_default_task_exception
    @with_ctx_guard
    def __call__(self):
        return self._run()

    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, self.name)


class StationXMLNetworkCombinerTask(CombinerTask):
    """
    Task downloading and combining `StationXML
    <http://www.fdsn.org/xml/station/>`_ information for a network element.
    Downloading is performed concurrently.

    :param list routes: Routes to combine. Must belong to exclusively a single
        network code.

    .. note::

        *StationXML* :code:`BaseNodeType` elements by definition
        (http://www.fdsn.org/xml/station/fdsn-station-1.0.xsd) are ordered
        using :code:`<xs:sequence></sequence>`. This fact is used when merging
        StationXML :code`BaseNodeType` elements.

    """

    LOGGER = 'flask.app.federator.task_combiner_stationxml'

    POOL_SIZE = 5

    NETWORK_TAG = settings.STATIONXML_ELEMENT_NETWORK
    STATION_TAG = settings.STATIONXML_ELEMENT_STATION
    CHANNEL_TAG = settings.STATIONXML_ELEMENT_CHANNEL

    def __init__(self, routes, query_params, **kwargs):

        nets = set([se.network for route in routes for se in route.streams])

        # TODO(damb): Use assert instead
        if len(nets) != 1:
            raise ValueError(
                'Routes must belong exclusively to a single '
                'network code.')

        super().__init__(routes, query_params, logger=self.LOGGER, **kwargs)
        self._level = self.query_params.get('level', 'station')

        self._network_elements = []
        self.path_tempfile = None

    def _clean(self, result):
        self.logger.debug(
            'Removing temporary file {!r} ...'.format(
                result.data))
        if (result.data and
            self._keep_tempfiles not in (KeepTempfiles.ALL,
                                         KeepTempfiles.ON_ERRORS)):
            try:
                os.remove(result.data)
            except OSError:
                pass

    def _run(self):
        """
        Combine `StationXML <http://www.fdsn.org/xml/station/>`_
        :code:`<Network></Network>` information.
        """
        self.logger.info('Executing task {!r} ...'.format(self))
        self._pool = ThreadPool(processes=self._num_workers)

        for route in self._routes:
            self.logger.debug(
                'Creating DownloadTask for route {!r} ...'.format(route))
            ctx = Context()
            self._ctx.append(ctx)

            t = RawDownloadTask(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=self.query_params),
                decode_unicode=True,
                context=ctx,
                keep_tempfiles=self._keep_tempfiles,
                http_method=self._http_method)

            # apply DownloadTask asynchronoulsy to the worker pool
            result = self._pool.apply_async(t)

            self._results.append(result)

        self._pool.close()

        # fetch results ready
        while True:
            ready = []
            for result in self._results:
                if result.ready():
                    _result = result.get()
                    if _result.status_code == 200:
                        if self._level in ('channel', 'response'):
                            # merge <Channel></Channel> elements into
                            # <Station></Station> from the correct
                            # <Network></Network> epoch element
                            for _net_element in self._extract_net_elements(
                                    _result.data):

                                # find the correct <Network></Network> epoch
                                # element
                                net_element, known = self._emerge_net_element(
                                    _net_element,
                                    exclude_tags=[
                                        '{}{}'.format(ns, self.STATION_TAG)
                                        for ns in
                                        settings.STATIONXML_NAMESPACES])

                                if not known:
                                    continue

                                # append/merge station elements
                                for sta_element in \
                                        self._emerge_sta_elements(
                                            _net_element):
                                    self._merge_sta_element(
                                        net_element,
                                        sta_element)

                        elif self._level == 'station':
                            # append <Station></Station> elements to the
                            # corresponding <Network></Network> epoch
                            for _net_element in self._extract_net_elements(
                                    _result.data):

                                net_element, known = self._emerge_net_element(
                                    _net_element,
                                    exclude_tags=[
                                        '{}{}'.format(ns, self.STATION_TAG)
                                        for ns in
                                        settings.STATIONXML_NAMESPACES])

                                if not known:
                                    continue

                                # append station elements
                                # NOTE(damb): <Station></Station> elements
                                # defined by multiple EIDA nodes are simply
                                # appended; no merging is performed
                                for sta_element in \
                                        self._emerge_sta_elements(
                                            _net_element):
                                    net_element.append(sta_element)

                        elif self._level == 'network':
                            for net_element in self._extract_net_elements(
                                    _result.data):
                                _, _ = self._emerge_net_element(net_element)

                        self._clean(_result)
                        self._sizes.append(_result.length)

                    else:
                        self._handle_error(_result)
                        self._sizes.append(0)

                    ready.append(result)

            for result in ready:
                self._results.remove(result)

            if not self._results:
                break

            if self._has_inactive_ctx():
                self.logger.debug('{}: Closing ...'.format(self.name))
                self._terminate()
                raise self.MissingContextLock

        self._pool.join()

        if not sum(self._sizes):
            self.logger.warning(
                'Task {!r} terminates with no valid result.'.format(self))
            return Result.nocontent(extras={'type_task': self._TYPE})

        _length = 0
        # dump xml tree for <Network></Network> epochs to temporary file
        self.path_tempfile = get_temp_filepath()
        self.logger.debug('{}: tempfile={!r}'.format(self, self.path_tempfile))
        with open(self.path_tempfile, 'wb') as ofd:
            for net_element in self._network_elements:
                s = etree.tostring(net_element)
                _length += len(s)
                ofd.write(s)

        if self._has_inactive_ctx():
            raise self.MissingContextLock

        self.logger.info(
            ('Task {!r} sucessfully finished '
             '(total bytes processed: {}, after processing: {}).').format(
                 self, sum(self._sizes), _length))

        return Result.ok(data=self.path_tempfile, length=_length,
                         extras={'type_task': self._TYPE})

    def _emerge_net_element(self, net_element, exclude_tags=[]):
        """
        Emerge a :code:`<Network></Network>` epoch element. If the
        :code:`<Network></Network>` element is unknown it is automatically
        appended to the list of already existing network elements.

        :param net_element: Emerge a network epoch element
        :type net_element: :py:class:`lxml.etree.Element`
        :param list exclude_tags: List of child element tags to be excluded
            while comparing
        :returns: Tuple of :code:`net_element` or a reference to an already
            existing network epoch element and a boolean value if the network
            element already is known (:code:`True`) else :code:`False`
        :rtype: tuple
        """
        for existing_net_element in self._network_elements:
            if elements_equal(
                net_element,
                existing_net_element,
                exclude_tags,
                    recursive=True):
                return existing_net_element, True

        self._network_elements.append(net_element)
        return net_element, False

    def _emerge_sta_elements(self, net_element,
                             namespaces=settings.STATIONXML_NAMESPACES):
        """
        Generator function emerging :code:`<Station><Station>` elements from
        :code:`<Network></Network>` tree.

        :param net_element: Network epoch `StationXML
        <http://www.fdsn.org/xml/station/>`_ element
        :type net_element: :py:class:`lxml.etree.Element`
        :param list namespaces: List of XML namespaces to be taken into
            consideration.
        """
        station_tags = ['{}{}'.format(ns, self.STATION_TAG)
                        for ns in namespaces]
        for tag in station_tags:
            for sta_element in net_element.findall(tag):
                yield sta_element

    def _emerge_cha_elements(self, sta_element,
                             namespaces=settings.STATIONXML_NAMESPACES):
        """
        Generator function emerging :code:`<Channel><Channel>` elements from
        :code:`<Station></Station>` tree.
        """
        channel_tags = ['{}{}'.format(ns, self.CHANNEL_TAG)
                        for ns in namespaces]
        for tag in channel_tags:
            for cha_element in sta_element.findall(tag):
                yield cha_element

    def _extract_net_elements(self, path_xml,
                              namespaces=settings.STATIONXML_NAMESPACES):
        """
        Extract :code:`<Network></Network>` epoch elements from `StationXML
        <http://www.fdsn.org/xml/station/>`_.

        :param str path_xml: Path to `StationXML
            <http://www.fdsn.org/xml/station/>`_ file.
        """
        network_tags = ['{}{}'.format(ns, self.NETWORK_TAG)
                        for ns in namespaces]

        with open(path_xml, 'rb') as ifd:
            station_xml = etree.parse(ifd).getroot()
            return [net_element
                    for net_element in station_xml.iter(*network_tags)]

    def _merge_sta_element(self, net_element, sta_element,
                           namespaces=settings.STATIONXML_NAMESPACES):
        """
        Merges a *StationXML* :code:`<Station></Station>` epoch element into a
        :code:`<Network></Network>` epoch element. Merging is performed
        recursively down to :code:`<Channel><Channel>` epochs.
        """
        # XXX(damb): Check if <Station></Station> epoch element is already
        # available - if not simply append.
        for _sta_element in net_element.iterfind(sta_element.tag):
            if elements_equal(sta_element,
                              _sta_element,
                              exclude_tags=[
                                  '{}{}'.format(ns, self.CHANNEL_TAG)
                                  for ns in namespaces],
                              recursive=False):
                # XXX(damb): Channels are ALWAYS appended; no merging is
                # performed
                for _cha_element in self._emerge_cha_elements(sta_element,
                                                              namespaces):
                    _sta_element.append(_cha_element)
                break

        else:
            net_element.append(sta_element)


# -----------------------------------------------------------------------------
class SplitAndAlignTask(TaskBase, ClientRetryBudgetMixin):
    """
    Base class for splitting and aligning (SAA) tasks.

    Concrete implementations of this task type implement stream epoch splitting
    and merging facilities.
    """
    _TYPE = ETask.SPLITALIGN
    LOGGER = 'flask.app.task_saa'

    DEFAULT_SPLITTING_CONST = 2

    def __init__(self, url, stream_epoch, query_params, **kwargs):
        super().__init__(self.LOGGER, **kwargs)
        self.query_params = query_params
        self.path_tempfile = get_temp_filepath()
        self._url = url
        self._stream_epoch_orig = stream_epoch
        self._endtime = kwargs.get('endtime', datetime.datetime.utcnow())

        self._splitting_const = self.DEFAULT_SPLITTING_CONST
        self._stream_epochs = []

        self._size = 0

    @property
    def url(self):
        return self._url

    @property
    def stream_epochs(self):
        return self._stream_epochs

    def split(self, stream_epoch, num):
        """
        Split a stream epoch's epoch into `num` epochs.

        :param stream_epoch: Stream epoch object to split
        :type stream_epoch: :py:class:`~eidangservices.utils.sncl.StreamEpoch`
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
                                   self._stream_epochs[idx + 1:])

        return stream_epochs

    def _handle_error(self, err):
        if self._keep_tempfiles not in (KeepTempfiles.ALL,
                                        KeepTempfiles.ON_ERRORS):
            try:
                os.remove(self.path_tempfile)
            except OSError:
                pass

        return Result.error(status='EndpointError',
                            status_code=err.response.status_code,
                            warning=str(err), data=err.response.data,
                            extras={'type_task': self._TYPE})

    def _run(self, stream_epoch):
        """
        Template method.
        """
        raise NotImplementedError

    @catch_default_task_exception
    @with_ctx_guard
    @with_client_retry_budget_validation
    def __call__(self):
        return self._run(self._stream_epoch_orig)


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
            except (OSError, IOError, ValueError):
                pass

            req = (request_handler.get()
                   if self._http_method == 'GET' else
                   request_handler.post())

            self.logger.debug(
                'Downloading (url={}, stream_epochs={}, method={!r}) '
                'to tempfile {!r}...'.format(
                    request_handler.url,
                    request_handler.stream_epochs,
                    self._http_method,
                    self.path_tempfile))

            try:
                with open(self.path_tempfile, 'ab') as ofd:
                    for chunk in stream_request(
                        req, hunk_size=self.CHUNK_SIZE, method='raw',
                            logger=self.logger):
                        if last_chunk is not None and last_chunk == chunk:
                            continue
                        self._size += len(chunk)
                        ofd.write(chunk)

            except RequestsError as err:
                code = (None if err.response is None else
                        err.response.status_code)
                if code == 413:
                    self.logger.info(
                        'Download failed (url={}, stream_epoch={}).'.format(
                            request_handler.url,
                            request_handler.stream_epochs))
                    self.update_cretry_budget(self.url, code)
                    self._run(stream_epoch)
                else:
                    return self._handle_error(err)
            else:
                code = 200
            finally:
                if code is not None:
                    self.update_cretry_budget(self.url, code)

            if stream_epoch in self.stream_epochs:
                self.logger.debug(
                    'Download (url={}, stream_epoch={}) finished.'.format(
                        request_handler.url,
                        request_handler.stream_epochs))

            if stream_epoch.endtime == self.stream_epochs[-1].endtime:
                return Result.ok(data=self.path_tempfile, length=self._size,
                                 extras={'type_task': self._TYPE})


class WFCatalogSplitAndAlignTask(SplitAndAlignTask):
    """
    SAA task implementation for a WFCatalog data stream. The task is
    implemented synchronously i.e. the task returns as soon as the last epoch
    segment is downloaded and aligned.

    .. note::

        The task requires parsing and analyzing (i.e. gradually loading)
        the stream of WFCatalog JSON objects.
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

            req = (request_handler.get()
                   if self._http_method == 'GET' else
                   request_handler.post())

            self.logger.debug(
                'Downloading (url={}, stream_epochs={}, method={!r}) '
                'to tempfile {!r}...'.format(
                    request_handler.url,
                    request_handler.stream_epochs,
                    self._http_method,
                    self.path_tempfile))
            try:
                with open(self.path_tempfile, 'ab') as ofd:
                    with raw_request(req, logger=self.logger) as ifd:

                        if self._last_obj is None:
                            ofd.write(self.JSON_LIST_START)
                            self._size += 1

                        for obj in ijson.items(ifd, 'item'):
                            # NOTE(damb): A python object has to be created
                            # since else we cannot compare objects. (JSON is
                            # unordered.)

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
                code = (None if err.response is None else
                        err.response.status_code)
                if code == 413:
                    self.logger.info(
                        'Download failed (url={}, stream_epoch={}).'.format(
                            request_handler.url,
                            request_handler.stream_epochs))

                    self.update_cretry_budget(self.url, code)
                    self._run(stream_epoch)
                else:
                    return self._handle_error(err)
            else:
                code = 200
            finally:
                if code is not None:
                    self.update_cretry_budget(self.url, code)

            if stream_epoch in self.stream_epochs:
                self.logger.debug(
                    'Download (url={}, stream_epoch={}) finished.'.format(
                        request_handler.url,
                        request_handler.stream_epochs))

            if stream_epoch.endtime == self.stream_epochs[-1].endtime:

                with open(self.path_tempfile, 'ab') as ofd:
                    ofd.write(self.JSON_LIST_END)
                    self._size += 1

                return Result.ok(data=self.path_tempfile, length=self._size,
                                 extras={'type_task': self._TYPE})


# -----------------------------------------------------------------------------
class RawDownloadTask(TaskBase, ClientRetryBudgetMixin):
    """
    Task downloading the data for a single StreamEpoch by means of streaming.

    :param bool decode_unicode: Decode the stream.
    """

    LOGGER = 'flask.app.federator.task_download_raw'

    CHUNK_SIZE = 1024 * 1024
    DECODE_UNICODE = False

    def __init__(self, request_handler, **kwargs):
        super().__init__(self.LOGGER, **kwargs)
        self._request_handler = request_handler
        self.chunk_size = kwargs.get('chunk_size', self.CHUNK_SIZE)
        self.decode_unicode = kwargs.get('decode_unicode', self.DECODE_UNICODE)

        self.path_tempfile = get_temp_filepath()
        self._size = 0

    @property
    def url(self):
        return self._request_handler.url

    @catch_default_task_exception
    @with_ctx_guard
    @with_client_retry_budget_validation
    def __call__(self):
        req = (self._request_handler.get()
               if self._http_method == 'GET' else self._request_handler.post())

        self.logger.debug(
            ('Downloading (url={}, stream_epochs={}, method={!r}) '
             'to tempfile {!r}...').
            format(self.url,
                   self._request_handler.stream_epochs,
                   self._http_method,
                   self.path_tempfile))

        try:
            self._run(req)
        except RequestsError as err:
            # set response code only if a connection could be established
            code = None if err.response is None else err.response.status_code
            return self._handle_error(err)
        else:
            code = 200
            self.logger.debug(
                'Download (url={}, stream_epochs={}) finished.'.format(
                    self.url,
                    self._request_handler.stream_epochs))
        finally:
            if code is not None:
                self.update_cretry_budget(self.url, code)

        return Result.ok(data=self.path_tempfile, length=self._size,
                         extras={'type_task': self._TYPE})

    def _handle_error(self, err):
        if self._keep_tempfiles not in (KeepTempfiles.ALL,
                                        KeepTempfiles.ON_ERRORS):
            try:
                os.remove(self.path_tempfile)
            except (TypeError, OSError):
                pass

        try:
            resp = err.response
            try:
                data = err.response.text
            except AttributeError:
                return Result.error('RequestsError',
                                    status_code=503,
                                    warning=type(err),
                                    data=str(err),
                                    extras={'type_task': self._TYPE,
                                            'req_handler':
                                            self._request_handler})

        except Exception as err:
            return Result.error('InternalServerError',
                                status_code=500,
                                warning='Unhandled exception.',
                                data=str(err),
                                extras={'type_task': self._TYPE,
                                        'req_handler': self._request_handler})
        else:
            if resp.status_code == 413:
                data = self._request_handler

            return Result.error(status='EndpointError',
                                status_code=resp.status_code,
                                warning=str(err), data=data,
                                extras={'type_task': self._TYPE,
                                        'req_handler': self._request_handler})

    def _run(self, req):
        """
        Template method performing the endpoint requests and dumping the result
        into a temporary file. The default implementation performs a *raw*
        download without any additional preprocessing.
        """

        with open(self.path_tempfile, 'wb') as ofd:
            for chunk in stream_request(
                    req,
                    chunk_size=self.chunk_size,
                    method='raw',
                    decode_unicode=self.decode_unicode,
                    logger=self.logger):
                self._size += len(chunk)
                ofd.write(chunk)


class StationTextDownloadTask(RawDownloadTask):
    """
    Download data from an endpoint. In addition this task removes header
    information from the response.
    """

    def _run(self, req):
        """
        Removes ``fdsnws-station`` ``format=text`` headers while downloading.
        """

        with open(self.path_tempfile, 'wb') as ofd:
            # NOTE(damb): For granular fdnsws-station-text request it seems
            # ok buffering the entire response in memory.
            with binary_request(req, logger=self.logger) as ifd:
                for line in ifd:
                    self._size += len(line)
                    if line.startswith(b'#'):
                        continue
                    ofd.write(line.strip() + b'\n')


class StationXMLDownloadTask(RawDownloadTask):
    """
    Download `StationXML <https://www.fdsn.org/xml/station/>`_ from an
    endpoint. Emerge :code:`<Network></Network>` epoch specific data from
    `StationXML <https://www.fdsn.org/xml/station/>`_.

    .. note::

        Network epoch extraction is performed stream based using a `SAX parser
        <https://lxml.de/api/lxml.etree.iterparse-class.html>`_.
    """
    NETWORK_TAG = settings.STATIONXML_ELEMENT_NETWORK

    def __init__(self, request_handler, **kwargs):
        super().__init__(request_handler, **kwargs)
        self.name = '{}-{}'.format(type(self).__name__,
                                   kwargs.get('name', 'UNKOWN'))
        network_tag = kwargs.get('network_tag', self.NETWORK_TAG)
        self._network_tags = ['{}{}'.format(ns, network_tag)
                              for ns in settings.STATIONXML_NAMESPACES]

    def _run(self, req):
        """
        Extracts ``Network`` elements from StationXML.
        """
        with open(self.path_tempfile, 'wb') as ofd:
            # XXX(damb): Load the entire result into memory.
            with binary_request(req, logger=self.logger) as ifd:
                for event, net_element in etree.iterparse(
                        ifd, tag=self._network_tags):
                    if event == 'end':
                        s = etree.tostring(net_element)
                        self._size += len(s)
                        ofd.write(s)
