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
from eidangservices.federator.server.schema import StationSchema
from eidangservices.federator.server.process import RequestProcessor
from eidangservices.utils import fdsnws
from eidangservices.utils.strict import with_strict_args
from eidangservices.utils.schema import (ManyStreamEpochSchema,
                                         StreamEpochSchema)


class StationResource(Resource):
    """
    Implementation of the :code:`fdsnws-station` resource.
    """

    LOGGER = 'flask.app.federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self._logger = logging.getLogger(self.LOGGER)
        self.logger = ContextLoggerAdapter(self._logger, {'ctx': g.ctx})

    @use_args(StationSchema(), locations=('query',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('query',)
    )
    @with_strict_args(
        (StreamEpochSchema, StationSchema),
        locations=('query',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self, args, stream_epochs):
        # request.method == 'GET'
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        s = StationSchema()
        args = s.dump(args)
        self.logger.debug('StationSchema (serialized): %s' % args)

        resource_cfg = 'fdsnws-station-' + args['format']

        # process request
        processor = RequestProcessor.create(
            args['service'],
            self._get_result_mimetype(args),
            query_params=args,
            stream_epochs=stream_epochs,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
            retry_budget_client=current_app.config['FED_CRETRY_BUDGET_ERATIO'],
            **current_app.config['FED_RESOURCE_CONFIG'][resource_cfg],)

        processor.post = False
        return processor.streamed_response

    @fdsnws.use_fdsnws_args(StationSchema(), locations=('form',))
    @fdsnws.use_fdsnws_kwargs(
        ManyStreamEpochSchema(context={'request': request}),
        locations=('form',)
    )
    @with_strict_args(
        StationSchema,
        locations=('form',)
    )
    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self, args, stream_epochs):
        # request.method == 'POST'
        self.logger.debug('StreamEpoch objects: %s' % stream_epochs)

        # serialize objects
        s = StationSchema()
        args = s.dump(args)
        self.logger.debug('StationSchema (serialized): %s' % args)

        resource_cfg = 'fdsnws-station-' + args['format']
        # process request
        processor = RequestProcessor.create(
            args['service'],
            self._get_result_mimetype(args),
            query_params=args,
            stream_epochs=stream_epochs,
            context=g.ctx,
            keep_tempfiles=current_app.config['FED_KEEP_TEMPFILES'],
            retry_budget_client=current_app.config['FED_CRETRY_BUDGET_ERATIO'],
            **current_app.config['FED_RESOURCE_CONFIG'][resource_cfg],)

        processor.post = True
        return processor.streamed_response

    def _get_result_mimetype(self, args):
        """Return result mimetype (either XML or plain text."""
        if args.get('format', 'xml') == 'text':
            return settings.STATION_MIMETYPE_TEXT

        return settings.STATION_MIMETYPE_XML
