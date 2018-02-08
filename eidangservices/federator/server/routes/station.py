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

import logging

from flask import request
from webargs.flaskparser import use_args

import eidangservices as eidangws

from eidangservices import settings, utils
from eidangservices.federator.server import general_request, schema


class StationResource(general_request.GeneralResource):

    LOGGER = 'flask.app.federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.StationSchema(), locations=('query',))
    @utils.use_fdsnws_kwargs(
        eidangws.utils.schema.ManyStreamEpochSchema(
            context={'request': request}),
        locations=('query',)
    )
    def get(self, station_args, stream_epochs):
        # request.method == 'GET'
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        s = schema.StationSchema()
        station_args = s.dump(station_args).data
        self.logger.debug('StationSchema (serialized): %s' % station_args)

        # process request
        return self._process_request(station_args, stream_epochs,
                                     self._get_result_mimetype(station_args),
                                     path_tempfile=self.path_tempfile)

    # get ()

    @utils.use_fdsnws_args(schema.StationSchema(), locations=('form',))
    @utils.use_fdsnws_kwargs(
        eidangws.utils.schema.ManyStreamEpochSchema(
            context={'request': request}),
        locations=('form',)
    )
    def post(self, station_args, stream_epochs):
        # request.method == 'POST'

        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        # serialize objects
        s = schema.StationSchema()
        station_args = s.dump(station_args).data
        self.logger.debug('StationSchema (serialized): %s' % station_args)

        return self._process_request(station_args, stream_epochs,
                                     self._get_result_mimetype(station_args),
                                     path_tempfile=self.path_tempfile,
                                     post=True)

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
