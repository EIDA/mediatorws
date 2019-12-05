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
from eidangservices.federator.server.schema import DataselectSchema
from eidangservices.federator.server.process import RequestProcessor
from eidangservices.utils import fdsnws
from eidangservices.utils.strict import with_strict_args
from eidangservices.utils.schema import (ManyStreamEpochSchema,
                                         StreamEpochSchema)


class DataselectResource(Resource):
    """
    Handler for dataselect service route.
    """
    LOGGER = 'flask.app.federator.dataselect_resource'

    def __init__(self):
        super(DataselectResource, self).__init__()
        self._logger = logging.getLogger(self.LOGGER)
        self.logger = ContextLoggerAdapter(self._logger, {'ctx': g.ctx})

    @use_args(DataselectSchema(), locations=('query',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('query',)
    )
    @with_strict_args(
        (DataselectSchema, StreamEpochSchema),
        locations=('query',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self, args, stream_epochs):
        # request.method == 'GET'
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        # serialize objects
        s = DataselectSchema()
        args = s.dump(args)
        self.logger.debug('DataselectSchema (serialized): %s' % args)

        # process request
        processor = RequestProcessor.create(
            args['service'],
            settings.DATASELECT_MIMETYPE,
            query_params=args,
            stream_epochs=stream_epochs,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
            retry_budget_client=current_app.config['FED_CRETRY_BUDGET_ERATIO'],
            **current_app.config['FED_RESOURCE_CONFIG']['fdsnws-dataselect'],)

        processor.post = False
        return processor.streamed_response

    @fdsnws.use_fdsnws_args(DataselectSchema(), locations=('form',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('form',)
    )
    @with_strict_args(
        DataselectSchema,
        locations=('form',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self, args, stream_epochs):
        # request.method == 'POST'
        # NOTE(fab): must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        s = DataselectSchema()
        args = s.dump(args)
        self.logger.debug('DataselectSchema (serialized): %s' % args)

        # process request
        processor = RequestProcessor.create(
            args['service'],
            settings.DATASELECT_MIMETYPE,
            query_params=args,
            stream_epochs=stream_epochs,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
            retry_budget_client=current_app.config['FED_CRETRY_BUDGET_ERATIO'],
            **current_app.config['FED_RESOURCE_CONFIG']['fdsnws-dataselect'],)

        processor.post = True
        return processor.streamed_response
