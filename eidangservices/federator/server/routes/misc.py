# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
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
# REVISION AND CHANGES
# 2018/05/28        V0.1    Daniel Armbruster
# -----------------------------------------------------------------------------
"""
Miscellaneous federator resources.
"""

import logging
import os

import flask
from flask_restful import Resource

from eidangservices import settings, utils
from eidangservices.federator import __version__
from eidangservices.utils import fdsnws


class MiscResource(Resource):
    """
    Base class for misc resources.
    """

    LOGGER = 'flask.app.federator.misc'

    def __init__(self):
        self.logger = logging.getLogger(self.LOGGER)

# class MiscResource


class DataselectVersionResource(MiscResource):
    """Service version for dataselect."""

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self):
        return utils.get_version_response(settings.FDSN_DATASELECT_VERSION)

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self):
        return utils.get_version_response(settings.FDSN_DATASELECT_VERSION)


class StationVersionResource(MiscResource):
    """Service version for station."""

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self):
        return utils.get_version_response(settings.FDSN_STATION_VERSION)

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self):
        return utils.get_version_response(settings.FDSN_STATION_VERSION)


class WFCatalogVersionResource(MiscResource):
    """Service version for wfcatalog."""

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self):
        return utils.get_version_response(settings.EIDA_WFCATALOG_VERSION)

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self):
        return utils.get_version_response(settings.EIDA_WFCATALOG_VERSION)


class DataselectWadlResource(MiscResource):
    """application.wadl for dataselect."""

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_DATASELECT_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_DATASELECT_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)


class StationWadlResource(MiscResource):
    """application.wadl for station."""

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_STATION_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.FDSN_STATION_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)


class WFCatalogWadlResource(MiscResource):
    """application.wadl for wfcatalog."""

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def get(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.EIDA_WFCATALOG_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

    @fdsnws.with_fdsnws_exception_handling(__version__)
    def post(self):
        return flask.send_file(
            os.path.join(settings.EIDA_FEDERATOR_APP_SHARE,
                         settings.EIDA_WFCATALOG_WADL_FILENAME),
            mimetype=settings.WADL_MIMETYPE)

# ---- END OF <misc.py> ----
