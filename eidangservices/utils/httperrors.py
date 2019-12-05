# -*- coding: utf-8 -*-
"""
FDSNWS conform HTTP error definitions.

See also: http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.1.pdf
"""

from flask import request, g

from eidangservices import settings

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


def get_error_message(code, description_short, description_long,
                      documentation_uri, request_url, request_time,
                      service_version):
    """Return text of error message."""

    return ERROR_MESSAGE_TEMPLATE % (code, description_short,
                                     description_long, documentation_uri,
                                     request_url, request_time,
                                     service_version)


# -----------------------------------------------------------------------------
class FDSNHTTPError(Exception):
    """
    General HTTP error class for 5xx and 4xx errors for FDSN web services,
    with error message according to standard. Needs to be subclassed for
    individual error types.

    """
    code = 0
    error_desc_short = ''

    DOCUMENTATION_URI = settings.FDSN_SERVICE_DOCUMENTATION_URI
    SERVICE_VERSION = ''

    @staticmethod
    def create(status_code, *args, **kwargs):
        """
        Factory method for concrete FDSN error implementations.
        """
        if status_code in settings.FDSN_NO_CONTENT_CODES:
            return NoDataError(status_code)
        elif status_code == 400:
            return BadRequestError(*args, **kwargs)
        elif status_code == 413:
            return RequestTooLargeError(*args, **kwargs)
        elif status_code == 414:
            return RequestURITooLargeError(*args, **kwargs)
        elif status_code == 500:
            return InternalServerError(*args, **kwargs)
        elif status_code == 503:
            return TemporarilyUnavailableError(*args, **kwargs)
        else:
            return InternalServerError(*args, **kwargs)

    def __init__(self, documentation_uri=None, service_version=None,
                 error_desc_long=None):
        super().__init__()

        self.documentation_uri = (documentation_uri if documentation_uri else
                                  self.DOCUMENTATION_URI)
        self.service_version = (service_version if service_version else
                                self.SERVICE_VERSION)
        self.error_desc_long = (error_desc_long if error_desc_long else
                                self.error_desc_short)

        self.description = get_error_message(
            self.code, self.error_desc_short, self.error_desc_long,
            self.documentation_uri, request.url,
            g.request_start_time.isoformat(),
            self.service_version)


class NoDataError(FDSNHTTPError):
    description = ''

    def __init__(self, status_code=204):
        self.code = status_code


class BadRequestError(FDSNHTTPError):
    code = 400
    error_desc_short = 'Bad request'


class RequestTooLargeError(FDSNHTTPError):
    code = 413
    error_desc_short = 'Request too large'


class RequestURITooLargeError(FDSNHTTPError):
    code = 414
    error_desc_short = 'Request URI too large'


class InternalServerError(FDSNHTTPError):
    code = 500
    error_desc_short = 'Internal server error'


class TemporarilyUnavailableError(FDSNHTTPError):
    code = 503
    error_desc_short = 'Service temporarily unavailable'
