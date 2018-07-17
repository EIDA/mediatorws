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
StationLite (stationlite) DB tools.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import logging

from contextlib import contextmanager

from sqlalchemy.orm import scoped_session, sessionmaker

from eidangservices.stationlite.engine import orm
from eidangservices.utils.error import Error, ErrorWithTraceback


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

# session_guard ()


def clean(session, timestamp):
    """
    Clean DB from data older than timestamp.

    :param :py:class:`sqlalchemy.orm.sessionSession` session: SQLAlchemy
        session
    :param :py:class:`obspy.UTCDateTime` Data older than timestamp will
        be removed.

    :returns: Total number of removed rows.
    :rtype int:
    """
    MAPPINGS_WITH_LASTSEEN = (orm.NetworkEpoch,
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
