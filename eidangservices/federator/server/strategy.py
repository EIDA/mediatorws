# -*- coding: utf-8 -*-
"""
Facilities for route based requesting strategies.
"""

import collections
import datetime
import logging

from eidangservices import utils, settings
from eidangservices.federator import __version__
from eidangservices.federator.server import response_code_stats
from eidangservices.federator.server.misc import (
    Context, ContextLoggerAdapter)
from eidangservices.federator.server.request import (
    GranularFdsnRequestHandler, BulkFdsnRequestHandler)
from eidangservices.utils.httperrors import FDSNHTTPError
from eidangservices.utils.request import (binary_request, RequestsError,
                                          NoContent)
from eidangservices.utils.error import ErrorWithTraceback
from eidangservices.utils.sncl import StreamEpoch


def demux_routes(routing_table):
    return [utils.Route(url, streams=[se])
            for url, streams in routing_table.items()
            for se in streams]


def group_routes_by(routing_table, key='network'):
    """
    Group routes by a certain :py:class:`eidangservices.sncl.Stream` keyword.
    Combined keywords are also possible e.g. network.station. When combining
    keys the seperating character is `.`. Routes are demultiplexed.

    :param dict routing_table: Routing table
    :param str key: Key used for grouping.
    """
    SEP = '.'

    routes = demux_routes(routing_table)
    retval = collections.defaultdict(list)

    for route in routes:
        try:
            _key = getattr(route.streams[0].stream, key)
        except AttributeError:
            try:
                if SEP in key:
                    # combined key
                    _key = SEP.join(getattr(route.streams[0].stream, k)
                                    for k in key.split(SEP))
                else:
                    raise KeyError(
                        'Invalid separator. Must be {!r}.'.format(SEP))
            except (AttributeError, KeyError) as err:
                raise RequestStrategyError(err)

        retval[_key].append(route)

    return retval


def _mux_routes(routing_table):
    retval = collections.defaultdict(list)
    for net, _routes in group_routes_by(
            routing_table, key='network').items():
        # sort by url
        mux_routes = collections.defaultdict(list)
        for r in _routes:
            mux_routes[r.url].append(r.streams[0])

        for url, ses in mux_routes.items():
            retval[net].append(utils.Route(url=url, streams=ses))

    return retval


class RequestStrategyError(ErrorWithTraceback):
    """Base RequestStrategy error ({})."""


class RoutingError(RequestStrategyError):
    """Error while routing ({})."""


