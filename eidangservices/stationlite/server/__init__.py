# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <__init__.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices is distributed in the hope that it will be useful,
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
#
# REVISION AND CHANGES
# 2018/03/14        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA NG StationLite webservice implementation.
"""

import datetime

from flask import Flask, make_response, g
from flask_sqlalchemy import SQLAlchemy

from eidangservices import settings
from eidangservices.utils import httperrors
from eidangservices.utils.fdsnws import (register_parser_errorhandler,
                                         register_keywordparser_errorhandler)
from eidangservices.stationlite import __version__


db = SQLAlchemy()


def create_app(config_dict, service_version=__version__):
    """
    Factory function for Flask application.

    :param config_dict: flask configuration object
    :type config_dict: :py:class:`flask.Config`
    :param str service_version: Version string
    """
    app = Flask(__name__)
    app.config.update(config_dict)

    @app.before_request
    def before_request():
        g.request_start_time = datetime.datetime.utcnow()

    def register_error(err):
        @app.errorhandler(err)
        def handle_error(error):
            return make_response(
                error.description, error.code,
                {'Content-Type': '{}; {}'.format(settings.ERROR_MIMETYPE,
                                                 settings.CHARSET_TEXT)})

    # register_error ()

    errors_to_register = (
        httperrors.NoDataError,
        httperrors.BadRequestError,
        httperrors.RequestTooLargeError,
        httperrors.RequestURITooLargeError,
        httperrors.InternalServerError,
        httperrors.TemporarilyUnavailableError)

    for err in errors_to_register:
        register_error(err)

    register_parser_errorhandler(service_version=service_version)
    register_keywordparser_errorhandler(service_version=service_version)

    db.init_app(app)

    return app

# create_app ()

# ---- END OF <__init__.py> ----
