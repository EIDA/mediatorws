# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
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
# -----------------------------------------------------------------------------
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging

from flask import request
from webargs.flaskparser import use_args

from eidangservices import settings
from eidangservices.federator.server import \
        general_request, schema, httperrors, misc


class StationResource(general_request.GeneralResource):

    LOGGER = 'flask.app.federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.StationSchema(), locations=('query',))
    def get(self, sncl_args, station_args):
        # request.method == 'GET'
        _context = {'request': request}

        args = {}
        # serialize objects
        s = schema.SNCLSchema(context=_context)
        args.update(s.dump(sncl_args).data)
        self.logger.debug('SNCLSchema (serialized): %s' % 
                s.dump(sncl_args).data)

        s = schema.StationSchema(context=_context)
        args.update(s.dump(station_args).data)
        self.logger.debug('StationSchema (serialized): %s' % 
                s.dump(station_args).data)

        # process request
        self.logger.debug('Request args: %s' % args)
        return self._process_request(args, self._get_result_mimetype(args), 
            path_tempfile=self.path_tempfile)

    # get ()

    @misc.use_fdsnws_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('form',)
    )
    @misc.use_fdsnws_args(schema.StationSchema(), locations=('form',))
    def post(self, sncl_args, station_args):
        # request.method == 'POST'

        # serialize objects
        s = schema.SNCLSchema()
        sncl_args = s.dump(sncl_args).data
        self.logger.debug('SNCLSchema (serialized): %s' % sncl_args)
        
        s = schema.StationSchema()
        station_args = s.dump(station_args).data
        self.logger.debug('StationSchema (serialized): %s' % station_args)
        self.logger.debug('Request args: %s' % station_args)

        # merge SNCL parameters
        sncls = misc.convert_sncl_dict_to_lines(sncl_args)
        self.logger.debug('SNCLs: %s' % sncls)
        sncls = '\n'.join(sncls) 

        return self._process_request(station_args,
                self._get_result_mimetype(station_args), 
                path_tempfile=self.path_tempfile,
                postdata=sncls)

    # post ()
    
    def _get_result_mimetype(self, args):
        """Return result mimetype (either XML or plain text."""
        try:
            args['format'] == 'text'
            return settings.STATION_MIMETYPE_TEXT
        except KeyError:
            return settings.STATION_MIMETYPE_XML

    # _get_result_mimetype () 
            
# class StationResource
