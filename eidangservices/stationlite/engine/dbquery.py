#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <dbquery.py>
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
# Copyright (c) Fabian Euchner (ETH), Daniel Armbruster (ETH)
#
# REVISION AND CHANGES
# 2018/01/08        V0.1    Daniel Armbruster
# =============================================================================
"""
DB query tools for stationlite web service.

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import collections
import datetime
import logging

from sqlalchemy import select

from eidangservices import utils
from eidangservices.utils.sncl import StreamEpochs, StreamEpochsHandler

logger = logging.getLogger('flask.app.stationlite.dbquery')

# ----------------------------------------------------------------------------
def find_streamepochs_and_routes(connection, tables, stream_epoch, service,
                                 like_escape='/'):
    """
    Return routes for a given stream epoch.

    :param :py:class:`sncl.StreamEpoch`: StreamEpoch the database query is
    performed with
    :param str service: String specifying the webservice
    :param str like_escape: Character used for the SQL ESCAPE statement

    :returns: List of :py:class:`utils.Route` objects
    :rtype list:
    """
    tn = tables['network']
    ts = tables['station']
    tc = tables['channel']
    tr = tables['routing']
    te = tables['endpoint']
    tsv = tables['service']

    conj = (tn.c.name.like(stream_epoch.network, escape=like_escape) &
            ts.c.name.like(stream_epoch.station, escape=like_escape) &
            tc.c.locationcode.like(stream_epoch.location, escape=like_escape) &
            tc.c.code.like(stream_epoch.channel, escape=like_escape) &
            (tc.c.network_ref == tn.c.oid) &
            (tc.c.station_ref == ts.c.oid) &
            (tr.c.channel_ref == tc.c.oid) &
            (tr.c.endpoint_ref == te.c.oid) &
            (te.c.service_ref == tsv.c.oid) &
            (service == tsv.c.name))

    if stream_epoch.starttime:
        # NOTE(damb): compare to None for undefined endtime (i.e. device
        # currently operating)
        conj &= ((stream_epoch.starttime < tr.c.endtime) |
                 (tr.c.endtime is None))
    if stream_epoch.endtime:
        conj &= (stream_epoch.endtime > tr.c.starttime)

    s = select([
        tn.c.name, ts.c.name, tc.c.locationcode, tc.c.code,
        tr.c.starttime, tr.c.endtime, te.c.url]).where(conj)

    rp = connection.execute(s).fetchall()

    now = datetime.datetime.utcnow()
    routes = collections.defaultdict(StreamEpochsHandler)

    for row in rp:
        #print('Query response: %r' % row)
        # NOTE(damb): Set endtime to 'now' if undefined (i.e. device currently
        # acquiring data).
        endtime = row[tr.c.endtime]
        if endtime is None:
            endtime = now

        stream_epochs = StreamEpochs(network=row[tn.c.name],
                                     station=row[ts.c.name],
                                     location=row[tc.c.locationcode],
                                     channel=row[tc.c.code],
                                     epochs=[(row[tr.c.starttime], endtime)])

        routes[row[te.c.url]].merge([stream_epochs])

    return [utils.Route(url=url, streams=streams)
            for url, streams in routes.items()]

# find_streamepochs_and_routes ()


def find_networks(connection, tables):

    tn = tables['network']

    s = select([tn.c.name])

    rp = connection.execute(s)
    r = rp.fetchall()

    return [x[0] for x in r]

# ---- END OF <dbquery.py> ----
