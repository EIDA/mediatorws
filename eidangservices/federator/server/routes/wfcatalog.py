# -*- coding: utf-8 -*-
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
        processor = RequestProcessor.create(
            args['service'],
            settings.WFCATALOG_MIMETYPE,
            query_params=args,
            stream_epochs=stream_epochs,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
            retry_budget_client=current_app.config['FED_CRETRY_BUDGET_ERATIO'],
            **current_app.config['FED_RESOURCE_CONFIG']['eidaws-wfcatalog'],)

        processor.post = False
        return processor.streamed_response

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
        processor = RequestProcessor.create(
            args['service'],
            settings.WFCATALOG_MIMETYPE,
            query_params=args,
            stream_epochs=stream_epochs,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
            retry_budget_client=current_app.config['FED_CRETRY_BUDGET_ERATIO'],
            **current_app.config['FED_RESOURCE_CONFIG']['eidaws-wfcatalog'],)

        processor.post = True
        return processor.streamed_response
