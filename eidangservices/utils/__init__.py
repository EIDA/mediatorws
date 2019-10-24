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
General purpose utils for EIDA NG webservices.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import argparse
import collections
import datetime
#import logging
import os
import re

import marshmallow as ma

from flask import make_response

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
    r'(?P<tzinfo>Z|(?![+-]\d{2}(?::?\d{2})?))?$'
)

# -----------------------------------------------------------------------------
Route = collections.namedtuple('Route', ['url', 'streams'])
"""
Container for routes.

:param str url: URL
:param list streams: List of stream epoch like objects (see
    :py:mod:`eidangservices.utils.sncl` module).
"""


# -----------------------------------------------------------------------------
def realpath(p):
    return os.path.realpath(os.path.expanduser(p))

# realpath ()


def real_file_path(path):
    """
    Check if file exists.

    :param str path: Path to be checked
    :returns: realpath in case the file exists
    :rtype: str
    :raises argparse.ArgumentTypeError: if file does not exist
    """
    path = realpath(path)
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError
    return path

# real_file_path ()


def real_dir_path(path):
    """
    Check if directory exists.

    :param str path: Path to be checked
    :returns: realpath in case the directory exists
    :rtype: str
    :raises argparse.ArgumentTypeError: if directory does not exist
    """
    path = realpath(path)
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError
    return path

# real_dir_path ()


def from_fdsnws_datetime(datestring, use_dateutil=True):
    """
    Parse a datestring from a string specified by the FDSNWS datetime
    specification.

    :param str datestring: String to be parsed
    :param bool use_dateutil: Make use of the :code:`dateutil` package if set
        to :code:`True`
    :returns: Datetime
    :rtype: :py:class:`datetime.datetime`

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
    """
    Convert a :py:class:`datetime.datetime` object to a ISO8601 conform string.

    :param datetime.datetime dt: Datetime object to be converted
    :param bool localtime: The parameter is ignored
    :returns: ISO8601 conform datetime string
    :rtype: str
    """
    # ignores localtime parameter
    return dt.isoformat(*args, **kwargs)


def convert_sncl_dicts_to_query_params(stream_epochs_dict):
    """
    Convert a list of :py:class:`sncl.StreamEpoch` objects to FDSNWS HTTP
    **GET** query parameters.

    :param list stream_epochs_dict: A list of :py:class:`sncl.StreamEpoch`
        dictionaries
    :return: StreamEpoch related FDSNWS conform HTTP **GET** query parameters
    :rtype: :py:class:`dict`
    :raises ValueError: If temporal constraints differ between stream epochs.

    Usage:

    .. code::

        se_schema = StreamEpochSchema(many=True, context={'request': self.GET})
        retval = convert_sncl_dicts_to_query_params(
            se_schema.dump(stream_epochs))

    .. note::

        :py:class:`sncl.StreamEpoch` objects are flattened.
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

# convert_sncl_dicts_to_query_params ()

def get_version_response(version_string):
    """
    Return :py:class:`flask.Response` object for version string with correct
    mimetype.

    :param str version_string: Version string to be responded
    :rtype: :py:class:`flask.Response`
    """

    response = make_response(version_string)
    response.headers['Content-Type'] = settings.VERSION_MIMETYPE
    return response

# get_version_response ()

# ---- END OF <utils.py> ----
