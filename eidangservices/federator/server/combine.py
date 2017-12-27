# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <combine.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-federator).
# 
# eida-federator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version.
#
# eida-federator is distributed in the hope that it will be useful,
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
# 2017/10/20        V0.1    Daniel Armbruster; most of the code is based on
#                           https://github.com/GEOFON/fdsnws_scripts/blob/ \
#                               master/fdsnws_fetch.py
# =============================================================================
"""
Federator response combination facilities
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from builtins import *

import codecs
import datetime
import errno
import json
import logging
import os
import stat
import struct
import tempfile
import threading

from xml.etree import ElementTree as ET
from future.utils import iteritems

from eidangservices import settings
from eidangservices.federator.server import misc


# -----------------------------------------------------------------------------
class Combiner(object):
    """
    Abstract base class for combiners.

    With :py:method:`Combiner.create()` a factory method is provided returning
    concrete combiner implementations.
    """

    MIMETYPE = None
    LOGGER = 'flask.app.federator.combiner'


    def __init__(self, path_pipe):
        self.logger = logging.getLogger(self.LOGGER)
        self._path_pipe = path_pipe
        self._buffer_size = 0
        self.__buffer_lock = threading.Lock()
        self._lock = threading.Lock()

    @staticmethod
    def create(resp_format, **kwargs):
        """Factory method for combiners.

        :param str resp_format: A reponse format used by FDSN and EIDA
        webservices.
        :param dict kwargs: A dictionary passed to the combiner constructors.
        :return: A concrete :class:`Combiner` implementation
        :rtype: :class:`Combiner`
        :raises KeyError: if an invalid format string was passed
        """
        if resp_format == 'miniseed':
            return MseedCombiner(**kwargs)
        elif resp_format == 'text':
            return StationTextCombiner(**kwargs)
        elif resp_format == 'xml':
            return StationXMLCombiner(**kwargs)
        elif resp_format == 'json':
            return WFCatalogJSONCombiner(**kwargs)
        else:
            raise KeyError('Invalid combiner chosen.')

    @property
    def buffer_size(self):
        """
        Query function for the combiner's buffer_size.
        """
        with self.__buffer_lock:
            return self._buffer_size

    def add_buffer_size(self, val):
        """
        Add val to the combiner's buffer size
        """
        with self.__buffer_lock:
            self._buffer_size += val

    @property
    def _pipe(self):
        if (self._path_pipe and os.path.exists(self._path_pipe) and
                stat.S_ISFIFO(os.stat(self._path_pipe).st_mode)):
            try:
                self.logger.debug("Opening named pipe '%s' ..." %
                                  self._path_pipe)
                return os.open(self.__path_pipe, os.O_WRONLY | os.O_NONBLOCK)
            except OSError as err:
                if err.errno == errno.ENXIO:
                    self.logger.error("Could not open pipe '%s'. (%s)" %
                                      (self._path_pipe, str(err)))
                else:
                    raise
            finally:
                return None
        return None


    @property
    def mimetype(self):
        """
        Query function returning the combiner's mimetype.
        """
        return self.MIMETYPE

    def combine(self, ifd, **kwargs):
        """Combines input data read.

        :param ifd: A file like object data is read from.
        """
        raise NotImplementedError

    def dump(self, ofd, **kwargs):
        """Dump the combined data.

        :param ofd: Output file stream.
        """
        raise NotImplementedError

# class Combiner


class MseedCombiner(Combiner):
    """
    An implementation of a miniseed combiner.

    The input is merged record by record.

    .. note: The combiner is using a temporary file. However, future versions
    will write directly to an output file descriptor (ofd).
    """

    MIMETYPE = settings.MIMETYPE_MSEED

    DATA_ONLY_BLOCKETTE_NUMBER = 1000
    FIXED_DATA_HEADER_SIZE = 48
    MINIMUM_RECORD_LENGTH = 256

    _CHARS = "abcdefghijklmnopqrstuvwxyz0123456789_"

    def __init__(self, **kwargs):
        path_pipe = kwargs.get('path_pipe')
        super(MseedCombiner, self).__init__(path_pipe)

        self.__path_tempfile = os.path.join(tempfile.gettempdir(),
                                            misc.choices(self._CHARS, k=10))
        while os.path.isfile(self.__path_tempfile):
            self.__path_tempfile = os.path.join(tempfile.gettempdir(),
                                                misc.choices(self._CHARS,
                                                             k=10))
        self.tempfile_ofd = open(self.__path_tempfile, 'wb')

    # __init__()

    def combine(self, ifd, **kwargs):
        """Thread safe combination of miniseed data.

        The data is stored in a temporary file. Most of the code was taken from
        `fdsnws_fetch.py
        <https://github.com/andres-h/fdsnws_scripts/blob/master/fdsnws_fetch.py>`_
        :param ifd: File like object data is read from
        """
        size = 0

        record_idx = 1
        # NOTE: cannot use fixed chunk size, because
        # response from single node mixes mseed record
        # sizes. E.g., a 4096 byte chunk could contain 7
        # 512 byte records and the first 512 bytes of a
        # 4096 byte record, which would not be completed
        # in the same write operation
        while True:

            # read fixed header
            buf = ifd.read(self.FIXED_DATA_HEADER_SIZE)
            if not buf:
                break

            record = buf
            curr_size = len(buf)

            # get offset of data (value before last,
            # 2 bytes, unsigned short)
            data_offset_idx = self.FIXED_DATA_HEADER_SIZE - 4
            data_offset, = struct.unpack(
                b'!H',
                buf[data_offset_idx:data_offset_idx+2])

            if data_offset >= self.FIXED_DATA_HEADER_SIZE:
                remaining_header_size = data_offset - \
                    self.FIXED_DATA_HEADER_SIZE

            elif data_offset == 0:
                self.logger.debug("record %s: zero data offset" % (
                    record_idx))

                # This means that blockettes can follow,
                # but no data samples. Use minimum record
                # size to read following blockettes. This
                # can still fail if blockette 1000 is after
                # position 256
                remaining_header_size = \
                    self.MINIMUM_RECORD_LENGTH - \
                        self.FIXED_DATA_HEADER_SIZE

            else:
                # Full header size cannot be smaller than
                # fixed header size. This is an error.
                self.logger.warning("record %s: data offset smaller than "\
                    "fixed header length: %s, bailing "\
                    "out" % (record_idx, data_offset))
                break

            buf = ifd.read(remaining_header_size)
            if not buf:
                self.logger.warning("remaining header corrupt in record "\
                    "%s" % record_idx)
                break

            record += buf
            curr_size += len(buf)

            # scan variable header for blockette 1000
            blockette_start = 0
            b1000_found = False

            while blockette_start < remaining_header_size:

                # 2 bytes, unsigned short
                blockette_id, = struct.unpack(
                    b'!H',
                    buf[blockette_start:blockette_start+2])

                # get start of next blockette (second
                # value, 2 bytes, unsigned short)
                next_blockette_start, = struct.unpack(
                    b'!H',
                    buf[blockette_start+2:blockette_start+4])

                if blockette_id == self.DATA_ONLY_BLOCKETTE_NUMBER:

                    b1000_found = True
                    break

                elif next_blockette_start == 0:
                    # no blockettes follow
                    self.logger.debug("record %s: no blockettes follow "\
                        "after blockette %s at pos %s" % (
                            record_idx, blockette_id, blockette_start))
                    break

                else:
                    blockette_start = next_blockette_start

            # blockette 1000 not found
            if not b1000_found:
                self.logger.debug("record %s: blockette 1000 not found,"\
                    " stop reading" % record_idx)
                break

            # get record size (1 byte, unsigned char)
            record_size_exponent_idx = blockette_start + 6
            record_size_exponent, = struct.unpack(
                b'!B',
                buf[record_size_exponent_idx:\
                record_size_exponent_idx+1])

            remaining_record_size = \
                2**record_size_exponent - curr_size

            # read remainder of record (data section)
            buf = ifd.read(remaining_record_size)
            if not buf:
                self.logger.warning("cannot read data section of record "\
                    "%s" % record_idx)
                break

            record += buf

            with self._lock:
                self.tempfile_ofd.write(record)

            size += len(record)
            record_idx += 1

        self.add_buffer_size(size)
        if hasattr(ifd, 'geturl'):
            self.logger.info("combined %d bytes (%s) from %s" %
                             (size, self.mimetype, ifd.geturl()))

        return size

    # combine ()

    def dump(self, ofd, **kwargs):
        # TODO(damb): This hack will be removed as soon as stationlite is in
        # use.
        self.tempfile_ofd.close()
        # rename the temporary file to the file fd is pointing to
        if (os.path.isfile(self.__path_tempfile) and
                os.path.getsize(self.__path_tempfile)):
            fd_name = ofd.name
            os.rename(self.__path_tempfile, fd_name)

    # dump ()

# class MseedCombiner


class WFCatalogJSONCombiner(Combiner):
    """
    An implementation of a JSON combiner combining *WFCatalog* data.
    """

    MIMETYPE = settings.MIMETYPE_JSON

    def __init__(self, **kwargs):
        path_pipe = kwargs.get('path_pipe')
        super(WFCatalogJSONCombiner, self).__init__(path_pipe)
        self.__data = []

    def combine(self, ifd, **kwargs):
        """
        Combines WFCatalog JSON data.

        .. note: The WFCatalog JSON objects are simply merged into a single
        array.
        """
        stream_data = ''
        size = 0
        while True:
            buf = ifd.readline()

            if not buf:
                break

            if isinstance(buf, bytes):
                buf = buf.decode('utf-8')

            stream_data = ''.join((stream_data, buf))
            size += len(buf)

        self.__data.extend(json.loads(stream_data))
        self.add_buffer_size(size)
        if hasattr(ifd, 'geturl'):
            self.logger.info("combined %d bytes (%s) from %s" %
                             (size, self.mimetype, ifd.geturl()))

        return size

    # combine ()

    def dump(self, ofd, **kwargs):
        """
        Dump WFCatalog JSON data
        """
        if self.__data:
            json.dump(self.__data, codecs.getwriter('utf-8')(ofd), **kwargs)

# class WFCatalogJSONCombiner


class StationTextCombiner(Combiner):
    """
    An implementation of a text combiner combining *Station* data
    """

    MIMETYPE = settings.MIMETYPE_TEXT

    def __init__(self, **kwargs):
        path_pipe = kwargs.get('path_pipe')
        super(StationTextCombiner, self).__init__(path_pipe)
        self.__text = ''

    def combine(self, ifd, **kwargs):
        """Combines data.

        .. note: The first header line is inserted into the output. Additional
        header lines are skipped.
        """
        # this is the station service in text format
        stream_data = ''
        size = 0
        while True:
            buf = ifd.readline()

            if not buf:
                break

            if isinstance(buf, bytes):
                buf = buf.decode('utf-8')

            # skip header lines that start with '#'
            # NOTE: first header line is inserted in TextCombiner class
            if buf.startswith('#'):
                continue

            stream_data = ''.join((stream_data, buf))
            size += len(buf)

        if self.__text:
            self.__text = ''.join((self.__text, stream_data))
        else:
            self.__text = '\n'.join((settings.STATION_RESPONSE_TEXT_HEADER,
                                     stream_data))

        self.add_buffer_size(size)
        if hasattr(ifd, 'geturl'):
            self.logger.info("combined %d bytes (%s) from %s" %
                             (size, self.mimetype, ifd.geturl()))

        return size

    # combine ()

    def dump(self, ofd, **kwargs):
        """
        Dump Station text data.
        """
        if self.__text:
            ofd.write(self.__text.encode('utf-8'))

# class StationTextCombiner


class StationXMLCombiner(Combiner):
    """
    A concrete implementation of XML combiner combining *Station* data.

    The resulting format is the `FDSN StationXML
    <http://www.fdsn.org/xml/station/>`_ format.
    """

    MIMETYPE = settings.MIMETYPE_XML

    def __init__(self, **kwargs):
        path_pipe = kwargs.get('path_pipe')
        super(StationXMLCombiner, self).__init__(path_pipe)
        self.__et = None
        self.__qp = kwargs.get('qp')
        self.__geometry_par_type = self._get_geometry_par_type(self.__qp)

    def __combine_element(self, one, other):
        mapping = {}

        for el in one:
            try:
                eid = (el.tag, el.attrib['code'], el.attrib['start'])
                mapping[eid] = el

            except KeyError:
                pass

        for el in other:

            # skip Sender, Source, Module, ModuleURI, Created elements of
            # subsequent trees
            if el.tag in settings.STATIONXML_RESOURCE_METADATA_ELEMENTS:
                continue

            # station coords: check lat-lon box, remove stations outside
            if self.__geometry_par_type is not None and \
                el.tag == settings.STATIONXML_NETWORK_ELEMENT:

                self._remove_stations_outside_box(
                    el, self.__qp, self.__geometry_par_type)

            try:
                eid = (el.tag, el.attrib['code'], el.attrib['start'])

                try:
                    self.__combine_element(mapping[eid], el)

                except KeyError:
                    mapping[eid] = el
                    one.append(el)

            except KeyError:
                one.append(el)

    # __combine_element ()

    def _get_geometry_par_type(self, qp):
        # TODO(damb): Is probably not relevant anymore.

        par_short_count = 0
        par_long_count = 0

        for p, v in iteritems(qp):

            if p in settings.FDSNWS_GEOMETRY_PARAMS_SHORT:
                try:
                    _ = float(v)
                    par_short_count += 1
                except Exception:
                    continue

            elif p in settings.FDSNWS_GEOMETRY_PARAMS_LONG:
                try:
                    _ = float(v)
                    par_long_count += 1
                except Exception:
                    continue

        if par_long_count == len(settings.FDSNWS_GEOMETRY_PARAMS_LONG):
            par_type = 'long'
        elif par_short_count == len(settings.FDSNWS_GEOMETRY_PARAMS_SHORT):
            par_type = 'short'
        else:
            par_type = None

        return par_type

    # _get_geometry_par_type ()

    def _is_within_box(self, lat, lon, qp, geometry_par_type):

        if geometry_par_type == 'long':
            return (lat >= float(qp['minlatitude']) and
                    lat <= float(qp['maxlatitude']) and
                    lon >= float(qp['minlongitude']) and
                    lon <= float(qp['maxlongitude']))

        elif geometry_par_type == 'short':
            return (lat >= float(qp['minlat']) and
                    lat <= float(qp['maxlat']) and
                    lon >= float(qp['minlon']) and
                    lon <= float(qp['maxlon']))

        return False

    # _is_within_box ()

    def _remove_stations_outside_box(self, net, qp, geometry_par_type):

        stations = net.findall(settings.STATIONXML_STATION_ELEMENT)

        for st in stations:
            lat = float(st.find(settings.STATIONXML_LATITUDE_ELEMENT).text)
            lon = float(st.find(settings.STATIONXML_LONGITUDE_ELEMENT).text)

            if not self._is_within_box(lat, lon, qp, geometry_par_type):
                net.remove(st)

    # _remove_stations_outside_box ()

    def combine(self, ifd, **kwargs):
        fdread = ifd.read
        s = [0]

        def read(self, *args, **kwargs):
            """
            Storing the buffur length while reading.
            """
            buf = fdread(self, *args, **kwargs)
            s[0] += len(buf)
            return buf

        ifd.read = read

        if self.__et:
            self.__combine_element(self.__et.getroot(),
                                   ET.parse(ifd).getroot())

        else:
            self.__et = ET.parse(ifd)
            root = self.__et.getroot()

            # NOTE: this assumes well-formed StationXML
            # first StationXML tree: modify Source, Created
            try:
                source = root.find(
                    settings.STATIONXML_RESOURCE_METADATA_ELEMENTS[0])
                source.text = 'EIDA'
            except Exception:
                pass

            try:
                created = root.find(
                    settings.STATIONXML_RESOURCE_METADATA_ELEMENTS[1])
                created.text = datetime.datetime.utcnow().strftime(
                    '%Y-%m-%dT%H:%M:%S')
            except Exception:
                pass

            # remove Sender, Module, ModuleURI
            for tag in settings.STATIONXML_RESOURCE_METADATA_ELEMENTS[2:]:
                el = root.find(tag)
                if el is not None:
                    root.remove(el)

            # station coords: check lat-lon box, remove stations outside
            if self.__geometry_par_type is not None:

                networks = root.findall(settings.STATIONXML_NETWORK_ELEMENT)
                for net in networks:
                    self._remove_stations_outside_box(
                        net, self.__qp, self.__geometry_par_type)

        self.add_buffer_size(s[0])

        if hasattr(ifd, 'geturl'):
            self.logger.info("combined %d bytes (%s) from %s" %
                             (s[0], self.mimetype, ifd.geturl()))

        return s[0]

    # combine ()

    def dump(self, ofd, **kwargs):
        if self.__et:
            self.__et.write(ofd)

# class StationXMLCombiner

# ---- END OF <combine.py> ----
