# -*- coding: utf-8 -*-
"""
Miscellaneous utils.

This file is part of the EIDA mediator/federator webservices.

"""

import argparse
import datetime
import os
import re
import sys
import tempfile

import marshmallow as ma

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
class ExitCodes:
    """
    Enum for exit code
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

# -----------------------------------------------------------------------------
def get_temp_filepath():
    """Return path of temporary file."""
    
    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

# get_temp_filepath ()


def realpath(p):
    return os.path.realpath(os.path.expanduser(p))

# realpath ()

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
