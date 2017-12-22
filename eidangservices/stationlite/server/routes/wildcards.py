# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import logging

from flask import request
from flask_restful import Resource
from webargs.flaskparser import use_args

import eidangservices as eidangws
from eidangservices import settings, utils

from eidangservices.stationlite.server import schema
from eidangservices.stationlite.utils import misc

       
class WildcardsResource(Resource):
    """Service query for wildcardresolver."""
    
    LOGGER = 'flask.app.stationlite.wildcards_resource'

    def __init__(self):
        super(WildcardsResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    # __init__ ()

    @use_args(schema.StationLiteSchema(), locations=('query',))
    @utils.use_fdsnws_kwargs(
        eidangws.schema.ManySNCLSchema(context={'request': request}),
        locations=('query',)
    )
    def get(self):
        """
        Process a *Wildcard* GET request.
        """
        return misc.get_response('get', settings.MIMETYPE_TEXT)

    # get ()

    @utils.use_fdsnws_args(schema.StationLiteSchema(), locations=('form',))
    @utils.use_fdsnws_kwargs(
        eidangws.schema.ManySNCLSchema(context={'request': request}),
        locations=('form',)
    )
    def post(self): 
        """
        Process a *Wildcard* POST request.
        """
        return misc.get_response('post', settings.MIMETYPE_TEXT)

    # post ()
    
