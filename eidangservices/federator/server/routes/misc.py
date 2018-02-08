# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
# This file is part of EIDA NG webservices (eida-federator).
#
# eida-federator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# eida-federator is distributed in the hope that it will be useful,
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
# -----------------------------------------------------------------------------
"""
This file is part of the EIDA mediator/federator webservices.

"""

import os

import flask
from flask import make_response
from flask_restful import Resource

from eidangservices import settings


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


class WFCatalogVersionResource(Resource):
    """Service version for wfcatalog."""

    def get(self):
        return get_version_response(settings.FDSN_WFCATALOG_VERSION)

    def post(self):
        return get_version_response(settings.FDSN_WFCATALOG_VERSION)


class DataselectWadlResource(Resource):
    """application.wadl for dataselect."""

    def get(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_DATASELECT_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

    def post(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_DATASELECT_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)


class StationWadlResource(Resource):
    """application.wadl for station."""

    def get(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_STATION_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

    def post(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_STATION_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)


class WFCatalogWadlResource(Resource):
    """application.wadl for wfcatalog."""

    def get(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_WFCATALOG_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

    def post(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_WFCATALOG_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

# -----------------------------------------------------------------------------
def get_version_response(version_string):
    """Return Response object for version string with correct mimetype."""

    response = make_response(version_string)
    response.headers['Content-Type'] = settings.VERSION_MIMETYPE
    return response
