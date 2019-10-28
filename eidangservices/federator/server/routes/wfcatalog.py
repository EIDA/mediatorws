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

import logging

from flask import current_app, g, request
from flask_restful import Resource
from webargs.flaskparser import use_args

from eidangservices import settings
from eidangservices.federator import __version__
from eidangservices.federator.server.misc import ContextLoggerAdapter
from eidangservices.federator.server.schema import WFCatalogSchema
from eidangservices.federator.server.process import RequestProcessor
from eidangservices.utils import fdsnws
from eidangservices.utils.httperrors import FDSNHTTPError
from eidangservices.utils.strict import with_strict_args
from eidangservices.utils.schema import (ManyStreamEpochSchema,
                                         StreamEpochSchema)


class WFCatalogResource(Resource):
    """
    Implementation of a `WFCatalog
    <https://www.orfeus-eu.org/data/eida/webservices/wfcatalog/>`_ resource.
    """

    LOGGER = 'flask.app.federator.wfcatalog_resource'

    def __init__(self):
        super(WFCatalogResource, self).__init__()
        self._logger = logging.getLogger(self.LOGGER)
        self.logger = ContextLoggerAdapter(self._logger, {'ctx': g.ctx})

    @use_args(WFCatalogSchema(), locations=('query',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request,
                                       'service': 'eidaws-wfcatalog'}),
        locations=('query',)
    )
    @with_strict_args(
        (StreamEpochSchema, WFCatalogSchema),
        locations=('query',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self, args, stream_epochs):
        """
        Process a *WFCatalog* GET request.
        """
        # request.method == 'GET'

        # sanity check - starttime and endtime must be specified
        if (not stream_epochs or stream_epochs[0].starttime is None or
                stream_epochs[0].endtime is None):
            raise FDSNHTTPError.create(
                400, service_version=__version__,
                error_desc_long='Both starttime and endtime required.')

        self.logger.debug('StreamEpoch objects: %r' % stream_epochs)

        # serialize objects
        s = WFCatalogSchema()
        args = s.dump(args)
        self.logger.debug('WFCatalogSchema (serialized): %s' % args)

        # process request
        return RequestProcessor.create(
            args['service'],
            settings.WFCATALOG_MIMETYPE,
            query_params=args,
            stream_epochs=stream_epochs,
            post=False,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
        ).streamed_response

    # get ()

    @fdsnws.use_fdsnws_args(WFCatalogSchema(), locations=('form',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('form',)
    )
    @with_strict_args(
        WFCatalogSchema,
        locations=('form',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
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
        return RequestProcessor.create(
            args['service'],
            settings.WFCATALOG_MIMETYPE,
            query_params=args,
            stream_epochs=stream_epochs,
            post=True,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
        ).streamed_response

    # post ()

# class WFCatalogResource

# ---- END OF <wfcatalog.py> ----