# -----------------------------------------------------------------------------
class RequestStrategyBase:
    """
    Request strategy encapsulating routing and requesting.
    """

    LOGGER = "flask.app.federator.strategy"

    def __init__(self, **kwargs):
        """
        :param ctx: Request context the strategy is used

        :param default_endtime: Default endtime to be used if the stream epochs
            have an undefined :code:`endtime`
        :param str logger: Logger name
        """

        self._ctx = kwargs.get('context')

        self._logger = logging.getLogger(
            self.LOGGER if kwargs.get('logger') is None
            else kwargs.get('logger'))
        self.logger = (ContextLoggerAdapter(self._logger, {'ctx': self._ctx})
                       if self._ctx else self._logger)

        self._default_endtime = kwargs.get('default_endtime',
                                           datetime.datetime.utcnow())

        self._routing_table_raw = {}

    @property
    def routing_table(self):
        """
        Returns the strategy's *raw* routing table.

        :rtype: dict
        """
        return self._routing_table_raw

    def _route(self, req, post=True, **kwargs):
        """
        Route a request and create a routing table. Routing is performed by
        means of the routing service provided.

        :param req: Routing service request handler
        :type req: :py:class:`RoutingRequestHandler`
        :param bool post: Execute a the request to the routing service via HTTP
            POST

        :raises NoContent: If no routes are available
        :raises RequestsError: General exception if request to routing service
            failed
        """

        _req = (req.post() if post else req.get())

        routing_table = {}
        self.logger.info("Fetching routes from %s" % req.url)
        try:
            with binary_request(_req) as fd:
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
                            routing_table[urlline] = stream_epochs

                        urlline = None
                        stream_epochs = []

                        if not line:
                            break
                    else:
                        # XXX(damb): Do not substitute an empty endtime when
                        # performing HTTP GET requests in order to guarantee
                        # more cache hits (if eida-federator is coupled with
                        # HTTP caching proxy).
                        stream_epochs.append(
                            StreamEpoch.from_snclline(line, default_endtime=(
                                self._default_endtime if post else None)))

        except NoContent as err:
            self.logger.warning(err)
            nodata = int(
                kwargs.get('nodata',
                           settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE))
            raise FDSNHTTPError.create(nodata)
        except RequestsError as err:
            self.logger.error(err)
            raise FDSNHTTPError.create(500, service_version=__version__)
        else:
            self.logger.debug(
                'Number of routes received: {}'.format(len(routing_table)))

        return routing_table

    def route(self, req, retry_budget_client=100, **kwargs):
        """
        Route a request and create a routing table. Routing is performed by
        means of the routing service provided. Since the
        :py:meth:`~RequestStrategy._route` returns the number of routes to be
        processed, :py:class:`~process.RequestProcessor` instances can scale
        their worker pool sizes appropriately.

        :param req: Routing service request handler
        :type req: :py:class:`RoutingRequestHandler`
        :param float retry_budget_client: Per client retry-budget the
            ``routing_table`` is filtered with

        :param bool post: Request data by means of HTTP POST.

        :returns: Number of routes
        :rtype: int
        """

        raise NotImplementedError

    def request(self, pool, tasks, query_params={}, **kwargs):
        """
        Execute requests.

        :param pool: Worker pool tasks are applied to
        :param dict tasks: Mapping of concrete tasks.
        :param dict query_params: Query parameters

        :returns: Asynchronous task results
        """

        raise NotImplementedError

    @staticmethod
    def _get_task_by_kw(tasks, kw):
        """
        Utility method returning the task by keyword.
        """
        try:
            t = tasks[kw]
        except KeyError as err:
            raise RequestStrategyError(err)
        else:
            return t

    def _filter_by_client_retry_budget(
            self, routing_table, retry_budget_client):
        """
        Filter ``routing_table`` based on a per-client retry budget.

        :param dict routing_table: Routing table to be filtered and modified
            in-place
        :param float retry_budget_client: Per client retry-budget the
            ``routing_table`` is filtered with. If the budget is equal to 100
            percent, then no filtering is performed at all.
        """

        if retry_budget_client == 100:
            return

        routed_urls = list(routing_table.keys())
        error_ratios = {url: response_code_stats.get_error_ratio(url)
                        for url in routed_urls}

        for url in routed_urls:
            if error_ratios[url] > retry_budget_client:
                self.logger.debug(
                    'Removing route (URL={}) due to past client retry budget: '
                    '({} > {})'.format(url, error_ratios[url],
                                       retry_budget_client))
                del routing_table[url]


class GranularRequestStrategy(RequestStrategyBase):
    """
    Fetch data using a granular endpoint request strategy.
    """

    def route(self, req, retry_budget_client=100, **kwargs):
        """
        Implements fully demultiplexed routing.
        """

        routing_table = super()._route(req, **kwargs)
        self._filter_by_client_retry_budget(routing_table, retry_budget_client)
        self._routing_table_raw = routing_table

        self._routes = demux_routes(routing_table)

        return len(self._routes)

    def request(self, pool, tasks, query_params={}, **kwargs):
        """
        Issue granular endpoint requests.
        """

        assert hasattr(self, '_routes'), 'Missing routes.'

        default_task = self._get_task_by_kw(tasks, 'default')

        retval = []
        for route in self._routes:
            self.logger.debug(
                'Creating {!r} for {!r} ...'.format(default_task, route))
            ctx = Context()
            self._ctx.append(ctx)
            t = default_task(
                GranularFdsnRequestHandler(
                    route.url,
                    route.streams[0],
                    query_params=query_params),
                context=ctx,
                **kwargs)
            result = pool.apply_async(t)
            retval.append(result)

        return retval


