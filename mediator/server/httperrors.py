# -*- coding: utf-8 -*-
"""
Custom HTTP error definitions.

This file is part of the EIDA mediator/federator webservices.

"""

from werkzeug.exceptions import HTTPException

from federator import settings

# Error <CODE>: <SIMPLE ERROR DESCRIPTION>
# <MORE DETAILED ERROR DESCRIPTION>
# Usage details are available from <SERVICE DOCUMENTATION URI>
# Request:
# <SUBMITTED URL>
# Request Submitted:
# <UTC DATE TIME>
# Service version:
# <3-LEVEL VERSION>

ERROR_MESSAGE_TEMPLATE = """
Error %s: %s

%s

Usage details are available from %s

Request:
%s

Request Submitted:
%s

Service version:
%s
"""


def get_error_message(
    code, description_short, description_long, documentation_uri, request_url,
    request_time):
    """Return text of error message."""
    
    return ERROR_MESSAGE_TEMPLATE % (code, description_short, 
        description_long, documentation_uri, request_url, request_time, 
        settings.VERSION)


class FDSNHTTPError(HTTPException):
    """
    General HTTP error class for 5xx and 4xx errors for FDSN web services,
    with error message according to standard. Needs to be subclassed for
    individual error types.
    
    """
    
    code = 0
    error_desc_short = ''
    
    def __init__(self, documentation_uri, request_url, request_time):
        super(FDSNHTTPError, self).__init__()
        
        self.description = get_error_message(
            self.code, self.error_desc_short, self.error_desc_short, 
            documentation_uri, request_url, request_time)


class NoDataError(HTTPException):
    code = 204


class BadRequestError(FDSNHTTPError):
    code = 400
    error_desc_short = 'Bad request'


class RequestTooLargeError(FDSNHTTPError):
    code = 413
    error_desc_short = 'Request too large'
    
    
class InternalServerError(FDSNHTTPError):
    code = 500
    error_desc_short = 'Internal server error'


class TemporarilyUnavailableError(FDSNHTTPError):
    code = 503
    error_desc_short = 'Service temporarily unavailable'


