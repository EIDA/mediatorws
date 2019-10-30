# -*- coding: utf-8 -*-
"""
EIDA NG stationlite ORM.
"""

import datetime

from sqlalchemy import (Column, Integer, Float, String, Unicode, DateTime,
                        ForeignKey)
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import relationship

# -----------------------------------------------------------------------------
LENGTH_CHANNEL_CODE = 3
LENGTH_DESCRIPTION = 512
LENGTH_LOCATION_CODE = 2
LENGTH_STD_CODE = 32
LENGTH_URL = 256


# -----------------------------------------------------------------------------
class Base:

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    oid = Column(Integer, primary_key=True)


class EpochMixin:

    @declared_attr
    def starttime(cls):
        return Column(DateTime, nullable=False, index=True)

    @declared_attr
    def endtime(cls):
        return Column(DateTime, index=True)


class LastSeenMixin:

    @declared_attr
    def lastseen(cls):
        return Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)


# -----------------------------------------------------------------------------
ORMBase = declarative_base(cls=Base)


class Network(ORMBase):

    name = Column(String(LENGTH_STD_CODE), nullable=False, index=True)

    network_epochs = relationship('NetworkEpoch', back_populates='network')
    channel_epochs = relationship('ChannelEpoch',
                                  back_populates='network')
    stream_epochs = relationship('StreamEpoch', back_populates='network')

    def __repr__(self):
        return '<Network(code=%s)>' % self.name


class NetworkEpoch(EpochMixin, LastSeenMixin, ORMBase):

    network_ref = Column(Integer, ForeignKey('network.oid'),
                         index=True)
    description = Column(Unicode(LENGTH_DESCRIPTION))

    network = relationship('Network', back_populates='network_epochs')


class ChannelEpoch(EpochMixin, LastSeenMixin, ORMBase):

    network_ref = Column(Integer, ForeignKey('network.oid'),
                         index=True)
    station_ref = Column(Integer, ForeignKey('station.oid'),
                         index=True)
    channel = Column(String(LENGTH_CHANNEL_CODE), nullable=False,
                     index=True)
    locationcode = Column(String(LENGTH_LOCATION_CODE), nullable=False,
                          index=True)

    network = relationship('Network',
                           back_populates='channel_epochs')
    station = relationship('Station',
                           back_populates='channel_epochs')

    # many to many ChannelEpoch<->Endpoint
    endpoints = relationship('Routing', back_populates='channel_epoch')

    def __repr__(self):
        return ('<ChannelEpoch(network=%r, station=%r, channel=%r, '
                'location=%r, starttime=%r, endtime=%r)>' %
                (self.network, self.station, self.channel,
                 self.locationcode, self.starttime, self.endtime))


class Station(ORMBase):

    name = Column(String(LENGTH_STD_CODE), nullable=False, index=True)

    station_epochs = relationship('StationEpoch', back_populates='station')

    channel_epochs = relationship('ChannelEpoch', back_populates='station')
    stream_epochs = relationship('StreamEpoch', back_populates='station')

    def __repr__(self):
        return '<Station(code=%s)>' % self.name


class StationEpoch(EpochMixin, LastSeenMixin, ORMBase):

    station_ref = Column(Integer, ForeignKey('station.oid'),
                         index=True)
    description = Column(Unicode(LENGTH_DESCRIPTION))
    longitude = Column(Float, nullable=False, index=True)
    latitude = Column(Float, nullable=False, index=True)

    station = relationship('Station', back_populates='station_epochs')


class Routing(EpochMixin, LastSeenMixin, ORMBase):

    channel_epoch_ref = Column(Integer, ForeignKey('channelepoch.oid'),
                               index=True)
    endpoint_ref = Column(Integer, ForeignKey('endpoint.oid'),
                          index=True)

    channel_epoch = relationship('ChannelEpoch', back_populates='endpoints')
    endpoint = relationship('Endpoint', back_populates='channel_epochs')

    def __repr__(self):
        return ('<Routing(url=%s, starttime=%r, endtime=%r)>' %
                (self.endpoint.url, self.starttime, self.endtime))


class Endpoint(ORMBase):

    service_ref = Column(Integer, ForeignKey('service.oid'),
                         index=True)
    url = Column(String(LENGTH_URL), nullable=False)

    # many to many ChannelEpoch<->Endpoint
    channel_epochs = relationship('Routing', back_populates='endpoint')

    service = relationship('Service', back_populates='endpoints')

    def __repr__(self):
        return '<Endpoint(url=%s)>' % self.url


class Service(ORMBase):

    name = Column(String(LENGTH_STD_CODE), nullable=False, unique=True)

    endpoints = relationship('Endpoint', back_populates='service')

    def __repr__(self):
        return '<Service(name=%s)>' % self.name


class StreamEpochGroup(ORMBase):

    name = Column(String(LENGTH_STD_CODE), nullable=False, unique=True)

    stream_epochs = relationship('StreamEpoch',
                                 back_populates='stream_epoch_group')

    def __repr__(self):
        return '<StreamEpochGroup(code=%s)>' % self.name


# TODO(damb): Find a way to map sncl.StreamEpoch to orm.StreamEpoch more
# elegantly
class StreamEpoch(EpochMixin, LastSeenMixin, ORMBase):

    network_ref = Column(Integer, ForeignKey('network.oid'),
                         index=True)
    station_ref = Column(Integer, ForeignKey('station.oid'),
                         index=True)
    stream_epoch_group_ref = Column(Integer,
                                    ForeignKey('streamepochgroup.oid'),
                                    index=True)
    channel = Column(String(LENGTH_CHANNEL_CODE), nullable=False,
                     index=True)
    location = Column(String(LENGTH_LOCATION_CODE), nullable=False,
                      index=True)

    station = relationship('Station',
                           back_populates='stream_epochs')
    network = relationship('Network',
                           back_populates='stream_epochs')
    stream_epoch_group = relationship('StreamEpochGroup',
                                      back_populates='stream_epochs')

    def __repr__(self):
        return ('<StreamEpoch(network=%r, station=%r, channel=%r, '
                'location=%r, starttime=%r, endtime=%r)>' %
                (self.network, self.station, self.channel, self.location,
                 self.starttime, self.endtime))