class NetworkBulkRequestStrategy(RequestStrategyBase):
    """
    Strategy executing bulk endpoint requests on network code granularity.
    """

    def route(self, req, retry_budget_client=100, **kwargs):
        """
        Multiplexed routing i.e. one route contains multiple stream epochs
        (for a unique network code). Implements bulk request routing based on
        network codes.
        """

        # NOTE(damb): We firstly group routes by network code. Afterwards,
        # grouped routes are multiplexed by network code, again.
        routing_table = super()._route(req, **kwargs)
        self._filter_by_client_retry_budget(routing_table, retry_budget_client)
        self._routing_table_raw = routing_table

        self._routes = _mux_routes(routing_table)

        return len(self._routes)

    def request(self, pool, tasks, query_params={}, **kwargs):
        """
        Issue a bulk endpoint request with network granularity.
        """

        assert hasattr(self, '_routes'), 'Missing routes.'

        default_task = self._get_task_by_kw(tasks, 'default')

        http_method = kwargs.pop(
            'http_method',
            settings.EIDA_FEDERATOR_DEFAULT_HTTP_METHOD)
        if http_method == 'GET':
            self.logger.debug(
                'Force HTTP POST endpoint requests.')

        retval = []
        for net, bulk_routes in self._routes.items():
            self.logger.debug(
                'Creating tasks for net={!r} ...'.format(net))

            for bulk_route in bulk_routes:
                self.logger.debug(
                    'Creating {!r} for {!r} ...'.format(
                        default_task, bulk_route))

                ctx = Context()
                self._ctx.append(ctx)

                # NOTE(damb): For bulk requests there's only http_method='POST'
                t = default_task(
                    BulkFdsnRequestHandler(
                        bulk_route.url,
                        stream_epochs=bulk_route.streams,
                        query_params=query_params),
                    context=ctx, http_method='POST', **kwargs)
                result = pool.apply_async(t)
                retval.append(result)

        return retval


class AdaptiveNetworkBulkRequestStrategy(NetworkBulkRequestStrategy):
    """
    Adaptive request strategy executing bulk endpoint requests on network code
    granularity. For distributed physical networks a executing endpoint
    requests is delegated to a secondary task.
    """

    def route(self, req, retry_budget_client=100, **kwargs):
        """
        Demultiplex routes for distributed physical networks.
        """
        routing_table = super()._route(req, **kwargs)
        self._filter_by_client_retry_budget(routing_table, retry_budget_client)
        self._routing_table_raw = routing_table

        self._routes = {}
        for net, _routes in _mux_routes(routing_table).items():
            if len(_routes) > 1:
                # demux routes
                self._routes[net] = [utils.Route(route.url, streams=[se])
                                     for route in _routes
                                     for se in route.streams]
            else:
                self._routes[net] = _routes

        return len(self._routes)

    def request(self, pool, tasks, query_params={}, **kwargs):
        """
        Issue a bulk endpoint request with network code granularity. For
        distributed physical networks a request execution is delegated to a
        secondary-level task.
        """
        assert hasattr(self, '_routes'), 'Missing routes.'

        default_task = self._get_task_by_kw(tasks, 'default')
        combining_task = self._get_task_by_kw(tasks, 'combining')

        http_method = kwargs.pop(
            'http_method',
            settings.EIDA_FEDERATOR_DEFAULT_HTTP_METHOD)

        retval = []

        for net, routes in self._routes.items():
            # create subcontext
            ctx = Context()
            self._ctx.append(ctx)

            if len(routes) == 1:
                if http_method == 'GET':
                    self.logger.debug(
                        'Force HTTP POST endpoint requests.')

                self.logger.debug(
                    'Creating {!r} for net={!r} ...'.format(
                        default_task, net))
                # NOTE(damb): For bulk requests there's only http_method='POST'
                t = default_task(
                    BulkFdsnRequestHandler(
                        routes[0].url, stream_epochs=routes[0].streams,
                        query_params=query_params),
                    context=ctx, name=net, http_method='POST', **kwargs)

            elif len(routes) > 1:
                self.logger.debug(
                    'Creating {!r} for net={!r} ...'.format(
                        combining_task, net))
                t = combining_task(
                    routes, query_params, name=net, context=ctx,
                    http_method=http_method, **kwargs)
            else:
                raise RoutingError('Missing routes.')

            result = pool.apply_async(t)
            retval.append(result)

        return retval


class NetworkCombiningRequestStrategy(RequestStrategyBase):
    """
    Request strategy implementing data merging on a network level granularity.
    """

    def route(self, req, retry_budget_client=100, **kwargs):
        routing_table = super()._route(req, **kwargs)
        self._filter_by_client_retry_budget(routing_table, retry_budget_client)
        self._routing_table_raw = routing_table

        self._routes = group_routes_by(routing_table, key='network')

        return len(self._routes)

    def request(self, pool, tasks, query_params={}, **kwargs):
        """
        Issue combining tasks. Issuing endpoint requests is delegated to those
        tasks.
        """
        assert hasattr(self, '_routes'), 'Missing routes.'

        combining_task = self._get_task_by_kw(tasks, 'combining')

        retval = []
        for net, routes in self._routes.items():
            ctx = Context()
            self._ctx.append(ctx)
            self.logger.debug(
                'Creating {!r} for net={!r} ...'.format(combining_task, net))
            t = combining_task(
                routes, query_params, name=net, context=ctx, **kwargs)
            result = pool.apply_async(t)
            retval.append(result)

        return retval
