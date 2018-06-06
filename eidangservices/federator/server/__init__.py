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

from eidangservices import settings
from eidangservices.utils import httperrors
from eidangservices.utils.fdsnws import register_parser_errorhandler

def create_app(config_dict={},
               service_id=settings.EIDA_FEDERATOR_SERVICE_ID):
    """
    Factory function for Flask application.

    :param :cls:`flask.Config config` flask configuration object
    """
    app = Flask(__name__)
    app.config.update(config_dict)

    # TODO(damb): move webservice error handling to eidangservices.utils
    @app.before_request
    def before_request():
        g.request_start_time = datetime.datetime.utcnow()

    def register_error(err):
        @app.errorhandler(err)
        def handle_error(error):
            return make_response(error.description, error.code)

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

    register_parser_errorhandler(service_id=service_id)

    return app

# create_app ()

# ---- END OF <__init__.py> ----
