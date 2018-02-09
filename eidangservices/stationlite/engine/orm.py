# -----------------------------------------------------------------------------
# This is <orm.py>
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
# 2018/02/12        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA NG stationlite ORM.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import datetime

from sqlalchemy import (Column, Integer, Float, String, Unicode, DateTime,
                        ForeignKey, Boolean, Table)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

ORMBase = declarative_base()

# -----------------------------------------------------------------------------
LENGTH_CHANNEL_CODE = 3
LENGTH_DESCRIPTION = 512
LENGTH_LOCATION_CODE = 2
LENGTH_STD_CODE = 32
LENGTH_URL = 256

# -----------------------------------------------------------------------------
node_service_relation = Table(
    'node_service_relation', ORMBase.metadata,
    Column('node_ref', Integer, ForeignKey('services.oid')),
    Column('service_ref', Integer, ForeignKey('nodes.oid')))

vnet_relation_epoch_relation = Table(
    'vnet_relation_epoch_relation', ORMBase.metadata,
    Column(
        'vnet_relation_ref',
        Integer,
        ForeignKey('channelepoch_network_relation.oid')),
    Column('epoch_ref', Integer, ForeignKey('epochs.oid')))


class Epoch(ORMBase):
    __tablename__ = 'epochs'

    oid = Column(Integer, primary_key=True)
    starttime = Column(DateTime, nullable=False, index=True)
    endtime = Column(DateTime, index=True)

    # Many to Many: ChannelEpochNetworkRelation<->Epoch
    vnet_relations = relationship('ChannelEpochNetworkRelation',
                                  secondary=vnet_relation_epoch_relation,
                                  back_populates='epochs')

    def _as_datetime_tuple(self):
        return (self.starttime,
                datetime.datetime.max if self.endtime is None else \
                self.endtime)

    def __repr__(self):
        return '<Epoch(start=%r, end=%r)>' % (self.starttime,
                                              self.endtime)

# class Epoch


class Node(ORMBase):
    __tablename__ = 'nodes'

    oid = Column(Integer, primary_key=True)
    name = Column(String(LENGTH_STD_CODE), nullable=False, unique=True)
    description = Column(Unicode(LENGTH_DESCRIPTION))

    networks = relationship('NodeNetworkInventory', back_populates='node')
    services = relationship('Service',
                            secondary=node_service_relation,
                            back_populates='nodes')

    def __repr__(self):
        return '<Node(name=%s, description=%s)>' % (self.name,
                                                    self.description)

# class Node


class NodeNetworkInventory(ORMBase):
    __tablename__ = 'node_network_inventory'

    # association object pattern
    node_ref = Column(Integer, ForeignKey('nodes.oid'),
                      primary_key=True)
    network_ref = Column(Integer, ForeignKey('networks.oid'),
                         primary_key=True)
    lastseen = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)

    node = relationship('Node', back_populates='networks')
    network = relationship('Network', back_populates='nodes')

# class NodeNetworkInventory


class Network(ORMBase):
    __tablename__ = 'networks'

    oid = Column(Integer, primary_key=True)
    name = Column(String(LENGTH_STD_CODE), nullable=False, index=True)
    is_virtual = Column(Boolean, default=False)

    network_epochs = relationship('NetworkEpoch', back_populates='network')
    nodes = relationship('NodeNetworkInventory', back_populates='network')
    # many to many ChannelEpoch<->Network
    channel_epochs = relationship('ChannelEpochNetworkRelation',
                                  back_populates='network')

    def __repr__(self):
        return '<Network(name=%s, is_virtual=%s)>' % (self.name,
                                                      self.is_virtual)

# class Network


class NetworkEpoch(ORMBase):
    __tablename__ = 'networkepochs'

    oid = Column(Integer, primary_key=True)
    network_ref = Column(Integer, ForeignKey('networks.oid'))
    description = Column(Unicode(LENGTH_DESCRIPTION))
    starttime = Column(DateTime, index=True)
    endtime = Column(DateTime, index=True)
    lastseen = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)

    network = relationship('Network', back_populates='network_epochs')

# class NetworkEpoch


