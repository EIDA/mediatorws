# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import os

import flask
from flask import make_response
from flask_restful import Resource

from eidangservices import settings                                


class DQResource(Resource):
    """Service version of mediator."""
    
    def get(self):
        return get_version_response(settings.VERSION)
    
    def post(self):
        return get_version_response(settings.VERSION)


class VersionResource(Resource):
    """Service version of mediator."""
    
    def get(self):
        return get_version_response(settings.VERSION)
    
    def post(self):
        return get_version_response(settings.VERSION)


def get_version_response(version_string):
    """Return Response object for version string with correct mimetype."""
    
    response = make_response(version_string)
    response.headers['Content-Type'] = settings.VERSION_MIMETYPE
    return response
