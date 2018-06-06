# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <fdsnws.py>
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
# 2018/06/05        V0.1    Daniel Armbruster
# =============================================================================
"""
General purpose utils for EIDA NG webservices
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import functools
import itertools
import sys
import traceback

import webargs

from webargs.flaskparser import FlaskParser
from webargs.flaskparser import parser as flaskparser

from eidangservices import settings
from eidangservices.utils.httperrors import FDSNHTTPError


# -----------------------------------------------------------------------------
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
def with_exception_handling(func, service_id):
    """
    Method decorator providing a generic exception handling. A well-formatted
    FDSN exception instead is raised. The exception itself is logged.
    """
    @functools.wraps(func)
    def decorator(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except FDSNHTTPError as err:
            raise err
        except Exception as err:
            # NOTE(damb): Prevents displaying the full stack trace. Just log
            # it.
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.critical('Local Exception: %s' % type(err))
            self.logger.critical('Traceback information: ' +
                                 repr(traceback.format_exception(
                                     exc_type, exc_value, exc_traceback)))
            raise FDSNHTTPError.create(500, service_id=service_id)

    return decorator

# with_exception_handling ()


def with_fdsnws_exception_handling(service_id):
    return functools.partial(with_exception_handling,
                             service_id=service_id)

# with_fdsnws_exception_handling ()


def register_parser_errorhandler(service_id):
    """
    register webargs parser errorhandler
    """
    @fdsnws_parser.error_handler
    @flaskparser.error_handler
    def handle_parser_error(err, req):
        """
        configure webargs error handler
        """
        raise FDSNHTTPError.create(400, service_id=service_id)

    return handle_parser_error

# register_parser_errorhandler ()


# ---- END OF <fdsnws.py> ----