class ChannelEpochNetworkRelation(ORMBase):
    # association object pattern
    __tablename__ = 'channelepoch_network_relation'

    oid = Column(Integer, primary_key=True)
    channel_epoch_ref = Column(Integer, ForeignKey('channelepochs.oid'))
    network_ref = Column(Integer, ForeignKey('networks.oid'))
    lastseen = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)

    # Many to Many: ChannelEpochNetworkRelation<->Epoch
    epochs = relationship('Epoch',
                          secondary=vnet_relation_epoch_relation,
                          back_populates='vnet_relations')

    channel_epoch = relationship('ChannelEpoch', back_populates='networks')
    network = relationship('Network', back_populates='channel_epochs')

# ChannelEpochNetworkRelation


class ChannelEpoch(ORMBase):
    __tablename__ = 'channelepochs'

    oid = Column(Integer, primary_key=True)
    station_ref = Column(Integer, ForeignKey('stations.oid'))
    channel = Column(String(LENGTH_CHANNEL_CODE), nullable=False,
                     index=True)
    locationcode = Column(String(LENGTH_LOCATION_CODE), nullable=False,
                          index=True)
    starttime = Column(DateTime, nullable=False, index=True)
    endtime = Column(DateTime, index=True)
    longitude = Column(Float, nullable=False, index=True)
    latitude = Column(Float, nullable=False, index=True)
    lastseen = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)

    station = relationship('Station',
                           back_populates='channel_epochs')

    # many to many ChannelEpoch<->Endpoint
    endpoints = relationship('Routing', back_populates='channel_epoch')

    # many to many ChannelEpoch<->Network
    networks = relationship('ChannelEpochNetworkRelation',
                            back_populates='channel_epoch')

# class ChannelEpoch


class Station(ORMBase):
    __tablename__ = 'stations'

    oid = Column(Integer, primary_key=True)
    name = Column(String(LENGTH_STD_CODE), nullable=False, index=True)

    station_epochs = relationship('StationEpoch', back_populates='station')

    channel_epochs = relationship('ChannelEpoch', back_populates='station')

# class Station


class StationEpoch(ORMBase):
    __tablename__ = 'stationepochs'

    oid = Column(Integer, primary_key=True)
    station_ref = Column(Integer, ForeignKey('stations.oid'))
    description = Column(Unicode(LENGTH_DESCRIPTION))
    longitude = Column(Float, nullable=False, index=True)
    latitude = Column(Float, nullable=False, index=True)
    starttime = Column(DateTime, index=True)
    endtime = Column(DateTime, index=True)
    lastseen = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)

    station = relationship('Station', back_populates='station_epochs')

# class StationEpoch


class Routing(ORMBase):
    # association object pattern
    __tablename__ = 'routings'

    channel_epoch_ref = Column(Integer, ForeignKey('channelepochs.oid'),
                               primary_key=True)
    endpoint_ref = Column(Integer, ForeignKey('endpoints.oid'),
                          primary_key=True)
    starttime = Column(DateTime, index=True)
    endtime = Column(DateTime, index=True)
    lastseen = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)

    channel_epoch = relationship('ChannelEpoch', back_populates='endpoints')
    endpoint = relationship('Endpoint', back_populates='channel_epochs')

# class Routing


class Endpoint(ORMBase):
    __tablename__ = 'endpoints'

    oid = Column(Integer, primary_key=True)
    service_ref = Column(Integer, ForeignKey('services.oid'))
    url = Column(String(LENGTH_URL), nullable=False)

    # many to many ChannelEpoch<->Endpoint
    channel_epochs = relationship('Routing', back_populates='endpoint')

    service = relationship('Service', back_populates='endpoints')

    def __repr__(self):
        return '<Endpoint(url=%s)>' % self.url

# class Endpoint


class Service(ORMBase):
    __tablename__ = 'services'

    oid = Column(Integer, primary_key=True)
    name = Column(String(LENGTH_STD_CODE), nullable=False, unique=True)
    standard = Column(String(LENGTH_STD_CODE), nullable=False)

    endpoints = relationship('Endpoint', back_populates='service')

    nodes = relationship('Node',
                         secondary=node_service_relation,
                         back_populates='services')

    def __repr__(self):
        return '<Service(name=%s, standard=%s)>' % (self.name, self.standard)

# class Service


# ---- END OF <orm.py> ----
