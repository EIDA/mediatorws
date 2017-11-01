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

from webargs import core
from webargs.flaskparser import FlaskParser

from federator import settings

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


class FDSNWSParser(FlaskParser):

    STREAM_BUFFER = ''

    def parse_form(self, req, name, field):

        buf = req.stream.read()
        if buf or req.stream.tell() == 0:
            FDSNWSParser.STREAM_BUFFER = buf

        # convert buffer into list
        req_buffer = FDSNWSParser.STREAM_BUFFER.split("\n")

        param_dict = {}
        sncls = []

        for line in req_buffer:
            check_param = line.split(settings.FDSNWS_QUERY_VALUE_SEPARATOR_CHAR)
            if len(check_param) == 2:
                
                # add query params
                param_dict[check_param[0].strip()] = check_param[1].strip()
                #self.logger.debug('Query parameter: %s' % check_param)
            elif len(check_param) == 1:
                sncl = line.split()
                if len(sncl) == 6:
                    sncls.append(line.strip())
            else:
                #self.logger.warn("Ignoring illegal POST line: %s" % line)
                continue

            """
            elif len(check_param) == 1:
                # parse SNCL
                sncl = line.split()
                if len(sncl) == 6:
                    sncl_dict = {}
                    sncl_dict['network'] = sncl[0]
                    sncl_dict['station'] = sncl[1]
                    sncl_dict['location'] = sncl[2]
                    sncl_dict['channel'] = sncl[3]
                    sncl_dict['starttime'] = sncl[4]
                    sncl_dict['endtime'] = sncl[5]

                    return core.get_value(sncl_dict, name, field)

                else:
                    # TODO(damb): raise an error
                    pass 
                    #self.logger.debug('Adding POST content: "%s"' % line)
            """
        if sncls:
            param_dict['sncls'] = sncls
        return core.get_value(param_dict, name, field)

    # parse_form ()

# class FDSNWSParser

fdsnws_parser = FDSNWSParser()
use_fdsnws_args = fdsnws_parser.use_args

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
