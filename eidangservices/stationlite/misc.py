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
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import argparse
import contextlib
import io

import requests

from flask import make_response

from sqlalchemy import create_engine

import eidangservices as eidangws
from eidangservices import settings
from eidangservices.utils.error import Error


# -----------------------------------------------------------------------------
class RequestsError(Error):
    """Base request error ({})."""

class ClientError(RequestsError):
    """Response code not OK ({})."""

class NoContent(RequestsError):
    """The request '{}' is not returning any content ({})."""

# -----------------------------------------------------------------------------
def get_response(output, mimetype):
    """Return Response object for output and mimetype."""

    response = make_response(output)
    response.headers['Content-Type'] = mimetype
    return response

# get_response ()

def db_engine(url):
    """
    check if url is a valid url
    """
    try:
        return create_engine(url)
    except Exception:
        raise argparse.ArgumentTypeError('Invalid database URL.')

# db_engine ()

@contextlib.contextmanager
def binary_stream_request(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        if response.status_code == 204:
            # TODO TODO TODO: url
            raise NoContent(url, response.status_code)

        if response.status_code != 200:
            raise ClientError(response.status_code)

        yield io.BytesIO(response.content)

    except requests.exceptions.RequestException as err:
        raise RequestsError(err)

# binary_stream_request ()

def node_generator(exclude=[]):

    nodes = list(settings.EIDA_NODES)

    for node in nodes:
        if node not in exclude:
            yield node, settings.EIDA_NODES[node]

# node_generator ()

# -----------------------------------------------------------------------------
class RoutingContext:
    """
    Context wrapper object for StreamEpoch/StreamEpochs classes.
    """

    def __init__(self, stream_epoch):
        self._stream_epoch = stream_epoch

    def __str__(self):
        se_schema = eidangws.utils.schema.StreamEpochSchema(
            context={'routing': True})
        return ' '.join(se_schema.dump(self._stream_epoch).values())

# class RoutingContext

# ---- END OF <misc.py> ----
