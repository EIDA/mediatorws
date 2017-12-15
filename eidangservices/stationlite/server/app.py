#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <app.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
# 
# eida-stationlite is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version.
#
# eida-stationlite is distributed in the hope that it will be useful,
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
# 2017/12/15        V0.1    Daniel Armbruster; standing on the shoulders of
#                           Fabian :)
# =============================================================================
"""
EIDA NG stationlite server.

This file is part of the EIDA mediator/federator webservices.

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import *

import argparse
import configparser
import logging
import logging.config
import logging.handlers # needed for handlers defined in logging.conf
import os
import sys

from flask import Flask, g
from flask_restful import Api
#from flask_sqlalchemy import SQLAlchemy

from eidangservices import settings, utils
from eidangservices.stationlite.engine import db
from eidangservices.stationlite.server.routes.stationlite import \
    StationLiteResource
from eidangservices.stationlite.server.routes.wildcards import \
    WildcardsResource


__version__ = utils.get_version("stationlite")

# ----------------------------------------------------------------------------
logger_configured = False

DEFAULT_DBFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    '../example/db/stationlite_2017-10-20.db')

# ----------------------------------------------------------------------------
def build_parser(parents=[]):
    """
    Set up the stationlite commandline argument parser.

    :param list parents: list of parent parsers
    :returns: parser
    :rtype: :py:class:`argparse.ArgumentParser`
    """
    parser = utils.CustomParser(
        prog="eida-stationlite",
        description='Launch EIDA stationlite web service.',
        parents=parents)
    parser.add_argument('--version', '-V', action='version',
                        version='%(prog)s version ' + __version__)
    parser.add_argument('--start-local', action='store_true', default=False,
                        help="start a local WSGI server (not for production)")
    parser.add_argument('-p', '--port', metavar='PORT', type=int,
                        default=settings.EIDA_STATIONLITE_DEFAULT_SERVER_PORT,
                        help=('server port (only considered when serving '
                        'locally i.e. with --start-local)'))
    parser.add_argument('-D', '--db', type=str, default=DEFAULT_DBFILE, 
                        help='Database (SQLite) file.')
    parser.add_argument('--debug', action='store_true', default=False, 
                        help="Run in debug mode.")
    parser.add_argument('--logging-conf', dest='path_logging_conf',
                        metavar='LOGGING_CONF', type=utils.real_file_path,
                        help="path to a logging configuration file")

    return parser

# build_parser ()

def register_teardowns(app):
    
    @app.teardown_appcontext
    def close_db(error):
        """Closes the database again at the end of the request."""
        if hasattr(g, 'db_connection'):
            g.db_connection.close()

# register_teardowns ()

def setup_app(args):
    """
    Build the Flask app.

    :param dict args: app configuration arguments
    :rtype :py:class:`flask.Flask`:
    """

    errors = {
        'NODATA': {
            'message': "Empty dataset.",
            'status': 204,
        },
    }

    app = Flask(__name__)
    api = Api(errors=errors)

    ## routing service endpoint
    
    # query method
    api.add_resource(
        StationLiteResource, "%s%s" % (settings.EIDA_STATIONLITE_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))

    ## wildcardresolver service endpoint
    
    # query method
    api.add_resource(
        WildcardsResource, "%s%s" % (settings.EIDA_WILDCARDS_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))
 
    sqlalchemy_uri = "sqlite:///{}".format(args.db)
    
    app.config.update(
        PORT=args.port,
        DB=args.db,
        SQLALCHEMY_DATABASE_URI=sqlalchemy_uri)
    
    #app.app_context().push()
    api.init_app(app)
    
    register_teardowns(app)
    
    return app

# setup_app ()

# ----------------------------------------------------------------------------
def main():
    """
    main function for EIDA stationlite webservice
    """
    global logger_configured
    
    c_parser = argparse.ArgumentParser(formatter_class=\
                                        argparse.RawDescriptionHelpFormatter,
                                       add_help=False)

    c_parser.add_argument("-c", "--config",
                          dest="config_file",
                          default=settings.PATH_EIDANGWS_CONF,
                          metavar="PATH",
                          type=utils.realpath,
                          help=("path to EIDA NG webservices configuration "
                          "file (default: '%(default)s')"))

    args, remaining_argv = c_parser.parse_known_args()

    config_parser = configparser.ConfigParser()
    config_parser.read(args.config_file)
    defaults = {}
    try:
        defaults = dict(config_parser.items(
            settings.EIDA_STATIONLITE_CONFIG_SECTION))
    except:
        pass

    parser = build_parser(parents=[c_parser])
    # set defaults taken from configuration file
    parser.set_defaults(**defaults)
    # set the config_file default explicitly since adding the c_parser as a
    # parent would change the args.config_file to default=PATH_IROUTED_CONF
    # within the child parser
    parser.set_defaults(config_file=args.config_file)

    args = parser.parse_args(remaining_argv)

    # configure logger
    if args.path_logging_conf:
        try:
            logging.config.fileConfig(args.path_logging_conf)
            logger = logging.getLogger()
            logger_configured = True
            logger.info('Using logging configuration read from "%s"',
                        args.path_logging_conf)
        except Exception as err:
            print('WARNING: Setup logging failed for "%s" with "%s".' %
                  (args.path_logging_conf, err), file=sys.stderr)
            # NOTE(damb): Provide fallback syslog logger.
            logger = logging.getLogger()
            fallback_handler = logging.handlers.SysLogHandler('/dev/log',
                                                              'local0')
            fallback_handler.setLevel(logging.WARN)
            fallback_formatter = logging.Formatter(
                fmt=("<STL> %(asctime)s %(levelname)s %(name)s %(process)d "
                     "%(filename)s:%(lineno)d - %(message)s"),
                datefmt="%Y-%m-%dT%H:%M:%S%z")
            fallback_handler.setFormatter(fallback_formatter)
            logger.addHandler(fallback_handler)
            logger_configured = True
            logger.warning('Setup logging failed with %s. '
                           'Using fallback logging configuration.' % err)

    app = setup_app(args)

    if defaults and logger_configured:
        logger.debug("Default configuration from '%s': %s.",
                     args.config_file, defaults)

    if args.start_local:
        # run local Flask WSGI server (not for production)
        if logger_configured:
            logger.info('Serving with local WSGI server.')
        app.run(threaded=True, debug=args.debug, port=args.port)

    # TODO(damb): prepare also for mod_wsgi

# main ()

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()

# ---- END OF <app.py> ----
