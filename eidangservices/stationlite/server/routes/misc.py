# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EDIA NG webservices is distributed in the hope that it will be useful,
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
# 2018/03/20        V0.1    Daniel Armbruster
# =============================================================================
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

# class StationLiteVersionResource


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

# class StationLiteWadlResource


# ---- END OF <misc.py> ----
