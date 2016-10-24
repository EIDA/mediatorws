# -*- coding: utf-8 -*-
"""
Custom HTTP error definitions.

This file is part of the EIDA mediator/federator webservices.

"""

from werkzeug.exceptions import HTTPException


class NoDataError(HTTPException):
    code = 204
    description = 'No data.'


class BadRequestError(HTTPException):
    code = 400
    description = 'Bad request.'


class InternalServerError(HTTPException):
    code = 500
    description = 'Internal server error.'
