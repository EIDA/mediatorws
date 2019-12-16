# -*- coding: utf-8 -*-
"""
StationLite (stationlite) DB tools.
"""

import logging

from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.orm import scoped_session, sessionmaker

from eidangservices.stationlite.engine import orm
from eidangservices.utils.error import Error, ErrorWithTraceback


logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
class DBError(ErrorWithTraceback):
    """Base DB error ({})."""


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

    .. code::

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


def configure_sqlite(pragmas):
    """
    Wraps up SQLite DB specific configuration.

    :param list pragmas: List of pragmas (:py:class:`str` objects) to be
        executed.
    :raises: :py:class:`DBError`
    """
    @listens_for(Engine, 'connect', named=True)
    def configure_pragmas(dbapi_connection, **kwargs):
        try:
            for pragma in pragmas:
                dbapi_connection.execute(pragma)
        except Exception as err:
            raise DBError(err)


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
        session.query(orm.StreamEpochGroup).
        filter(orm.StreamEpochGroup.id.in_(vnets_active)).
        all())

    vnets_all = set(session.query(orm.StreamEpochGroup).all())

    for vnet_not_active in (vnets_all - vnets_active):
        logger.debug('Deleting VNET {0!r}'.format(vnet_not_active))
        session.delete(vnet_not_active)
        retval += 1

    return retval
