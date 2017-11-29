#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch federator server.

This file is part of the EIDA mediator/federator webservices.

"""

import argparse
import logging
import logging.config
import os
import sys
import tempfile
#import traceback

from flask import Flask
from flask_restful import Api
from __future__ import print_function

from eidangservices import settings
from eidangservices.federator.server.misc import realpath, CustomParser
from eidangservices.federator.server.routes.misc import \
    DataselectVersionResource, StationVersionResource, \
    WFCatalogVersionResource, DataselectWadlResource, \
    StationWadlResource, WFCatalogWadlResource 
from eidangservices.federator.server.routes.dataselect import DataselectResource
from eidangservices.federator.server.routes.station import StationResource
from eidangservices.federator.server.routes.wfcatalog import WFCatalogResource 

try:
    # Python 2.x
    import ConfigParser as configparser
except ImportError:
    # Python 3:
    import configparser



def real_file_path(p):
    p = realpath(p)
    if not os.path.isfile(p):
        raise argparse.ArgumentTypeError
    return p

# realpath_file ()

def real_dir_path(p):
    p = realpath(p)
    if not os.path.isdir(p):
        raise argparse.ArgumentTypeError
    return p

# real_dir_path ()

def build_parser(parents=[]):
    parser = CustomParser(
            prog="python -m federator.server",
            description='Launch EIDA federator web service.', 
            parents=parents)

    parser.add_argument(
        '--start-local', action='store_true', default=False, 
        help="start a local WSGI server (not for production)")
    parser.add_argument('-p', '--port', metavar='PORT', type=int,
        default=settings.EIDA_FEDERATOR_DEFAULT_SERVER_PORT, 
        help='server port (only considered when serving locally i.e. with ' +
        '--start-local)')
    parser.add_argument('-R', '--routing', type=str, metavar='SERVICE_ID',
        default=settings.DEFAULT_ROUTING_SERVICE,
        choices=list(settings.EIDA_NODES),
        help='routing service identifier (choices: {%(choices)s})')
    parser.add_argument("-t", "--timeout", metavar='SECONDS', type=int,
        default=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_TIMEOUT,
        help="routing/federating service request timeout in seconds " +
        "(default: %(default)s)")
    parser.add_argument("-r", "--retries", type=int,
        default=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRIES,
        help="routing/federating service number of retries "
        "(default: %(default)s)")
    parser.add_argument("-w", "--retry-wait", type=int,
        default=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_WAIT,
        help="seconds to wait before each retry  (default: %(default)s)")
    parser.add_argument("-L", "--retry-lock", action='store_true',
        default=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_LOCK,
        help="while retrying lock an URL for other federator instances " +
        "(default: %(default)s)")
    parser.add_argument("-n", "--threads", type=int,
        default=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS,
        help="maximum number of download threads (default: %(default)s)")
    parser.add_argument(
        '--tmpdir', type=str, default='', 
        help='directory for temp files')
    # TODO(damb): verify functionality - perhaps its better to use the logger
    # instead
    parser.add_argument(
        '--debug', action='store_true', default=False, 
        help="run in debug mode")
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

    ## station service endpoint
    
    # query method
    api.add_resource(
        StationResource, "%s%s" % (settings.FDSN_STATION_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))
        
    # version method
    api.add_resource(
        StationVersionResource, "%s%s" % (settings.FDSN_STATION_PATH, 
            settings.FDSN_VERSION_METHOD_TOKEN))
        
    # application.wadl method
    api.add_resource(
        StationWadlResource, "%s%s" % (settings.FDSN_STATION_PATH, 
            settings.FDSN_WADL_METHOD_TOKEN))

    ## dataselect service endpoint
    
    # query method
    api.add_resource(
        DataselectResource, "%s%s" % (settings.FDSN_DATASELECT_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))
        
    # queryauth method
    
    # version method
    api.add_resource(
        DataselectVersionResource, "%s%s" % (settings.FDSN_DATASELECT_PATH, 
            settings.FDSN_VERSION_METHOD_TOKEN))
    
    # application.wadl method
    api.add_resource(
        DataselectWadlResource, "%s%s" % (settings.FDSN_DATASELECT_PATH, 
            settings.FDSN_WADL_METHOD_TOKEN))
        
    ## wfcatalog service endpoint

    api.add_resource(
        WFCatalogResource, "%s%s" % (settings.FDSN_WFCATALOG_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))

    # version method
    api.add_resource(
        WFCatalogVersionResource, "%s%s" % (settings.FDSN_WFCATALOG_PATH, 
            settings.FDSN_VERSION_METHOD_TOKEN))
        
    # application.wadl method
    api.add_resource(
        WFCatalogWadlResource, "%s%s" % (settings.FDSN_WFCATALOG_PATH, 
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
        TMPDIR=tempfile.gettempdir()
    )

    return app

# setup_app()

# -----------------------------------------------------------------------------
def main(argv=None):
    logger_configured = False

    c_parser = argparse.ArgumentParser( 
        formatter_class=argparse.RawDescriptionHelpFormatter, 
        add_help=False)

    c_parser.add_argument("-c", "--config", 
        dest="config_file", default=settings.PATH_EIDANGWS_CONF,
        metavar="PATH", type=realpath,
        help="path to federator configuration file (default: '%(default)s')")

    args, remaining_argv = c_parser.parse_known_args()

    config_parser = configparser.ConfigParser()
    config_parser.read(args.config_file)
    defaults = {}
    try:
        defaults = dict(config_parser.items(
            settings.EIDA_FEDERATOR_CONFIG_SECTION))
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
            logger.info('Using logging configuration read from "%s"' %
                    args.path_logging_conf)
        except Exception as err:
            print('WARNING: Setup logging failed for "%s" with "%s".' % 
                    (args.path_logging_conf, err), file=sys.stderr)
            # TODO(damb): Provide a fallback mechanism

    app = setup_app(args)

    if defaults:
        logger.debug("Default configuration from '%s': %s." % 
                (args.config_file, defaults))


    if args.start_local:
        # run local Flask WSGI server (not for production)
        logger.info('Serving with local WSGI server.')
        app.run(threaded=True, debug=args.debug, port=args.port)
    else:
        try:
            from mod_wsgi import version
            logger.info('Serving with mod_wsgi.')
        except:
            pass
        return app

# main ()

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
