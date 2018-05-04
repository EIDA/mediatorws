# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <stationlite.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
#
# eida-stationlite is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# eida-stationlite is distributed in the hope that it will be useful,
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
#
# REVISION AND CHANGES
# 2017/12/15        V0.1    Daniel Armbruster
# =============================================================================
"""
Implementation of a *StationLite* resource.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import collections
import logging

from flask import request
from flask_restful import Resource
from webargs.flaskparser import use_args

import eidangservices as eidangws
from eidangservices import settings, utils
from eidangservices.utils import httperrors
from eidangservices.utils.sncl import StreamEpochsHandler

from eidangservices.stationlite import misc
from eidangservices.stationlite.engine import dbquery
from eidangservices.stationlite.server import db, schema
from eidangservices.stationlite.server.stream import OutputStream


class StationLiteResource(Resource):
    """Service query for routing."""

    LOGGER = 'flask.app.stationlite.stationlite_resource'

    def __init__(self):
        super(StationLiteResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    # __init__ ()

    @use_args(schema.StationLiteSchema(), locations=('query',))
    @utils.use_fdsnws_kwargs(
        eidangws.utils.schema.ManyStreamEpochSchema(
            context={'request': request}),
        locations=('query',)
    )
    def get(self, args, stream_epochs):
        """
        Process a *StationLite* GET request.
        """
        self.logger.debug('StationLiteSchema: %s' % args)
        self.logger.info('StreamEpoch objects: %s' % stream_epochs)

        response = self._process_request(args, stream_epochs)
        if not response:
            raise httperrors.NoDataError()

        return misc.get_response(response, settings.MIMETYPE_TEXT)

    # get ()

    @utils.use_fdsnws_args(schema.StationLiteSchema(), locations=('form',))
    @utils.use_fdsnws_kwargs(
        eidangws.utils.schema.ManyStreamEpochSchema(
            context={'request': request}),
        locations=('form',)
    )
    def post(self, args, stream_epochs):
        """
        Process a *StationLite* POST request.
        """
        self.logger.debug('StationLiteSchema: %s' % args)
        self.logger.info('StreamEpoch objects: %s' % stream_epochs)

        response = self._process_request(args, stream_epochs)
        if not response:
            raise httperrors.NoDataError()

        return misc.get_response(response, settings.MIMETYPE_TEXT)

    # post ()

    def _process_request(self, args, stream_epochs):
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
            merged_routes[url] = [se for ses in stream_epochs for se in ses]

        # sort response
        routes = [utils.Route(url=url,
                              streams=sorted(stream_epochs))
                  for url, stream_epochs in merged_routes.items()]
        # sort additionally by url
        routes.sort()

        ostream = OutputStream.create(args['format'], routes=routes)
        return str(ostream)

    # _process_request ()

# class StationLiteResource

# ---- END OF <stationlite.py> ----
