# -*- coding: utf-8 -*-
"""
Implementation of a *StationLite* resource.
"""

import collections
import logging

from flask import request
from flask_restful import Resource
from webargs.flaskparser import use_args

import eidangservices as eidangws
from eidangservices import settings, utils
from eidangservices.utils import fdsnws
from eidangservices.utils.httperrors import FDSNHTTPError
from eidangservices.utils.strict import with_strict_args
from eidangservices.utils.sncl import StreamEpochsHandler, StreamEpoch

from eidangservices.stationlite import __version__
from eidangservices.stationlite import misc
from eidangservices.stationlite.engine import dbquery
from eidangservices.stationlite.server import db, schema
from eidangservices.stationlite.server.stream import OutputStream


class StationLiteResource(Resource):
    """
    Service query for routing.
    """

    LOGGER = 'flask.app.stationlite.stationlite_resource'

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.StationLiteSchema(), locations=('query',))
    @fdsnws.use_fdsnws_kwargs(
        eidangws.utils.schema.ManyStreamEpochSchema(
            context={'request': request}),
        locations=('query',)
    )
    @with_strict_args(
        (eidangws.utils.schema.StreamEpochSchema, schema.StationLiteSchema),
        locations=('query',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self, args, stream_epochs):
        """
        Process a *StationLite* GET request.
        """
        self.logger.debug('StationLiteSchema: %s' % args)
        self.logger.info('StreamEpoch objects: %s' % stream_epochs)

        response = self._process_request(
            args, stream_epochs,
            netloc_proxy=args['proxynetloc'])

        if not response:
            self._handle_nodata(args)

        return misc.get_response(response, settings.MIMETYPE_TEXT)

    @fdsnws.use_fdsnws_args(schema.StationLiteSchema(), locations=('form',))
    @fdsnws.use_fdsnws_kwargs(
        eidangws.utils.schema.ManyStreamEpochSchema(
            context={'request': request}),
        locations=('form',)
    )
    @with_strict_args(
        schema.StationLiteSchema,
        locations=('form',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self, args, stream_epochs):
        """
        Process a *StationLite* POST request.
        """
        self.logger.debug('StationLiteSchema: %s' % args)
        self.logger.info('StreamEpoch objects: %s' % stream_epochs)

        response = self._process_request(
            args, stream_epochs,
            netloc_proxy=args['proxynetloc'])

        if not response:
            self._handle_nodata(args)

        return misc.get_response(response, settings.MIMETYPE_TEXT)

    def _handle_nodata(self, args):
        raise FDSNHTTPError.create(
            int(
                args.get('nodata',
                         settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE)))

    def _process_request(
            self, args, stream_epochs, netloc_proxy=None):
        # resolve virtual network streamepochs
        vnet_stream_epochs = []
        for stream_epoch in stream_epochs:
            self.logger.debug(
                'Resolving {0!r} regarding VNET.'.format(stream_epoch))
            vnet_stream_epochs.extend(
                dbquery.resolve_vnetwork(db.session, stream_epoch))

        self.logger.debug('Stream epochs from VNETs: '
                          '{0!r}'.format(vnet_stream_epochs))

        stream_epochs.extend(vnet_stream_epochs)

        # collect results for each stream epoch
        routes = []
        for stream_epoch in stream_epochs:
            self.logger.debug('Processing request for %r' % (stream_epoch,))
            # query
            _routes = dbquery.find_streamepochs_and_routes(
                db.session, stream_epoch, args['service'],
                level=args['level'], access=args['access'],
                minlat=args['minlatitude'],
                maxlat=args['maxlatitude'],
                minlon=args['minlongitude'],
                maxlon=args['maxlongitude'])

            # adjust stream_epoch regarding time_constraints
            for url, streams in _routes:
                streams.modify_with_temporal_constraints(
                    start=stream_epoch.starttime,
                    end=stream_epoch.endtime)
            routes.extend(_routes)

        # flatten response list
        self.logger.debug('StationLite routes: %s' % routes)

        # merge stream epochs for each route
        merged_routes = collections.defaultdict(StreamEpochsHandler)
        for url, stream_epochs in routes:
            merged_routes[url].merge(stream_epochs)

        self.logger.debug('StationLite routes (merged): %r' % merged_routes)

        for url, stream_epochs in merged_routes.items():
            if args['level'] in ('network', 'station'):
                merged_routes[url] = [StreamEpoch.from_streamepochs(ses)
                                      for ses in stream_epochs]
            else:
                merged_routes[url] = [se for ses in stream_epochs
                                      for se in ses]

        # sort response
        routes = [utils.Route(url=url,
                              streams=sorted(stream_epochs))
                  for url, stream_epochs in merged_routes.items()]

        # sort additionally by url
        routes.sort()

        ostream = OutputStream.create(
            args['format'], routes=routes, netloc_proxy=netloc_proxy)
        return str(ostream)
