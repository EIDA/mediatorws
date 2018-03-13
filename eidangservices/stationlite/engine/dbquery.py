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
import contextlib
import datetime
import logging

from eidangservices import utils
from eidangservices.utils.sncl import (StreamEpochs, StreamEpochsHandler,
                                       none_as_max)

from eidangservices.stationlite.engine import orm

logger = logging.getLogger('flask.app.stationlite.dbquery')

# ----------------------------------------------------------------------------
@contextlib.contextmanager
def vnetwork(session, stream_epoch, like_escape='/'):
    yield resolve_vnetwork(session, stream_epoch, like_escape)

def resolve_vnetwork(session, stream_epoch, like_escape='/'):
    """
    Resolve a stream epoch regarding virtual networks.

    :returns: List of :cls:`eidangservices.utils.sncl.StreamEpoch` object
    instances.
    :rtype: list
    """
    _stream_epoch = stream_epoch.fdsnws_to_sql_wildcards()
    logger.debug(
        '(VNET) Processing request for (SQL) {0!r}'.format(stream_epoch))

    query = session.query(orm.StreamEpoch).\
        join(orm.StreamEpochGroup).\
        join(orm.Station).\
        filter(orm.StreamEpochGroup.name.like(_stream_epoch.network,
                                              escape=like_escape)).\
        filter(orm.Station.name.like(_stream_epoch.station,
                                     escape=like_escape)).\
        filter(orm.StreamEpoch.channel.like(_stream_epoch.channel,
                                            escape=like_escape)).\
        filter(orm.StreamEpoch.location.like(_stream_epoch.location,
                                             escape=like_escape))

    if _stream_epoch.starttime:
        # NOTE(damb): compare to None for undefined endtime (i.e. instrument
        # currently operating)
        query = query.\
            filter((orm.StreamEpoch.endtime > _stream_epoch.starttime) |
                   (orm.StreamEpoch.endtime == None))  # noqa
    if _stream_epoch.endtime:
        query = query.\
            filter(orm.StreamEpoch.starttime < _stream_epoch.endtime)

    # slice the stream epoch
    sliced_ses = []
    for s in query.all():
        #print('Query response: {0!r}'.format(StreamEpoch.from_orm(s)))
        with none_as_max(s.endtime) as end:
            se = StreamEpochs(
                network=s.network.name,
                station=s.station.name,
                location=s.location,
                channel=s.channel,
                epochs=[(s.starttime, end)])
            se.modify_with_temporal_constraints(start=_stream_epoch.starttime,
                                                end=_stream_epoch.endtime)
            sliced_ses.append(se)

    logger.debug(
        'Found {0!r} matching {0!r}'.format(sorted(sliced_ses),
                                            stream_epoch))

    return [se for ses in sliced_ses for se in ses]

# resolve_vnetwork ()

def find_streamepochs_and_routes(session, stream_epoch, service,
                                 like_escape='/'):
    """
    Return routes for a given stream epoch.

    :param :cls:``
    :param :py:class:`sncl.StreamEpoch`: StreamEpoch the database query is
    performed with
    :param str service: String specifying the webservice
    :param str like_escape: Character used for the SQL ESCAPE statement

    :returns: List of :py:class:`utils.Route` objects
    :rtype list:
    """
    logger.debug('Processing request for (SQL) {0!r}'.format(stream_epoch))
    _stream_epoch = stream_epoch.fdsnws_to_sql_wildcards()

    query = session.query(orm.ChannelEpoch.channel,
                          orm.ChannelEpoch.locationcode,
                          orm.Network.name,
                          orm.Station.name,
                          orm.Routing.starttime,
                          orm.Routing.endtime,
                          orm.Endpoint.url).\
        join(orm.Routing).\
        join(orm.Endpoint).\
        join(orm.Service).\
        filter((orm.Routing.channel_epoch_ref == orm.ChannelEpoch.oid) &
               (orm.Routing.endpoint_ref == orm.Endpoint.oid)).\
        filter(orm.Network.name.like(_stream_epoch.network,
                                     escape=like_escape)).\
        filter(orm.Station.name.like(_stream_epoch.station,
                                     escape=like_escape)).\
        filter(orm.ChannelEpoch.channel.like(_stream_epoch.channel,
                                             escape=like_escape)).\
        filter(orm.ChannelEpoch.locationcode.like(_stream_epoch.location,
                                                  escape=like_escape)).\
        filter(orm.Service.name == service)

    if _stream_epoch.starttime:
        # NOTE(damb): compare to None for undefined endtime (i.e. device
        # currently operating)
        query = query.\
            filter((orm.ChannelEpoch.endtime > _stream_epoch.starttime) |
                   (orm.ChannelEpoch.endtime == None))  # noqa
    if _stream_epoch.endtime:
        query = query.\
            filter(orm.ChannelEpoch.starttime < _stream_epoch.endtime)

    now = datetime.datetime.utcnow()
    routes = collections.defaultdict(StreamEpochsHandler)

    for row in query.all():
        print('Query response: {0!r}'.format(row))
        # NOTE(damb): Set endtime to 'now' if undefined (i.e. device currently
        # acquiring data).
        with none_as_max(row[5]) as end:
            stream_epochs = StreamEpochs(
                network=row[2],
                station=row[3],
                location=row[1],
                channel=row[0],
                epochs=[(row[4], end)])

            routes[row[6]].merge([stream_epochs])

    return [utils.Route(url=url, streams=streams)
            for url, streams in routes.items()]

# find_streamepochs_and_routes ()


# ---- END OF <dbquery.py> ----
