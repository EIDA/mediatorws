# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <db.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
#
# EIDA NG webservices are free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices are distributed in the hope that it will be useful,
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
# 2018/02/16        V0.1    Daniel Armbruster
# =============================================================================
"""
Station "light" (stationlite) DB tools.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import collections
import logging

from contextlib import contextmanager

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


from eidangservices import settings
from eidangservices.stationlite.engine import orm
from eidangservices.utils.error import Error, ErrorWithTraceback
from eidangservices.utils.sncl import (none_as_max, max_as_none,
                                       StreamEpochs, StreamEpochsHandler)


# TODO(damb): Find a more elegant solution for CACHED_SERVICES workaround.
CACHED_SERVICES = ('station', 'dataselect', 'wfcatalog')

CACHED_SERVICES_FDSN = ('station', 'dataselect')
CACHED_SERVICES_EIDA = ('wfcatalog',)
CACHED_SERVICES = {
    'fdsn': CACHED_SERVICES_FDSN,
    'eida': CACHED_SERVICES_EIDA
}


logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
class StationLiteDBEngineError(Error):
    """General purpose EIDA StationLite DB engine error ({})."""

class MissingNodeConfigParam(StationLiteDBEngineError):
    """Parameter missing in node config ({})."""


InvalidEndpointConfig = MissingNodeConfigParam

class InvalidDBUrl(StationLiteDBEngineError):
    """Invalid URL: '{}'"""

class DBEmptyQueryResultError(StationLiteDBEngineError):
    """Query '{}' returned no results."""

# -----------------------------------------------------------------------------
class ScopedSession:
    """
    An object wrapping up the SQLAlchemy session initialization process.

    The user finally obtains a scoped session as descriped at
    `Contextual/Thread-local Sessions
    <http://www.sphinx-doc.org/en/stable/rest.html#hyperlinks>`_

    Usage:
    Session = db.ScopedSession()
    Session.configure(engine)
    session = Session()
    """
    # TODO(damb): Make a ScopedSession a Singleton

    class NotConfigured(ErrorWithTraceback):
        """The session has not been configured, yet."""

    def __init__(self):
        self._session_factory = sessionmaker()
        self._session = None
        self.is_configured = False

    def configure(self, bind):
        if not self.is_configured:
            self._session_factory.configure(bind=bind)
            self._session = scoped_session(self._session_factory)
        self.is_configured = True

    def __call__(self):
        if not self.is_configured:
            raise self.NotConfigured()
        return self._session()

# class ScopedSession


# -----------------------------------------------------------------------------
@contextmanager
def session_guard(session):
    """Provide a transactional scope around a series of operations."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_cached_services():
    retval = []
    for k, v in CACHED_SERVICES.items():
        retval.extend(v)
    return retval


def init(session):
    """initialize database tables"""

    def _lookup_service(services, name, std):
        return next(
            (x for x in services if x.name == name and x.standard == std),
            None)

    # _lookup_service ()

    # populate db tables from the mediatorws configuration (i.e. currently
    # settings.py)
    logger.debug('Collecting mappings ...')
    _services = []
    for service_std, services in CACHED_SERVICES.items():
        for s_name in services:
            _services.append(orm.Service(name=s_name,
                                         standard=service_std))

    _nodes = []
    _endpoints = []

    logger.debug('Services available: %s' % _services)

    for node_name, node_par in settings.EIDA_NODES.items():

        try:
            n = orm.Node(name=node_name,
                         description=node_par['name'])

            # add services to node
            # NOTE(damb): Only such services are added which are both
            # cached and have configured parameters in settings.py

            # fdsn services
            for s, v in node_par['services']['fdsn'].items():
                _service = _lookup_service(_services, s, 'fdsn')
                if v and _service:
                    logger.debug("Adding service '%r' to '%r'" % (_service, n))
                    n.services.append(_service)

            # eida services
            for s, v in node_par['services']['eida'].items():
                _service = _lookup_service(_services, s, 'eida')
                if v and _service:
                    logger.debug("Adding service '%r' to '%r'" % (_service, n))
                    n.services.append(_service)

        except KeyError as err:
            raise MissingNodeConfigParam(err)

        _nodes.append(n)

        # create endpoints and add service
        try:
            # fdsn services
            for s, v in node_par['services']['fdsn'].items():
                if v and _lookup_service(_services, s, 'fdsn'):
                    e = orm.Endpoint(
                        url='{}/fdsnws/{}/1/query'.format(
                            node_par['services']['fdsn']['server'], s),
                        service=_lookup_service(_services, s, 'fdsn'))

                    logger.debug('Created endpoint %r' % e)
                    _endpoints.append(e)

            # eida services
            for s, v in node_par['services']['eida'].items():
                if (v['server'] and
                        _lookup_service(_services, s, 'eida')):
                    e = orm.Endpoint(
                        url='{}{}'.format(v['server'],
                                          v['uri_path_query']),
                        service=_lookup_service(_services, s, 'eida'))

                    logger.debug('Created endpoint %r' % e)
                    _endpoints.append(e)

        except KeyError as err:
            raise InvalidEndpointConfig(err)

    payload = _nodes
    payload.extend(_endpoints)

    with session_guard(session) as s:
        s.add_all(payload)

