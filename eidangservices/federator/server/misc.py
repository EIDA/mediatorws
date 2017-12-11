# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
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
# -----------------------------------------------------------------------------
"""
Miscellaneous utils.

This file is part of the EIDA mediator/federator webservices.
"""
from __future__ import (absolute_import, division, print_function,
        unicode_literals)

from builtins import *

import argparse
import datetime
import hashlib
import itertools
import os
import pkg_resources
import random
import re
import sys
import tempfile
import time

import fasteners
import marshmallow as ma
import webargs

from webargs.flaskparser import FlaskParser

from eidangservices import settings

dateutil_available = False
try:
    from dateutil import parser
    dateutil_available = True
except ImportError:
    dateutil_available = False


# from marshmallow (originally from Django)
_iso8601_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    # tzinfo must not be available
    r'(?P<tzinfo>(?!\Z|[+-]\d{2}(?::?\d{2})?))?$'
)

# -----------------------------------------------------------------------------
class SNCL(object):

    def __init__(self, network='*', station='*', location='*', channel='*',
            starttime=None, endtime=None):
        self.network = network
        self.station = station
        self.location = location
        self.channel = channel
        self.starttime = starttime
        self.endtime = endtime

    # __init__ ()

    def __eq__(self, other):
        """
        allows comparing SNCLs
        """
        if other.__class__ is self.__class__:
            return (other.network == self.network and
                    other.station == self.station and
                    other.location == self.location and
                    other.channel == self.channel and
                    other.starttime == self.starttime and
                    other.endtime == self.endtime)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return ("<SNCL(net=%r, sta=%r, loc=%r, cha=%r, start=%r, end=%r)>" %
                (self.network, self.station, self.location, self.channel,
                 self.starttime, self.endtime))

    def __str__(self):
        return ("%s %s %s %s %s %s" %
                (self.network, self.station, self.location, self.channel,
                 self.starttime, self.endtime))

# class SNCL


class ExitCodes:
    """
    Enum for exit codes.
    """
    EXIT_SUCCESS = 0
    EXIT_WARNING = 1
    EXIT_ERROR = 2

# class ExitCodes


class URLConnectionLock(fasteners.InterProcessLock):
    """
    A :py:class:`fasteners.InterProcessLock` wrapper encoding the URL passed by
    means of an hash within the lockfile's filename.
    """
    def __init__(self, url, path_lockdir=settings.PATH_LOCKDIR, 
            sleep_func=time.sleep, logger=None):
        """
        :param str url: url to be encoded within the lockfile's filename
        :param str path_lockdir: lockfile directory path
        :param sleep_func: reference to a sleep function
        :param logging.Logger logger: logger instance
        """
        hashed_url = hashlib.sha224(url).hexdigest()
        path = os.path.join(path_lockdir, hashed_url)
        super(URLConnectionLock, self).__init__(path, sleep_func, logger)

    # __init__ ()

# class URLConnectionLock


class CustomParser(argparse.ArgumentParser):

    def error(self, message):
        sys.stderr.write('USAGE ERROR: %s\n' % message)
        self.print_help()
        sys.exit(ExitCodes.EXIT_ERROR)

# class CustomParser


