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
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import datetime

from flask import Flask, make_response, g
from flask_cors import CORS

# from werkzeug.contrib.profiler import ProfilerMiddleware

from eidangservices import settings
from eidangservices.federator import __version__
from eidangservices.utils import httperrors
from eidangservices.utils.fdsnws import (register_parser_errorhandler,
                                         register_keywordparser_errorhandler)

def create_app(config_dict={}, service_version=__version__):
    """
    Factory function for Flask application.

    :param config_dict: flask configuration object
    :type config_dict: :py:class:`flask.Config`
    :param str service_version: Version string
    """
    app = Flask(__name__)
    app.config.update(config_dict)
    # allows CORS for all domains for all routes
    CORS(app)

    # app.config['PROFILE'] = True
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])

    # TODO(damb): move webservice error handling to eidangservices.utils
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

    return app

# create_app ()

# ---- END OF <__init__.py> ----
