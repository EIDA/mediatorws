# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <sncl.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices is distributed in the hope that it will be useful,
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
# 2018/01/10        V0.1    Daniel Armbruster
# =============================================================================
"""
SNCL related utilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import contextlib
import datetime
import functools

from collections import namedtuple, OrderedDict

from intervaltree import IntervalTree

import eidangservices as eidangws

from eidangservices import settings, utils

Epochs = IntervalTree

# ----------------------------------------------------------------------------
@contextlib.contextmanager
def none_as_max(endtime):
    """
    Use ``datetime.datetime.max`` instead of ``None``.
    """
    # convert endtime to datetime.datetime.max if None
    end = endtime
    if end is None:
        end = datetime.datetime.max
    yield end

# none_as_max ()

@contextlib.contextmanager
def none_as_now(endtime, now=datetime.datetime.utcnow()):
    """
    Use ``datetime.datetime.max`` instead of ``None``.
    """
    # convert endtime to datetime.datetime.max if None
    end = endtime
    if end is None:
        end = now
    yield end

# none_as_now ()

@contextlib.contextmanager
def max_as_none(endtime):
    """
    Convert ``datetime.datetime.max`` to ``None``.
    """
    end = endtime
    if end == datetime.datetime.max:
        end = None
    yield end

# max_as_none ()

@contextlib.contextmanager
def max_as_empty(endtime):
    """
    Convert ``datetime.datetime.max`` to ``None``.
    """
    end = endtime
    if end == datetime.datetime.max:
        end = ''
    yield end

# max_as_empty ()

def fdsnws_to_sql_wildcards(str_old, like_multiple='%', like_single='_', # noqa
                            like_escape='/'):
    """
    Replace the FDSNWS wildcard characters in *str_old* with the corresponding
    SQL LIKE statement character.

    :param str like_multiple: Character replacing the FDSNWS * wildcard
    character
    :param str like_single: Character replacing the FDSNWS _ wildcard
    character
    :param str like_escape: Character used in the SQL ESCAPE clause.
    """

    # NOTE(damb): first escape the *like_single* character, then replace '?'
    return str_old.replace(
        like_single, like_escape+like_single).replace(
        settings.FDSNWS_QUERY_WILDCARD_SINGLE_CHAR, like_single).\
        replace(settings.FDSNWS_QUERY_WILDCARD_MULT_CHAR, like_multiple)

# fdsnws_to_sql_wildcards ()

# ----------------------------------------------------------------------------
@functools.total_ordering # noqa
class Stream(namedtuple('Stream',
                        ['network', 'station', 'location', 'channel'])):
    """
    This class represents a stream coming along with the properties:
        - network
        - station
        - location
        - channel

    .. note::

        For the sake of simplicity a Stream object is also named SNCL referring
        to the Stream object's properties.
    """
    __slots__ = ()

    FIELDS_SHORT = ('net', 'sta', 'loc', 'cha')

    def id(self, sep='.'):
        # TODO(damb): configure separator globally (i.e. in settings module)
        return sep.join([self.network, self.station, self.location,
                        self.channel])

    def __new__(cls, network='*', station='*', location='*', channel='*'):
        return super().__new__(cls, network=network,
                               station=station,
                               location=location,
                               channel=channel)

    @classmethod
    def from_route_attrs(cls, **kwargs):
        return super().__new__(cls,
                               network=kwargs.get('networkCode', '*'),
                               station=kwargs.get('stationCode', '*'),
                               location=kwargs.get('locationCode', '*'),
                               channel=kwargs.get('streamCode', '*'))

    def _asdict(self, short_keys=False):
        """Return a new OrderedDict which maps field names to their values."""
        fields = self.FIELDS_SHORT if short_keys else self._fields
        return OrderedDict(zip(fields, self))

    # _asdict ()

    def __eq__(self, other):
        return self.id() == other.id()

    def __lt__(self, other):
        return self.id() < other.id()

    def __repr__(self):
        return ('<Stream(net=%r, sta=%r, loc=%r, cha=%r)>' %
                (self.network, self.station, self.location, self.channel))

    def __str__(self):
        return ' '.join([self.network, self.station, self.location,
                        self.channel])

# class Stream


@functools.total_ordering
class StreamEpoch(namedtuple('StreamEpoch',
                  ['stream', 'starttime', 'endtime'])):
    """
    This class represents a stream epoch i.e. a Stream object + epoch
    (starttime + endtime).
    """

    __slots__ = ()

    FIELDS_SHORT = ('net', 'sta', 'loc', 'cha', 'start', 'end')

    def __new__(cls, stream, starttime=None, endtime=None):
        return super().__new__(cls,
                               stream=stream,
                               starttime=starttime,
                               endtime=endtime)

    @classmethod
    def from_sncl(cls, network='*', station='*', location='*', channel='*',
                  starttime=None, endtime=None):
        return cls(stream=Stream(network=network,
                                 station=station,
                                 location=location,
                                 channel=channel),
                   starttime=starttime,
                   endtime=endtime)

    @classmethod
    def from_snclline(cls, line, default_endtime=None):
        """
        Create a StreamEpoch from a SNCL line (FDSN POST format).

        :param str line: SNCL line in FDSN POST format i.e.
        `NET STA LOC CHA START END`
        :param :cls:`datetime.datetime` default_endtime: Substitute an empty
        endtime with the datetime passed.
        """
        if isinstance(line, bytes):
            line = line.decode('utf-8')

        args = line.strip().split(' ')
        end = None
        if len(args) == 6:
            end = utils.from_fdsnws_datetime(args[5])
        elif len(args) == 5 and default_endtime is not None:
            end = default_endtime

        return cls(stream=Stream(network=args[0],
                                 station=args[1],
                                 location=args[2],
                                 channel=args[3]),
                   starttime=utils.from_fdsnws_datetime(args[4]),
                   endtime=end)

    # from_snclline ()

    @classmethod
    def from_orm(cls, stream_epoch):
        return cls(stream=Stream(network=stream_epoch.network.name,
                                 station=stream_epoch.station.name,
                                 location=stream_epoch.location,
                                 channel=stream_epoch.channel),
                   starttime=stream_epoch.starttime,
                   endtime=stream_epoch.endtime)

    def id(self, sep='.'):
        return self.stream.id(sep=sep)

    def fdsnws_to_sql_wildcards(self, like_multiple='%', like_single='_',
                                like_escape='/'):
        """
        Replace the FDSNWS wildcard characters in *network*, *station*,
        *location* and *channel* with the corresponding SQL LIKE statement
        character. Since StreamEpoch is immutable a new StreamEpoch instance is
        returned.

        :param str like_multiple: Character replacing the FDSNWS * wildcard
        character
        :param str like_single: Character replacing the FDSNWS _ wildcard
        character
        :param str like_escape: Character used in the SQL ESCAPE clause.
        """
        net = fdsnws_to_sql_wildcards(self.network, like_multiple, like_single,
                                      like_escape)
        sta = fdsnws_to_sql_wildcards(self.station, like_multiple, like_single,
                                      like_escape)
        loc = fdsnws_to_sql_wildcards(self.location, like_multiple,
                                      like_single, like_escape)
        cha = fdsnws_to_sql_wildcards(self.channel, like_multiple, like_single,
                                      like_escape)
        stream = self.stream._replace(network=net, station=sta, location=loc,
                                      channel=cha)
        return self._replace(stream=stream)

    # fdsnws_to_sql_wildcards ()

    def slice(self, num=2, default_endtime=datetime.datetime.utcnow()):
        """
        Split StreamEpoch into `num` chunks.

        :param int num: Number of StreamEpochs to be splitted.
        :param :cls:`datetime.datetime` default_endtime: Default endtime to
        use in case `self.endtime == None`.
        :returns: List of :cls:`StreamEpoch` objects.
        """
        if num < 2:
            return self
        end = self.endtime if self.endtime else default_endtime
        t = Epochs.from_tuples([(self.starttime, end)])

        for n in range(1, num):
            t.slice(self.starttime + (end-self.starttime)/num*n)

        return [type(self)(stream=self.stream,
                           starttime=i.begin, endtime=i.end) for i in t]

    # slice ()

    def _asdict(self, short_keys=False):
        """Return a new OrderedDict which maps field names to their values."""
        fields = self.FIELDS_SHORT if short_keys else self._fields
        return OrderedDict(zip(fields, self))

    # _asdict ()

    @property
    def network(self):
        return self.stream.network

    @property
    def station(self):
        return self.stream.station

    @property
    def location(self):
        return self.stream.location

    @property
    def channel(self):
        return self.stream.channel

    def __eq__(self, other):
        """
        allows comparing StreamEpoch objects
        """
        return (self.stream == other.stream and
                self.starttime == other.starttime and
                self.endtime == other.endtime)
    # __eq__ ()

    def __lt__(self, other):
        if self.stream == other.stream:
            if self.starttime == other.starttime:
                if None not in (self.endtime, other.endtime):
                    return self.endtime < other.endtime
                elif self.endtime is None:
                    return False
                return True
            return self.starttime < other.starttime
        return self.stream < other.stream

    # __lt__ ()

    def __repr__(self):
        return ("<StreamEpoch(stream=%r, start=%r, end=%r)>" %
                (self.stream, self.starttime, self.endtime))

    def __str__(self):
        se_schema = eidangws.utils.schema.StreamEpochSchema()
        stream_epoch = se_schema.dump(self)
        return ' '.join(str(v) for v in stream_epoch.values())

# class StreamEpoch


@functools.total_ordering
class StreamEpochs(object):
    """
    This class represents a mapping of a Stream object to multiple epochs. In
    an abstract sense it is a container for StreamEpoch objects.

    Uses IntervalTree, https://github.com/chaimleib/intervaltree

    ..note::

        Intervals within the tree are automatically merged.
    """

    def __init__(self, network='*', station='*', location='*', channel='*',
                 epochs=[]):
        """
        :param str network: Network code
        :param str station: Station code
        :param str location: Location code
        :param str channel: Channel code
        :param list epochs: Epochs is a list of (t1, t2) tuples, with t1 and t2
        of type datetime.datetime. It can contain overlaps.
        The intervals are merged in the constructor.
        """

        self._stream = Stream(network=network,
                              station=station,
                              location=location,
                              channel=channel)

        try:
            self.epochs = Epochs.from_tuples(epochs)
        except TypeError:
            self.epochs = Epochs()
        self.epochs.merge_overlaps()

    # __init__ ()

    @classmethod
    def from_stream_epoch(cls, stream_epoch):
        return cls(network=stream_epoch.network,
                   station=stream_epoch.station,
                   location=stream_epoch.location,
                   channel=stream_epoch.channel,
                   epochs=[(stream_epoch.starttime,
                            stream_epoch.endtime)])

    @classmethod
    def from_stream(cls, stream, epochs=[]):
        return cls(network=stream.network,
                   station=stream.station,
                   location=stream.location,
                   channel=stream.channel,
                   epochs=epochs)

    def id(self):
        return self._stream.id()

    def merge(self, epochs):
        """
        Merge an epoch list into an existing SNCLE.
        :param list epochs: List of (t1, t2) tuples
        """

        for iv in epochs:
            self.epochs.addi(iv[0], iv[1])

        self.epochs.merge_overlaps()

    # merge ()

    def fdsnws_to_sql_wildcards(self, like_multiple='%', like_single='_',
                                like_escape='/'):
        """
        Replace the FDSNWS wildcard characters in *network*, *station*,
        *location* and *channel* with the corresponding SQL LIKE statement
        character. Replacement is done inplace.

        :param str like_multiple: Character replacing the FDSNWS * wildcard
        character
        :param str like_single: Character replacing the FDSNWS _ wildcard
        character
        :param str like_escape: Character used in the SQL ESCAPE clause.
        """
        net = fdsnws_to_sql_wildcards(self.network, like_multiple, like_single,
                                      like_escape)
        sta = fdsnws_to_sql_wildcards(self.station, like_multiple, like_single,
                                      like_escape)
        loc = fdsnws_to_sql_wildcards(self.location, like_multiple,
                                      like_single, like_escape)
        cha = fdsnws_to_sql_wildcards(self.channel, like_multiple, like_single,
                                      like_escape)

        self._stream = self._stream._replace(network=net, station=sta,
                                             location=loc, channel=cha)

    # fdsnws_to_sql_wildcards ()

    def modify_with_temporal_constraints(self, start=None, end=None):
        """
        modify epochs by performing a real intersection
        """
        # perform a real intersection i.e.
        # ------..----..--------
        #           +
        #    ---------------
        #           =
        #    ---..----..----
        _start = start
        _end = end

        if _start is None:
            _start = self.epochs.begin()
        if _end is None:
            _end = self.epochs.end()

        # slice at new boundaries
        self.epochs.slice(_start)
        self.epochs.slice(_end)
        # search and assign the overlap
        self.epochs = Epochs(sorted(self.epochs.search(_start, _end)))

    # modify_with_temporal_constraints ()

    @property
    def network(self):
        return self._stream.network

    @property
    def station(self):
        return self._stream.station

    @property
    def location(self):
        return self._stream.location

    @property
    def channel(self):
        return self._stream.channel

    @property
    def starttime(self):
        if not self.epochs.begin():
            return None
        return self.epochs.begin()

    @property
    def endtime(self):
        if not self.epochs.end():
            return None
        return self.epochs.end()

    @property
    def stream(self):
        """
        Expose stream to provide an interface equal to StreamEpoch.
        """
        return self._stream

    def __iter__(self):
        """
        iterator protocol by means of a generator
        """
        for epoch in self.epochs:
            yield StreamEpoch.from_sncl(network=self.network,
                                        station=self.station,
                                        location=self.location,
                                        channel=self.channel,
                                        starttime=epoch.begin,
                                        endtime=epoch.end)
    # __iter__ ()

    def __eq__(self, other):
        """
        allows comparing StreamEpochs objects
        """
        return (self._stream == other._stream and self.epochs == other.epochs)

    # __eq__ ()

    def __lt__(self, other):
        if self._stream == other._stream:
            if self.starttime == other.starttime:
                return self.epochs.end() < other.epochs.end()
            return self.epochs.begin() < other.epochs.begin()
        return self._stream < other._stream

    # __lt__ ()

    def __repr__(self):
        return ('<StreamEpochs(stream=%r, start=%r, end=%r)>' %
                (self._stream, self.starttime, self.endtime))

    def __str__(self):
        se_schema = eidangws.utils.schema.StreamEpochSchema(many=True)
        stream_epochs = se_schema.dump(list(self))
        return '\n'.join([' '.join(stream_epoch.values())
                         for stream_epoch in stream_epochs])

    # __str__ ()

# class StreamEpochs


class StreamEpochsHandler(object):
    """
    This class is intended to represent a handler/container for StreamEpochs
    objects.
    """

    def __init__(self, stream_epochs=[]):
        self.d = {}

        if stream_epochs:
            self.merge(stream_epochs)

    def modify_with_temporal_constraints(self, start=None, end=None):
        """
        modify epochs by performing a real intersection
        """
        # perform a real intersection i.e.
        # ------..----..--------
        #           +
        #    ---------------
        #           =
        #    ---..----..----
        for stream_id, epochs in self.d.items():
            se = StreamEpochs.from_stream(
                Stream(**self.__stream_id_to_dict(stream_id)),
                epochs=epochs)
            se.modify_with_temporal_constraints(start, end)

            self.d[se.id()] = se.epochs

    # modify_with_temporal_constraints ()

    def merge(self, others):
        """
        Merge other StreamEpochs to object.

        :param list others: List of :py:class:`StreamEpochs` objects
        """
        for stream_epochs in others:
            self._merge(stream_epochs.id(), stream_epochs.epochs)

    # merge ()

    def _merge(self, key, epochs):
        """
        Merge a Stream code (or object) and Epochs into StreamEpochHandler.
        """
        if key in self.d:
            # merge epoch interval trees (union)
            self.d[key] |= epochs
        else:
            # add new StreamEpochs object
            self.d[key] = epochs

        # tree for key may be overlapping
        self.d[key].merge_overlaps()

    # _merge ()

    @property
    def streams(self):
        return list(self)

    def __iter__(self):
        """
        iterator protocol by means of a generator
        """
        for stream_id, stream_epochs in self.d.items():
            yield StreamEpochs.from_stream(
                Stream(**self.__stream_id_to_dict(stream_id)),
                epochs=stream_epochs)

    # __iter__ ()

    def __repr__(self):
        return '<StreamEpochsHandler(streams=%r)>' % list(self)

    def __str__(self):
        return '\n'.join(str(stream_epochs) for stream_epochs in self)

    def __stream_id_to_dict(self, stream_id, sep='.'):
        # TODO(damb): configure separator globally (i.e. in settings module)
        net, sta, loc, cha = stream_id.split(sep)
        return dict(network=net,
                    station=sta,
                    location=loc,
                    channel=cha)

# class StreamEpochsHandler

# ---- END OF <scnl.py> ----