# init ()

def delete_vnetworks(session):
    """
    Remove all virtual networks from the stationlite DB.

    :param :cls:`sqlalchemy.orm.session.Session` session: SQLAlchemy session
    instance.
    """
    # fetch all networks with 'is_virtual=True'
    vnets = session.query(orm.Network).\
        filter(orm.Network.is_virtual.is_(True)).\
        all()
    for vnet in vnets:
        # delete NodeNetworkInventory from vnets
        session.query(orm.NodeNetworkInventory).\
            filter(orm.NodeNetworkInventory.network == vnet).\
            delete()

        for vnet_relation in session.query(orm.ChannelEpochNetworkRelation).\
            filter(orm.ChannelEpochNetworkRelation.network == vnet).\
                all():

            delete_channel_epoch_network_relation(session, vnet_relation)

    session.commit()

# delete_vnetworks ()

def merge(session):
    """
    Merge StreamEpochs regarding time constraints. When merging the
    epoch's routing information is taken into consideration.

    :param :cls:`sqlalchemy.orm.sessionSession` session: SQLAlchemy session
    """
    class _Routing(collections.namedtuple('_Routing',
                                          ['url', 'starttime', 'endtime'])):
        """
        A hashable py:class:`orm.Routing` adapter.
        """

        @classmethod
        def from_orm(cls, routing):
            return cls(url=routing.endpoint.url,
                       starttime=routing.starttime,
                       endtime=routing.endtime)

        def _emerge_orm(self, session, cha_epoch):
            try:
                endpoint = session.query(orm.Endpoint).\
                    filter(orm.Endpoint.url == self.url).\
                    one()
            except (NoResultFound, MultipleResultsFound) as err:
                raise StationLiteDBEngineError(err)

            routing = session.query(orm.Routing).\
                filter(orm.Routing.endpoint == endpoint).\
                filter(orm.Routing.channel_epoch == cha_epoch).\
                filter(orm.Routing.starttime == self.starttime).\
                filter(orm.Routing.endtime == self.endtime).\
                scalar()

            if not routing:
                routing = orm.Routing(
                    endpoint=endpoint,
                    channel_epoch=cha_epoch,
                    starttime=self.starttime,
                    endtime=self.endtime)

            session.add(routing)
            return routing

    # class _Routing

    merged_routes = collections.defaultdict(StreamEpochsHandler)
    # consider all orm.ChannelEpochs for a orm.Network
    nets = session.query(orm.Network).all()
    for net in nets:
        for cha_epoch, routing in session.query(
            orm.ChannelEpoch, orm.Routing).\
            join(orm.ChannelEpochNetworkRelation).\
            join(orm.Network).\
            join(orm.Routing).\
            filter((orm.ChannelEpochNetworkRelation.channel_epoch_ref ==
                    orm.ChannelEpoch.oid) &
                   (orm.ChannelEpochNetworkRelation.network_ref ==
                    orm.Network.oid)).\
            filter(orm.Network.name == net.name).\
            filter(orm.Routing.channel_epoch_ref ==
                   orm.ChannelEpoch.oid).\
                all():

            with none_as_max(cha_epoch.endtime) as end:
                stream_epochs = StreamEpochs(
                    network=net.name,
                    station=cha_epoch.station.name,
                    channel=cha_epoch.channel,
                    location=cha_epoch.locationcode,
                    epochs=[(cha_epoch.starttime,
                             end)])
                # use a hashable _Routing instance as key
                merged_routes[_Routing.from_orm(routing)].merge(
                    [stream_epochs])

    # TODO(damb): Use generators instead
    # add previously merged ChannelEpochs to DB
    for routing, stream_epochs_handlers in merged_routes.items():
        lst_stream_epoch = [se for ses in sorted(stream_epochs_handlers)
                            for se in ses]

        for stream_epoch in lst_stream_epoch:
            logger.debug(
                'Processing StreamEpoch object {0!r}'.format(stream_epoch))
            with max_as_none(stream_epoch.endtime) as end:
                # checks if a orm.ChannelEpoch is already available
                cha_epoch = session.query(orm.ChannelEpoch).\
                    join(orm.ChannelEpochNetworkRelation).\
                    join(orm.Network).\
                    join(orm.Station).\
                    filter(
                        (orm.ChannelEpochNetworkRelation.channel_epoch_ref ==
                         orm.ChannelEpoch.oid) &
                        (orm.ChannelEpochNetworkRelation.network_ref ==
                         orm.Network.oid)).\
                    filter(orm.Network.name ==
                           stream_epoch.network).\
                    filter(orm.Station.name ==
                           stream_epoch.station).\
                    filter(orm.ChannelEpoch.channel ==
                           stream_epoch.channel).\
                    filter(orm.ChannelEpoch.locationcode ==
                           stream_epoch.location).\
                    filter(orm.ChannelEpoch.starttime ==
                           stream_epoch.starttime).\
                    filter(orm.ChannelEpoch.endtime == end).\
                    scalar()

                if cha_epoch is None:
                    # create a new orm.ChannelEpoch including all relations

                    try:
                        net = session.query(orm.Network).\
                            filter(orm.Network.name ==
                                   stream_epoch.network).\
                            one()
                        sta = session.query(orm.Station).\
                            filter(orm.Station.name ==
                                   stream_epoch.station).\
                            one()
                        endpoint = session.query(orm.Endpoint).\
                            filter(orm.Endpoint.url == routing.url).\
                            one()
                    except (NoResultFound, MultipleResultsFound) as err:
                        raise StationLiteDBEngineError(err)

                    cha_epoch = orm.ChannelEpoch(
                        channel=stream_epoch.channel,
                        locationcode=stream_epoch.location,
                        starttime=stream_epoch.starttime,
                        endtime=end,
                        station=sta)

                    session.add(cha_epoch)

                    # create relations
                    _ = orm.ChannelEpochNetworkRelation(
                        channel_epoch=cha_epoch,
                        network=net)
                    _ = orm.Routing(
                        channel_epoch=cha_epoch,
                        endpoint=endpoint,
                        starttime=routing.starttime,
                        endtime=routing.endtime)
                    logger.debug(
                        "Created new channel_epoch object '{}'".format(
                            cha_epoch))

                    # delete the two orm.ChannelEpochs from the DB
                    # responsible for the epoch borders of the newly
                    # created merged orm.ChannelEpoch
                    to_delete = session.query(orm.ChannelEpoch).\
                        join(orm.ChannelEpochNetworkRelation).\
                        join(orm.Network).\
                        join(orm.Station).\
                        join(orm.Routing).\
                        filter(
                            (orm.ChannelEpochNetworkRelation.\
                             channel_epoch_ref == orm.ChannelEpoch.oid) &
                            (orm.ChannelEpochNetworkRelation.network_ref ==
                             orm.Network.oid)).\
                        filter((orm.Routing.endpoint == endpoint) &
                               (orm.Routing.channel_epoch_ref ==
                                orm.ChannelEpoch.oid) &
                               (orm.Routing.starttime ==
                                routing.starttime) &
                               (orm.Routing.endtime ==
                                routing.endtime)).\
                        filter(orm.Network.name ==
                               stream_epoch.network).\
                        filter(orm.Station.name ==
                               stream_epoch.station).\
                        filter(orm.ChannelEpoch.channel ==
                               stream_epoch.channel).\
                        filter(orm.ChannelEpoch.locationcode ==
                               stream_epoch.location).\
                        filter((orm.ChannelEpoch.starttime ==
                                stream_epoch.starttime) |
                               (orm.ChannelEpoch.endtime == end)).\
                        all()

                    # FIXME(damb): The orm.ChannelEpoch might have
                    # additional relations to orm.Network objects via
                    # orm.ChannelEpochNetworkRelation.

                    print(to_delete)

                    if len(to_delete) < 2:
                        raise StationLiteDBEngineError(
                            'Expected at least two orm.ChannelEpoch '
                            'objects but found {}'.format(to_delete))

                    for e in to_delete:
                        logger.debug(
                            'Trying to delete orm.ChannelEpoch object '
                            '{}'.format(e))
                        trydelete_channel_epoch(session, e, net,
                                                endpoint,
                                                routing.starttime,
                                                routing.endtime)

    # delete all orm.ChannelEpoch objects from the DB which are
    # real subsets of another orm.ChannelEpoch
    # TODO TODO TODO
    """
    for net in nets:
        for cha_epoch in session.query(orm.ChannelEpoch).\
            join(orm.ChannelEpochNetworkRelation).\
            join(orm.Network).\
            filter(orm.ChannelEpochNetworkRelation.channel_epoch_ref ==
                   orm.ChannelEpoch.oid).\
            filter(orm.Network.name == net.name).\
                all():

            to_delete = session.query(orm.ChannelEpoch).\
                join(orm.ChannelEpochNetworkRelation).\
                join(orm.Network).\
                join(orm.Station).\
                filter((orm.ChannelEpochNetworkRelation.channel_epoch_ref ==
                        orm.ChannelEpoch.oid) &
                       (orm.ChannelEpochNetworkRelation.network_ref ==
                        orm.Network.oid)).\
                filter(orm.Network.name == net.name).\
                filter(orm.Station.name ==
                       cha_epoch.station.name).\
                filter(orm.ChannelEpoch.channel ==
                       cha_epoch.channel).\
                filter(orm.ChannelEpoch.locationcode ==
                       cha_epoch.locationcode).\
                filter((orm.ChannelEpoch.starttime >
                        stream_epoch.starttime) &
                       (orm.ChannelEpoch.endtime < end)).\
                all()

            for e in to_delete:
                db.trydelete_channel_epoch(session, e, net)
    """

# merge ()
