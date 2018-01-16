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

from builtins import *

import functools

from collections import namedtuple

from intervaltree import Interval, IntervalTree

import eidangservices as eidangws

Epochs = IntervalTree

# ----------------------------------------------------------------------------
def fdsnws_to_sql_wildcards(str_old, like_multiple='%', like_single='_',
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
            '?', like_single).replace('*', like_multiple)

# fdsnws_to_sql_wildcards ()

# ----------------------------------------------------------------------------
@functools.total_ordering
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

    def id(self, sep='.'):
        # TODO(damb): configure separator globally (i.e. in settings module)
        return sep.join([self.network, self.station, self.location,
                        self.channel])

    def __new__(cls, network='*', station='*', location='*', channel='*'):
        return super().__new__(cls, network=network,
                               station=station,
                               location=location,
                               channel=channel)
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
        return '%s %s %s' % (str(self.stream), self.starttime, self.endtime)

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
                   epochs=epochs[(stream_epoch.starttime,
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
        # TODO(damb): check for a more elegant implementation
        return iter([StreamEpoch.from_sncl(network=self.network,
                                           station=self.station,
                                           location=self.location,
                                           channel=self.channel,
                                           starttime=epoch.begin,
                                           endtime=epoch.end)
                                           for epoch in self.epochs])
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
        se_schema = eidangws.schema.StreamEpochSchema(many=True)
        stream_epochs = se_schema.dump(list(self)).data
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
        modfiy epochs by performing a real intersection
        """
        # perform a real intersection i.e.
        # ------..----..--------
        #           +
        #    ---------------
        #           =
        #    ---..----..----
        for stream_id, epochs in self.d.items():

            _start = start
            _end = end

            if _start is None:
                _start = epochs.begin()
            if _end is None:
                _end = epochs.end()

            # slice at new boundaries
            epochs.slice(_start)
            epochs.slice(_end)
            # search and assign the overlap
            self.d[stream_id] = Epochs(sorted(epochs.search(_start,_end)))

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
        # TODO(damb): check for more elegant implementation
        return iter([StreamEpochs.from_stream(
                    Stream(**self.__stream_id_to_dict(stream_id)),
                    epochs=stream_epochs)
                    for stream_id, stream_epochs in self.d.items()])

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
