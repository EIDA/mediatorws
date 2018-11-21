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
import logging

from eidangservices import utils, settings
from eidangservices.utils.sncl import (StreamEpochs, StreamEpochsHandler,
                                       none_as_max)

from eidangservices.stationlite.engine import orm

logger = logging.getLogger('flask.app.stationlite.dbquery')

# ----------------------------------------------------------------------------
def resolve_vnetwork(session, stream_epoch, like_escape='/'):
    """
    Resolve a stream epoch regarding virtual networks.

    :returns: List of :py:class:`eidangservices.utils.sncl.StreamEpoch` object
        instances.
    :rtype: list
    """
    if (stream_epoch.network == settings.FDSNWS_QUERY_WILDCARD_MULT_CHAR or
        (len(stream_epoch.network) <= 2 and
         set(stream_epoch.network) ==
            set([settings.FDSNWS_QUERY_WILDCARD_SINGLE_CHAR]))):
        logger.debug(
            'Not resolving VNETs (stream_epoch.network == {})'.format(
                stream_epoch.network))
        return []

    sql_stream_epoch = stream_epoch.fdsnws_to_sql_wildcards()
    logger.debug(
        '(VNET) Processing request for (SQL) {0!r}'.format(stream_epoch))

    query = session.query(orm.StreamEpoch).\
        join(orm.StreamEpochGroup).\
        join(orm.Station).\
        filter(orm.StreamEpochGroup.name.like(sql_stream_epoch.network,
                                              escape=like_escape)).\
        filter(orm.Station.name.like(sql_stream_epoch.station,
                                     escape=like_escape)).\
        filter(orm.StreamEpoch.channel.like(sql_stream_epoch.channel,
                                            escape=like_escape)).\
        filter(orm.StreamEpoch.location.like(sql_stream_epoch.location,
                                             escape=like_escape))

    if sql_stream_epoch.starttime:
        # NOTE(damb): compare to None for undefined endtime (i.e. instrument
        # currently operating)
        query = query.\
            filter((orm.StreamEpoch.endtime > sql_stream_epoch.starttime) |
                   (orm.StreamEpoch.endtime == None))  # noqa
    if sql_stream_epoch.endtime:
        query = query.\
            filter(orm.StreamEpoch.starttime < sql_stream_epoch.endtime)

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
            se.modify_with_temporal_constraints(
                start=sql_stream_epoch.starttime,
                end=sql_stream_epoch.endtime)
            sliced_ses.append(se)

    logger.debug(
        'Found {0!r} matching {0!r}'.format(sorted(sliced_ses),
                                            stream_epoch))

    return [se for ses in sliced_ses for se in ses]

# resolve_vnetwork ()

def find_streamepochs_and_routes(session, stream_epoch, service,
                                 level='channel',
                                 minlat=-90., maxlat=90., minlon=-180.,
                                 maxlon=180., like_escape='/'):
    """
    Return routes for a given stream epoch.

    :param session: SQLAlchemy session
    :type session: :py:class:`sqlalchemy.orm.sessionSession`
    :param stream_epoch: StreamEpoch the database query is performed with
    :type stream_epoch: :py:class:`eidangservices.utils.sncl.StreamEpoch`
    :param str service: String specifying the webservice
    :param str level: Optional `fdsnws-station` *level* parameter
    :param float minlat: Latitude larger than or equal to the specified minimum
    :param float maxlat: Latitude smaller than or equal to the specified
        maximum
    :param float minlon: Longitude larger than or equal to the specified
        minimum
    :param float maxlon: Longitude smaller than or equal to the specified
        maximum
    :param str like_escape: Character used for the `SQL ESCAPE` statement
    :return: List of :py:class:`eidangservices.utils.Route` objects
    :rtype: list
    """
    logger.debug('Processing request for (SQL) {0!r}'.format(stream_epoch))
    sql_stream_epoch = stream_epoch.fdsnws_to_sql_wildcards()

    sta = sql_stream_epoch.station
    loc = sql_stream_epoch.location
    cha = sql_stream_epoch.channel

    query = session.query(orm.ChannelEpoch.channel,
                          orm.ChannelEpoch.locationcode,
                          orm.ChannelEpoch.starttime,
                          orm.ChannelEpoch.endtime,
                          orm.Network.name,
                          orm.Station.name,
                          orm.Routing.starttime,
                          orm.Routing.endtime,
                          orm.Endpoint.url).\
        join(orm.Routing,
             orm.Routing.channel_epoch_ref == orm.ChannelEpoch.oid).\
        join(orm.Endpoint,
             orm.Routing.endpoint_ref == orm.Endpoint.oid).\
        join(orm.Service).\
        join(orm.Network).\
        join(orm.Station).\
        join(orm.StationEpoch).\
        filter(orm.Network.name.like(sql_stream_epoch.network,
                                     escape=like_escape)).\
        filter(orm.Station.name.like(sta, escape=like_escape)).\
        filter((orm.StationEpoch.latitude >= minlat) &
               (orm.StationEpoch.latitude <= maxlat)).\
        filter((orm.StationEpoch.longitude >= minlon) &
               (orm.StationEpoch.longitude <= maxlon)).\
        filter(orm.ChannelEpoch.channel.like(cha, escape=like_escape)).\
        filter(orm.ChannelEpoch.locationcode.like(loc, escape=like_escape)).\
        filter(orm.Service.name == service)

    if sql_stream_epoch.starttime:
        # NOTE(damb): compare to None for undefined endtime (i.e. device
        # currently operating)
        query = query.\
            filter((orm.ChannelEpoch.endtime > sql_stream_epoch.starttime) |
                   (orm.ChannelEpoch.endtime == None))  # noqa
    if sql_stream_epoch.endtime:
        query = query.\
            filter(orm.ChannelEpoch.starttime < sql_stream_epoch.endtime)

    routes = collections.defaultdict(StreamEpochsHandler)

    for row in query.all():
        #print('Query response: {0!r}'.format(row))
        # NOTE(damb): Adjust epoch in case the ChannelEpoch is smaller than the
        # RoutingEpoch (regarding time constraints).
        starttime = row[2] if row[2] > row[6] else row[6]
        endtime = row[3] if ((row[7] is None and row[3] is not None) or
                             (row[7] is not None and row[3] is not None and
                              row[7] > row[3])) else row[7]

        if endtime is not None and endtime <= starttime:
            # epoch is not routed
            continue

        # NOTE(damb): Set endtime to 'max' if undefined (i.e. device currently
        # acquiring data).
        with none_as_max(endtime) as end:
            sta = row[5]
            loc = row[1]
            cha = row[0]

            # NOTE(damb): level reduction
            if level == 'network':
                sta = loc = cha = '*'
            elif level == 'station':
                loc = cha = '*'

            stream_epochs = StreamEpochs(
                network=row[4],
                station=sta,
                location=loc,
                channel=cha,
                epochs=[(starttime, end)])

            routes[row[8]].merge([stream_epochs])

    return [utils.Route(url=url, streams=streams)
            for url, streams in routes.items()]

# find_streamepochs_and_routes ()


# ---- END OF <dbquery.py> ----
