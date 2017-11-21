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
#import traceback

from eidangservices import settings
from eidangservices.federator.server.app import main as start_app
from eidangservices.federator.server.misc import realpath, CustomParser

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

    parser.add_argument('-p', '--port', type=int,
        default=settings.DEFAULT_SERVER_PORT, 
        help='server port')
    parser.add_argument('-R', '--routing', type=str, metavar='SERVICE_ID',
        default=settings.DEFAULT_ROUTING_SERVICE,
        choices=list(settings.EIDA_NODES),
        help='routing service identifier (choices: {%(choices)s})')
    parser.add_argument("-t", "--timeout", metavar='SECONDS', type=int,
        default=settings.DEFAULT_ROUTING_TIMEOUT,
        help="routing service request timeout in seconds " +
        "(default: %(default)s)")
    parser.add_argument("-r", "--retries", type=int,
        default=settings.DEFAULT_ROUTING_RETRIES,
        help="routing service number of retries (default: %(default)s)")
    parser.add_argument("-w", "--retry-wait", type=int,
        default=settings.DEFAULT_ROUTING_RETRY_WAIT,
        help="seconds to wait before each retry  (defaults: %(default)s)")
    parser.add_argument("-n", "--threads", type=int,
        default=settings.DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS,
        help="maximum number of download threads (default: %(default)s)")
    parser.add_argument(
        '--tmpdir', type=str, default='', 
        help='directory for temp files')
    parser.add_argument(
        '--debug', action='store_true', default=False, 
        help="run in debug mode")
    parser.add_argument('--logging-conf', dest='path_logging_conf', 
        metavar='LOGGING_CONF', type=real_file_path, 
        help="path to a logging configuration file")

    return parser

# build_parser ()

# -----------------------------------------------------------------------------
def main():
    logger_configured = False

    parser = build_parser()
    args = parser.parse_args(sys.argv[1:])

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
                    (args.path_logging_conf, err))
    start_app(args)

# main ()

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
