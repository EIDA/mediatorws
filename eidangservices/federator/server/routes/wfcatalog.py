# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <wfcatalog.py>
# -----------------------------------------------------------------------------
#
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
#
# REVISION AND CHANGES
# 2017/10/26        V0.1    Daniel Armbruster
# =============================================================================
"""
This file is part of the EIDA mediator/federator webservices.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import datetime
import logging

from flask import request
from flask_restful import Resource
from webargs.flaskparser import use_args

from eidangservices import settings, utils
from eidangservices.federator.server.schema import WFCatalogSchema
from eidangservices.federator.server.process import RequestProcessor
from eidangservices.utils.httperrors import BadRequestError
from eidangservices.utils.schema import ManyStreamEpochSchema


class WFCatalogResource(Resource):
    """
    Implementation of a `WFCatalog
    <https://www.orfeus-eu.org/data/eida/webservices/wfcatalog/>`_ resource.
    """

    LOGGER = 'flask.app.federator.wfcatalog_resource'

    def __init__(self):
        super(WFCatalogResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(WFCatalogSchema(), locations=('query',))
    @utils.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('query',)
    )
    def get(self, args, stream_epochs):
        """
        Process a *WFCatalog* GET request.
        """
        # request.method == 'GET'

        # sanity check - starttime and endtime must be specified
        if (not stream_epochs or stream_epochs[0].starttime is None or
                stream_epochs[0].endtime is None):
            raise BadRequestError(service_id='federator')

        self.logger.debug('StreamEpoch objects: %r' % stream_epochs)

        # serialize objects
        s = WFCatalogSchema()
        args = s.dump(args)
        self.logger.debug('WFCatalogSchema (serialized): %s' % args)

        # process request
        return RequestProcessor.create(args['service'],
                                       settings.WFCATALOG_MIMETYPE,
                                       query_params=args,
                                       stream_epochs=stream_epochs,
                                       post=False).streamed_response

    # get ()

    @utils.use_fdsnws_args(WFCatalogSchema(), locations=('form',))
    @utils.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('form',)
    )
    def post(self, args, stream_epochs):
        """
        Process a *WFCatalog* POST request.
        """
        # request.method == 'POST'
        # NOTE: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        self.logger.debug('StreamEpoch objects: %r' % stream_epochs)

        # serialize objects
        s = WFCatalogSchema()
        args = s.dump(args)
        self.logger.debug('WFCatalogSchema (serialized): %s' % args)

        # process request
        return RequestProcessor.create(args['service'],
                                       settings.WFCATALOG_MIMETYPE,
                                       query_params=args,
                                       stream_epochs=stream_epochs,
                                       post=True).streamed_response

    # post ()

# class WFCatalogResource

# ---- END OF <wfcatalog.py> ----
