#!/usr/bin/env python
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
Launch federator server.

This file is part of the EIDA mediator/federator webservices.

"""

from __future__ import print_function

import argparse
import logging
import logging.config
import logging.handlers  # needed for handlers defined in logging.conf
import os
import sys
import tempfile

from flask import Flask
from flask_restful import Api

from eidangservices import settings, utils
from eidangservices.federator.server.routes.misc import \
    DataselectVersionResource, StationVersionResource, \
    WFCatalogVersionResource, DataselectWadlResource, \
    StationWadlResource, WFCatalogWadlResource
from eidangservices.federator.server.routes.dataselect import \
    DataselectResource
from eidangservices.federator.server.routes.station import StationResource
from eidangservices.federator.server.routes.wfcatalog import WFCatalogResource

try:
    # Python 2.x
    import ConfigParser as configparser
except ImportError:
    # Python 3:
    import configparser


__version__ = utils.get_version("federator")

logger_configured = False

# -----------------------------------------------------------------------------
def real_file_path(path):
    """
    check if file exists
    :returns: realpath in case the file exists
    :rtype: str
    :raises argparse.ArgumentTypeError: if file does not exist
    """
    path = utils.realpath(path)
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError
    return path

# realpath_file ()

def real_dir_path(path):
    """
    check if directory exists
    :returns: realpath in case the directory exists
    :rtype: str
    :raises argparse.ArgumentTypeError: if directory does not exist
    """
    path = utils.realpath(path)
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError
    return path

# real_dir_path ()

def build_parser(parents=[]):
    """
    Set up the federator commandline argument parser.

    :param list parents: list of parent parsers
    :returns: parser
    :rtype: :py:class:`argparse.ArgumentParser`
    """

    parser = utils.CustomParser(
        prog="eida-federator",
        description='Launch EIDA federator web service.',
        parents=parents)

    parser.add_argument('--version', '-V', action='version',
                        version='%(prog)s version ' + __version__)
    parser.add_argument('--start-local', action='store_true', default=False,
                        help="start a local WSGI server (not for production)")
    parser.add_argument('-p', '--port', metavar='PORT', type=int,
                        default=settings.EIDA_FEDERATOR_DEFAULT_SERVER_PORT,
                        help='server port (only considered when serving ' +
                        'locally i.e. with --start-local)')
    parser.add_argument('-R', '--routing', type=str, metavar='SERVICE_ID',
                        default=settings.DEFAULT_ROUTING_SERVICE,
                        choices=list(settings.EIDA_NODES),
                        help='routing service identifier ' +
                        '(choices: {%(choices)s})')
    parser.add_argument("-t", "--timeout", metavar='SECONDS', type=int,
                        default=\
                        settings.EIDA_FEDERATOR_DEFAULT_ROUTING_TIMEOUT,
                        help="routing/federating service request timeout " +
                        "in seconds (default: %(default)s)")
    parser.add_argument("-r", "--retries", type=int,
                        default=\
                        settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRIES,
                        help="routing/federating service number of retries "
                        "(default: %(default)s)")
    parser.add_argument("-w", "--retry-wait", type=int,
                        default=\
                        settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_WAIT,
                        help="seconds to wait before each retry  " +
                        "(default: %(default)s)")
    parser.add_argument("-L", "--retry-lock", action='store_true',
                        default=\
                        settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_LOCK,
                        help="while retrying lock an URL for other " +
                        "federator instances (default: %(default)s)")
    parser.add_argument("-n", "--threads", type=int,
                        default=\
                        settings.
                        EIDA_FEDERATOR_DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS,
                        help="maximum number of download threads " +
                        "(default: %(default)s)")
    parser.add_argument('--tmpdir', type=str, default='',
                        help='directory for temp files')
    parser.add_argument('--logging-conf', dest='path_logging_conf',
                        metavar='LOGGING_CONF', type=real_file_path,
                        help="path to a logging configuration file")

    return parser

# build_parser ()

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

    if args.tmpdir:
        tempfile.tempdir = args.tmpdir

    app = Flask(__name__)

    api = Api(errors=errors)

    # station service endpoint
    # ----

    # query method
    api.add_resource(StationResource, "%s%s" %
                     (settings.FDSN_STATION_PATH,
                      settings.FDSN_QUERY_METHOD_TOKEN))

    # version method
    api.add_resource(StationVersionResource, "%s%s" %
                     (settings.FDSN_STATION_PATH,
                      settings.FDSN_VERSION_METHOD_TOKEN))

    # application.wadl method
    api.add_resource(StationWadlResource, "%s%s" %
                     (settings.FDSN_STATION_PATH,
                      settings.FDSN_WADL_METHOD_TOKEN))

    # dataselect service endpoint
    # ----

    # query method
    api.add_resource(DataselectResource, "%s%s" %
                     (settings.FDSN_DATASELECT_PATH,
                      settings.FDSN_QUERY_METHOD_TOKEN))

    # queryauth method

    # version method
    api.add_resource(DataselectVersionResource, "%s%s" %
                     (settings.FDSN_DATASELECT_PATH,
                      settings.FDSN_VERSION_METHOD_TOKEN))

    # application.wadl method
    api.add_resource(DataselectWadlResource, "%s%s" %
                     (settings.FDSN_DATASELECT_PATH,
                      settings.FDSN_WADL_METHOD_TOKEN))

    # wfcatalog service endpoint
    # ----

    api.add_resource(WFCatalogResource, "%s%s" %
                     (settings.FDSN_WFCATALOG_PATH,
                      settings.FDSN_QUERY_METHOD_TOKEN))

    # version method
    api.add_resource(WFCatalogVersionResource, "%s%s" %
                     (settings.FDSN_WFCATALOG_PATH,
                      settings.FDSN_VERSION_METHOD_TOKEN))

    # application.wadl method
    api.add_resource(WFCatalogWadlResource, "%s%s" %
                     (settings.FDSN_WFCATALOG_PATH,
                      settings.FDSN_WADL_METHOD_TOKEN))

    api.init_app(app)

    app.config.update(
        # TODO(damb): Pass log_level to app.config!
        NUM_THREADS=args.threads,
        ROUTING_SERVICE=args.routing,
        ROUTING_TIMEOUT=args.timeout,
        ROUTING_RETRIES=args.retries,
        ROUTING_RETRY_WAIT=args.retry_wait,
        ROUTING_RETRY_LOCK=args.retry_lock,
        TMPDIR=tempfile.gettempdir())

    return app

# setup_app()

# -----------------------------------------------------------------------------
def main():
    """
    main for EIDA federator webservice
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
                          help="path to federator configuration file " +
                          "(default: '%(default)s')")

    args, remaining_argv = c_parser.parse_known_args()

    config_parser = configparser.ConfigParser()
    config_parser.read(args.config_file)
    defaults = {}
    try:
        defaults = dict(config_parser.items(
            settings.EIDA_FEDERATOR_CONFIG_SECTION))
    except Exception:
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
                fmt=("<FED> %(asctime)s %(levelname)s %(name)s %(process)d "
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
        app.run(threaded=True, debug=True, port=args.port)
    else:
        try:
            from mod_wsgi import version # noqa
            if logger_configured:
                logger.info('Serving with mod_wsgi.')
        except Exception:
            pass
        return app

# main ()


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
