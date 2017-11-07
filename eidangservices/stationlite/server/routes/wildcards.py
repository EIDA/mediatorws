# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

from flask_restful import Resource

from eidangservices import settings

from eidangservices.stationlite.utils import misc

       
class WildcardsResource(Resource):
    """Service query for wildcardresolver."""
    
    def get(self):
        return misc.get_response('get', settings.GENERAL_TEXT_MIMETYPE)

    def post(self): 
        return misc.get_response('post', settings.GENERAL_TEXT_MIMETYPE)
    
