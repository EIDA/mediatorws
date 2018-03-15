# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <utils.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EDIA NG webservices is distributed in the hope that it will be useful,
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
# 2017/12/12        V0.1    Daniel Armbruster
# =============================================================================
"""
General purpose utils for EIDA NG webservices
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import argparse
import collections
import datetime
import itertools
import os
import pkg_resources
import re
import sys

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
Route = collections.namedtuple('Route', ['url', 'streams'])


class ExitCodes:
    """
    Enum for exit codes.
    """
    EXIT_SUCCESS = 0
    EXIT_WARNING = 1
    EXIT_ERROR = 2

# class ExitCodes


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
            look up keys in req.args
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
        networks = _get_values(('net', 'network')) or ['*']
        stations = _get_values(('sta', 'station')) or ['*']
        locations = _get_values(('loc', 'location')) or ['*']
        channels = _get_values(('cha', 'channel')) or ['*']

        stream_epochs = []
        for prod in itertools.product(networks, stations, locations, channels):
            stream_epochs.append({'net': prod[0],
                                  'sta': prod[1],
                                  'loc': prod[2],
                                  'cha': prod[3]})
        # add times
        starttime = _get_values(('start', 'starttime'), raw=True)
        if starttime:
            for stream_epoch_dict in stream_epochs:
                stream_epoch_dict['start'] = starttime
        endtime = _get_values(('end', 'endtime'), raw=True)
        if endtime:
            for stream_epoch_dict in stream_epochs:
                stream_epoch_dict['end'] = endtime

        args = {'stream_epochs': stream_epochs}

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

        param_dict = {'stream_epochs': []}

        for line in req_buffer:
            check_param = line.split(
                settings.FDSNWS_QUERY_VALUE_SEPARATOR_CHAR)
            if len(check_param) == 2:

                # add query params
                param_dict[check_param[0].strip()] = check_param[1].strip()
                # self.logger.debug('Query parameter: %s' % check_param)
            elif len(check_param) == 1:
                # parse StreamEpoch
                stream_epoch = line.split()
                if len(stream_epoch) == 6:
                    stream_epoch = {
                        'net': stream_epoch[0],
                        'sta': stream_epoch[1],
                        'loc': stream_epoch[2],
                        'cha': stream_epoch[3],
                        'start': stream_epoch[4],
                        'end': stream_epoch[5]}
                    param_dict['stream_epochs'].append(stream_epoch)
            else:
                # self.logger.warn("Ignoring illegal POST line: %s" % line)
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
    except: # noqa
        return pkg_resources.get_distribution("eidangservices").version

# get_version ()


def realpath(p):
    return os.path.realpath(os.path.expanduser(p))

# realpath ()


def real_file_path(path):
    """
    check if file exists
    :returns: realpath in case the file exists
    :rtype: str
    :raises argparse.ArgumentTypeError: if file does not exist
    """
    path = realpath(path)
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError
    return path

# real_file_path ()


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


def convert_scnl_dicts_to_query_params(stream_epochs_dict):
    """
    Convert a list of StreamEpoch objects to StreamEpoch FDSNWS query
    parameters.

    :param list stream_epochs_dict: A list of :py:class`sncl.StreamEpoch` dicts
    :return: StreamEpoch related query parameters
    :retval: dict
    :raises ValueError: If temporal constraints differ between stream epochs.

    .. note::

        StreamEpoch objects are flattened.
    """
    retval = collections.defaultdict(set)
    _temporal_constraints_params = ('starttime', 'endtime')
    if stream_epochs_dict:
        for stream_epoch in stream_epochs_dict:
            for key, value in stream_epoch.items():
                retval[key].update([value])
    for key, values in retval.items():
        if key in _temporal_constraints_params:
            if len(values) != 1:
                raise ValueError("StreamEpoch objects provide "
                                 "multiple temporal constraints.")
            retval[key] = values.pop()
        else:
            retval[key] = ','.join(values)

    return retval

# convert_scnl_dicts_to_query_params ()

# ---- END OF <utils.py> ----
