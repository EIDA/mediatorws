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
import datetime 
import logging

from flask import request
from webargs.flaskparser import use_args

import eidangservices as eidangws

from eidangservices import httperrors, settings, utils
from eidangservices.federator.server import general_request, schema


class WFCatalogResource(general_request.GeneralResource):
    """
    Implementation of a `WFCatalog
    <https://www.orfeus-eu.org/data/eida/webservices/wfcatalog/>`_ resource.
    """

    LOGGER = 'flask.app.federator.wfcatalog_resource'

    def __init__(self):
        super(WFCatalogResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.WFCatalogSchema(), locations=('query',))
    @utils.use_fdsnws_kwargs(
        eidangws.schema.ManyStreamEpochSchema(context={'request': request}),
        locations=('query',)
    )
    def get(self, wfcatalog_args, stream_epochs):
        """
        Process a *WFCatalog* GET request.
        """
        # request.method == 'GET'

        # sanity check - starttime and endtime must be specified
        if not stream_epochs or stream_epochs[0].starttime is None or stream_epochs[0].endtime is None:
            raise httperrors.BadRequestError(
                    settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                    datetime.datetime.utcnow()
            )

        self.logger.debug('StreamEpoch objects: %r' % stream_epochs)

        # serialize objects
        s = schema.WFCatalogSchema()
        wfcatalog_args = s.dump(wfcatalog_args).data
        self.logger.debug('WFCatalogSchema (serialized): %s' %
                          wfcatalog_args)

        # process request
        return self._process_request(wfcatalog_args, stream_epochs,
                                     settings.WFCATALOG_MIMETYPE,
                                     path_tempfile=self.path_tempfile)

    # get ()

    @utils.use_fdsnws_args(schema.WFCatalogSchema(), locations=('form',))
    @utils.use_fdsnws_kwargs(
        eidangws.schema.ManyStreamEpochSchema(context={'request': request}),
        locations=('form',)
    )
    def post(self, wfcatalog_args, stream_epochs):
        """
        Process a *WFCatalog* POST request.
        """
        # request.method == 'POST'
        # NOTE: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"

        self.logger.debug('StreamEpoch objects: %r' % stream_epochs)

        # serialize objects
        s = schema.WFCatalogSchema()
        wfcatalog_args = s.dump(wfcatalog_args).data
        self.logger.debug('WFCatalogSchema (serialized): %s' % wfcatalog_args)

        return self._process_request(wfcatalog_args, stream_epochs,
                                     settings.WFCATALOG_MIMETYPE,
                                     path_tempfile=self.path_tempfile,
                                     post=True)

    # post ()

# class WFCatalogResource

# ---- END OF <wfcatalog.py> ----
