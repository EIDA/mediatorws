# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <dataselect.py>
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
# REVISION AND CHANGES
# 2018/05/18        V0.1    Daniel Armbruster, Fabian Euchner
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
from eidangservices.federator import __version__
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
        self.logger = logging.getLogger(self.LOGGER)

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
        return RequestProcessor.create(args['service'],
                                       settings.DATASELECT_MIMETYPE,
                                       query_params=args,
                                       stream_epochs=stream_epochs,
                                       post=False).streamed_response
    # get ()

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
        return RequestProcessor.create(args['service'],
                                       settings.DATASELECT_MIMETYPE,
                                       query_params=args,
                                       stream_epochs=stream_epochs,
                                       post=True).streamed_response

    # post ()

# class DataselectResource


# ---- END OF <dataselect.py> ----
