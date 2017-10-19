# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

from flask import make_response


def get_response(output, mimetype):
    """Return Response object for output and mimetype."""
    
    response = make_response(output)
    response.headers['Content-Type'] = mimetype
    return response
