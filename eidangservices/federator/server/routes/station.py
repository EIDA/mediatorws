# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <station.py>
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
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import logging

from flask import request
from flask_restful import Resource
from webargs.flaskparser import use_args

from eidangservices import settings
from eidangservices.federator.server.schema import StationSchema
from eidangservices.federator.server.process import RequestProcessor
from eidangservices.utils import fdsnws
from eidangservices.utils.schema import ManyStreamEpochSchema


class StationResource(Resource):

    LOGGER = 'flask.app.federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(StationSchema(), locations=('query',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('query',)
    )
    @fdsnws.with_fdsnws_exception_handling(settings.EIDA_FEDERATOR_SERVICE_ID)
    def get(self, args, stream_epochs):
        # request.method == 'GET'
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        s = StationSchema()
        args = s.dump(args)
        self.logger.debug('StationSchema (serialized): %s' % args)

        # process request
        return RequestProcessor.create(args['service'],
                                       self._get_result_mimetype(args),
                                       query_params=args,
                                       stream_epochs=stream_epochs,
                                       post=False).streamed_response

    # get ()

    @fdsnws.use_fdsnws_args(StationSchema(), locations=('form',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('form',)
    )
    @fdsnws.with_fdsnws_exception_handling(settings.EIDA_FEDERATOR_SERVICE_ID)
    def post(self, args, stream_epochs):
        # request.method == 'POST'
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        # serialize objects
        s = StationSchema()
        args = s.dump(args)
        self.logger.debug('StationSchema (serialized): %s' % args)

        # process request
        return RequestProcessor.create(args['service'],
                                       self._get_result_mimetype(args),
                                       query_params=args,
                                       stream_epochs=stream_epochs,
                                       post=True).streamed_response

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

# ---- END OF <station.py> ----
