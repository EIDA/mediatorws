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

def clean(session, timestamp):
    """
    Clean DB from data older than timestamp.

    :param :cls:`sqlalchemy.orm.sessionSession` session: SQLAlchemy session
    :param :cls:`obspy.UTCDateTime` Data older than timestamp will be removed.

    :returns: Total number of removed rows.
    :rtype int:
    """
    MAPPINGS_WITH_LASTSEEN = (orm.NodeNetworkInventory,
                              orm.NetworkEpoch,
                              orm.ChannelEpoch,
                              orm.StationEpoch,
                              orm.Routing,
                              orm.StreamEpoch)
    retval = 0
    for m in MAPPINGS_WITH_LASTSEEN:
        retval += session.query(m).\
            filter(m.lastseen < timestamp.datetime).\
            delete()

    # NOTE(damb): If VNet/orm.StationEpochGroup has no StreamEpochs anymore
    # remove also the orm.StreamEpochGroup.
    # Currently virtual networks do not come along with a corresponding
    # 'VirtualNetworkEpoch'.
    vnets_active = set(
        session.query(orm.StreamEpoch.stream_epoch_group_ref).all())

    if vnets_active:
        # flatten result list
        vnets_active = set(
            [item for sublist in vnets_active for item in sublist])

    vnets_active = set(
        session.query(orm.StreamEpochGroup).\
            filter(orm.StreamEpochGroup.oid.in_(vnets_active)).\
            all())


    vnets_all = set(session.query(orm.StreamEpochGroup).all())

    for vnet_not_active in (vnets_all - vnets_active):
        logger.debug('Deleting VNET {0!r}'.format(vnet_not_active))
        session.delete(vnet_not_active)
        retval += 1

    return retval

# clean ()


# ---- END OF <db.py> ----
