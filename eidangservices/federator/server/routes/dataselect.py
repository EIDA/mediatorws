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

import flask
from flask import request
from webargs.flaskparser import use_args

from eidangservices import settings
from eidangservices.federator.server import \
        general_request, schema, httperrors, misc


class DataselectResource(general_request.GeneralResource):
    """
    Handler for dataselect service route.
    
    """
    LOGGER = 'flask.app.federator.dataselect_resource'

    def __init__(self):
        super(DataselectResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.DataselectSchema(), locations=('query',))
    @misc.use_fdsnws_kwargs(
        schema.ManySNCLSchema(context={'request': request}),
        locations=('query',)
    )
    def get(self, args, sncls):
        # request.method == 'GET'

        self.logger.debug('SNCLs: %s' % sncls)

        # serialize objects
        s = schema.DataselectSchema()
        args = s.dump(args).data
        self.logger.debug('DataselectSchema (serialized): %s' % args)

        # process request
        return self._process_request(args, sncls, settings.DATASELECT_MIMETYPE,
                                     path_tempfile=self.path_tempfile)

    # get ()

        
    @misc.use_fdsnws_args(schema.DataselectSchema(), locations=('form',))
    @misc.use_fdsnws_kwargs(
        schema.ManySNCLSchema(context={'request': request}),
        locations=('form',)
    )
    def post(self, args, sncls):
        # request.method == 'POST'
        # NOTE: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"

        s = schema.DataselectSchema()
        args = s.dump(args).data
        self.logger.debug('DataselectSchema (serialized): %s' % args)

        return self._process_request(args, sncls, settings.DATASELECT_MIMETYPE,
                                     path_tempfile=self.path_tempfile,
                                     post=True)

    # post ()

# class DataselectResource
