# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

from flask import make_response
from flask_restful import Resource

from federator import settings                                

     
class DataselectVersionResource(Resource):
    """Service version for dataselect."""
    
    def get(self):
        return get_version_response(settings.FDSN_DATASELECT_VERSION)

    def post(self): 
        return get_version_response(settings.FDSN_DATASELECT_VERSION)


class StationVersionResource(Resource):
    """Service version for station."""
    
    def get(self):
        return get_version_response(settings.FDSN_STATION_VERSION)
    
    def post(self):
        return get_version_response(settings.FDSN_STATION_VERSION)


def get_version_response(version_string):
    """Return Response object for version string with correct mimetype."""
    
    response = make_response(version_string)
    response.headers['Content-Type'] = 'text/plain'
    return response