class FDSNWSParser(FlaskParser):
    """
    FDSNWS parser with enhanced SNCL parsing.
    """

    def parse_querystring(self, req, name, field):
        """
        Parse SNCL arguments from req.args.
        """
        def _get_values(keys, raw=False):
            """
            löok up keys in req.args
            :param keys: an iterable with keys to look up
            :param bool raw: return the raw value if True - else the value is
            splitted
            """
            for key in keys:
                val = req.args.get(key)
                if val:
                    if not raw:
                        return val.split(
                                    settings.FDSNWS_QUERY_LIST_SEPARATOR_CHAR)
                    return val
            return None

        # _get_values ()

        # preprocess the req.args multidict regarding SNCL parameters
        networks = _get_values(('net', 'networks')) or ['*']
        stations = _get_values(('sta', 'stations')) or ['*']
        locations = _get_values(('loc', 'locations')) or ['*']
        channels = _get_values(('cha', 'channels')) or ['*']

        sncls = []
        for prod in itertools.product(networks, stations, locations, channels):
            sncls.append({'net': prod[0],
                          'sta': prod[1],
                          'loc': prod[2],
                          'cha': prod[3]})
        # add times
        starttime = _get_values(('start', 'starttime'), raw=True)
        if starttime:
            for sncl_dict in sncls:
                sncl_dict['start'] = starttime
        endtime = _get_values(('end', 'endtime'), raw=True)
        if endtime:
            for sncl_dict in sncls:
                sncl_dict['end'] = endtime

        args = req.args.copy()
        args.setlist('sncls', sncls)

        # remove former scnl related values
        for key in ('net', 'network',
                     'sta', 'station',
                     'loc', 'location',
                     'cha', 'channel',
                     'start', 'starttime'
                     'end', 'endtime'):
            try:
                del args[key]
            except KeyError:
                pass

        return webargs.core.get_value(args, name, field)

    # parse_querystring ()

    def parse_form(self, req, name, field):
        """
        Intended to emulate parsing SNCL arguments from FDSNWS formatted
        postfiles.
        """

        buf = req.stream.read()
        if buf or req.stream.tell() == 0:
            req.data = buf
        
        if isinstance(req.data, bytes):
            req.data = req.data.decode('utf-8')

        # convert buffer into list
        req_buffer = req.data.split("\n")

        param_dict = {'sncls': []}

        for line in req_buffer:
            check_param = line.split(
                                settings.FDSNWS_QUERY_VALUE_SEPARATOR_CHAR)
            if len(check_param) == 2:
                
                # add query params
                param_dict[check_param[0].strip()] = check_param[1].strip()
                #self.logger.debug('Query parameter: %s' % check_param)
            elif len(check_param) == 1:
                # parse SNCL
                sncl = line.split()
                if len(sncl) == 6:
                    sncl = {
                            'net': sncl[0],
                            'sta': sncl[1],
                            'loc': sncl[2],
                            'cha': sncl[3],
                            'start': sncl[4],
                            'end': sncl[5]
                            }
                    param_dict['sncls'].append(sncl)
            else:
                #self.logger.warn("Ignoring illegal POST line: %s" % line)
                continue

        return webargs.core.get_value(param_dict, name, field)

    # parse_form ()

# class FDSNWSParser

fdsnws_parser = FDSNWSParser()
use_fdsnws_args = fdsnws_parser.use_args
use_fdsnws_kwargs = fdsnws_parser.use_kwargs

# -----------------------------------------------------------------------------
def get_version(namespace_pkg_name=None):
    """
    fetch version string

    :param str namespace_pkg_name: distribution name of the namespace package
    :returns: version string
    :rtype: str
    """
    try:
        # distributed as namespace package
        if namespace_pkg_name:
            return pkg_resources.get_distribution(namespace_pkg_name).version
        raise
    except:
        return pkg_resources.get_distribution("eidangservices").version

# get_version ()

def get_temp_filepath():
    """Return path of temporary file."""
    
    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

# get_temp_filepath ()


def realpath(p):
    return os.path.realpath(os.path.expanduser(p))

# realpath ()


def choices(seq, k=1):
    return ''.join(random.choice(seq) for i in range(k))

# choices ()


def from_fdsnws_datetime(datestring, use_dateutil=True):
    """
    parse a datestring from a string specified by the fdsnws datetime
    specification

    See: http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.1.pdf
    """
    IGNORE_TZ = True

    if len(datestring) == 10:
        # only YYYY-mm-dd is defined
        return datetime.datetime.combine(ma.utils.from_iso_date(datestring,
            use_dateutil), datetime.time())
    else:
        # from marshmallow
        if not _iso8601_re.match(datestring):
            raise ValueError('Not a valid ISO8601-formatted string.')
        # Use dateutil's parser if possible
        if dateutil_available and use_dateutil:
            return parser.parse(datestring, ignoretz=IGNORE_TZ)
        else:
            # Strip off microseconds and timezone info.
            return datetime.datetime.strptime(datestring[:19], 
                '%Y-%m-%dT%H:%M:%S')

# from_fdsnws_datetime ()

def fdsnws_isoformat(dt, localtime=False, *args, **kwargs):
    # ignores localtime parameter
    return dt.isoformat(*args, **kwargs)

def convert_scnl_dicts_to_query_params(sncls):
    """
    Convert a list of SNCLs to SNCL FDSNWS query parameters.

    :param list sncls: A list of SNCL dicts
    :return: SNCL related query parameters
    :retval: dict
    :raises ValueError: If temporal constraints differ between sncls.

    .. note::

        SNCLs are flattened.
    """
    retval = {}
    _temporal_constraints_params = ('starttime', 'endtime')
    if sncls:
        for sncl in sncls:
            for key, value in sncl.items():
                if key in retval:
                    retval[key].update([value])
                else:
                    retval[key] = set([value])
    for key, values in retval.items():
        if key in _temporal_constraints_params:
            if len(values) != 1:
                raise ValueError(
                        "SNCLs provide different temporal constraints.")
            retval[key] = values.pop()
        else:
            retval[key] = ','.join(values)

    return retval

# convert_scnl_dicts_to_query_params ()

# ---- END OF <misc.py> ----
