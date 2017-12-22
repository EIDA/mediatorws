# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <stationlite.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
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
#
# REVISION AND CHANGES
# 2017/12/15        V0.1    Daniel Armbruster
# =============================================================================
"""
This file is part of the EIDA mediator/federator webservices.
"""
import logging

from flask import request
from flask_restful import Resource
from webargs.flaskparser import use_args

import eidangservices as eidangws
from eidangservices import settings, utils

from eidangservices.stationlite.engine import dbquery
from eidangservices.stationlite.server import schema
from eidangservices.stationlite import misc


class StationLiteResource(Resource):
    """Service query for routing."""
    
    LOGGER = 'flask.app.stationlite.stationlite_resource'

    def __init__(self):
        super(StationLiteResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    # __init__ ()

    @use_args(schema.StationLiteSchema(), locations=('query',))
    @utils.use_fdsnws_kwargs(
        eidangws.schema.ManySNCLSchema(context={'request': request}),
        locations=('query',)
    )
    def get(self, args, sncls):
        """
        Process a *StationLite* GET request.
        """
        self.logger.debug('StationLiteSchema: %s' % args)
        self.logger.debug('SNCLs: %s' % sncls)

        # TODO(damb): approach:
        # convert sncl to a sncl schema

        db_engine, db_connection, db_tables = misc.get_db()
        
        # TODO(fab): put in "real" query for SNCL at al.
        # this is an simple example query that lists all networks
        net = dbquery.find_networks(db_connection, db_tables)
        
        return misc.get_response(str(net), settings.MIMETYPE_TEXT)

    # get ()

    @utils.use_fdsnws_args(schema.StationLiteSchema(), locations=('form',))
    @utils.use_fdsnws_kwargs(
        eidangws.schema.ManySNCLSchema(context={'request': request}),
        locations=('form',)
    )
    def post(self, args, sncls): 
        """
        Process a *StationLite* POST request.
        """
        self.logger.debug('StationLiteSchema: %s' % args)
        self.logger.debug('SNCLs: %s' % sncls)

        # TODO(damb): to be implemented

        return misc.get_response('post', settings.MIMETYPE_TEXT)

    # post ()

# class StationLiteResource

# ---- END OF <stationlite.py> ----
