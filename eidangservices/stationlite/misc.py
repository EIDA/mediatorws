# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
#
# eida-stationlite is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# eida-stationlite is distributed in the hope that it will be useful,
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
# 2017/12/21        V0.1    Daniel Armbruster; Based on fab's code.
# =============================================================================
"""
This file is part of the EIDA mediator/federator webservices.

"""

import argparse
from flask import make_response

from sqlalchemy import create_engine

from eidangservices import settings


def get_response(output, mimetype):
    """Return Response object for output and mimetype."""

    response = make_response(output)
    response.headers['Content-Type'] = mimetype
    return response

# get_response ()

def db_engine(url):
    """
    Check if `url` is a valid URL by means of creating a `SQLAlchemy
    <https://www.sqlalchemy.org/>`_.
    """
    try:
        return create_engine(url)
    except Exception as err:
        raise argparse.ArgumentTypeError(
            'Error while creating engine ({}).'.format(err))

# db_engine ()

def node_generator(exclude=[]):

    nodes = list(settings.EIDA_NODES)

    for node in nodes:
        if node not in exclude:
            yield node, settings.EIDA_NODES[node]

# node_generator ()

# ---- END OF <misc.py> ----
