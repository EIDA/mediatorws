# -*- coding: utf-8 -*-
"""
Miscellaneous stationlite resources.
"""

import os
import socket

from flask import make_response
from flask_restful import Resource

from eidangservices import settings, utils
from eidangservices.stationlite import __version__


class StationLiteVersionResource(Resource):
    """Service version for StationLite."""

    def get(self):
        return utils.get_version_response(__version__)

    def post(self):
        return utils.get_version_response(__version__)


class StationLiteWadlResource(Resource):
    """application.wadl for stationlite."""

    def __init__(self):
        super().__init__()
        self.path_wadl = os.path.join(settings.EIDA_STATIONLITE_APP_SHARE,
                                      settings.EIDA_ROUTING_WADL_FILENAME)

    @property
    def wadl(self):
        with open(self.path_wadl) as ifd:
            return ifd.read().format(
                'http://{}{}'.format(socket.getfqdn(),
                                     settings.EIDA_ROUTING_PATH))

    def get(self):
        return make_response(self.wadl, 200,
                             {'Content-Type': settings.WADL_MIMETYPE})

    def post(self):
        return make_response(self.wadl, 200,
                             {'Content-Type': settings.WADL_MIMETYPE})
