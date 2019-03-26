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

from builtins import * # noqa

#import logging
import argparse
import os
import sys
import traceback

from flask_restful import Api

from eidangservices import settings
from eidangservices.stationlite import __version__
from eidangservices.stationlite.engine.db import configure_sqlite
from eidangservices.stationlite.server import create_app
from eidangservices.stationlite.server.routes.stationlite import \
    StationLiteResource
from eidangservices.stationlite.server.routes.misc import \
    StationLiteVersionResource, StationLiteWadlResource
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error, ErrorWithTraceback, ExitCodes


# -----------------------------------------------------------------------------
class ModWSGIError(ErrorWithTraceback):
    """Base mod_wsgi error ({})."""

# ----------------------------------------------------------------------------
def url(url):
    """
    check if SQLite URL is absolute.
    """
    if (url.startswith('sqlite:') and not
            (url.startswith('////', 7) or url.startswith('///C:', 7))):
        raise argparse.ArgumentTypeError('SQLite URL must be absolute.')
    return url

# url ()

# ----------------------------------------------------------------------------
class StationLiteWebservice(App):
    """
    Implementation of the EIDA StationLite webservice.
    """
    DB_PRAGMAS = ['PRAGMA case_sensitive_like=on']

    def build_parser(self, parents=[]):
        """
        Set up the stationlite commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(
            prog="eida-stationlite",
            description='Launch EIDA stationlite web service.',
            parents=parents)
        # optional arguments
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)
        parser.add_argument('--start-local', action='store_true',
                            default=False,
                            help=("start a local WSGI server "
                                  "(not for production)"))
        parser.add_argument('-p', '--port', metavar='PORT', type=int,
                            default=settings.\
                            EIDA_STATIONLITE_DEFAULT_SERVER_PORT,
                            help=('server port (only considered when serving '
                                  'locally i.e. with --start-local)'))

        # positional arguments
        parser.add_argument('db_url', type=url, metavar='URL',
                            help=('DB URL indicating the database dialect and '
                                  'connection arguments. For SQlite only a '
                                  'absolute file path is supported.'))

        return parser

    # build_parser ()

    def run(self):
        """
        Run application.
        """
        # configure SQLAlchemy logging
        # log_level = self.logger.getEffectiveLevel()
        # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

        exit_code = ExitCodes.EXIT_SUCCESS
        try:
            app = self.setup_app()

            if self.args.db_url.startswith('sqlite'):
                configure_sqlite(self.DB_PRAGMAS)

            if self.args.start_local:
                # run local Flask WSGI server (not for production)
                self.logger.info('Serving with local WSGI server.')
                app.run(
                    threaded=True, port=self.args.port,
                    debug=(os.environ.get('DEBUG') == 'True'))
            else:
                try:
                    from mod_wsgi import version  # noqa
                    self.logger.info('Serving with mod_wsgi.')
                except Exception as err:
                    raise ModWSGIError(err)

                return app

        except Error as err:
            self.logger.error(err)
            exit_code = ExitCodes.EXIT_ERROR
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.critical('Local Exception: %s' % err)
            self.logger.critical('Traceback information: ' +
                                 repr(traceback.format_exception(
                                     exc_type, exc_value, exc_traceback)))
            exit_code = ExitCodes.EXIT_ERROR

        sys.exit(exit_code)

    # run ()

    def setup_app(self):
        """
        Setup and configure the Flask app with its API.

        :returns: The configured Flask application instance.
        :rtype: :py:class:`flask.Flask`
        """

        api = Api()
        app_config = {
            'PROPAGATE_EXCEPTIONS': True,
            'PORT': self.args.port,
            'SQLALCHEMY_DATABASE_URI': self.args.db_url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False
        }
        # query method
        api.add_resource(
            StationLiteResource, "%s%s" %
            (settings.EIDA_ROUTING_PATH, settings.FDSN_QUERY_METHOD_TOKEN))

        # version method
        api.add_resource(StationLiteVersionResource, "%s%s" %
                         (settings.EIDA_ROUTING_PATH,
                          settings.FDSN_VERSION_METHOD_TOKEN))

        # application.wadl method
        api.add_resource(StationLiteWadlResource, "%s%s" %
                         (settings.EIDA_ROUTING_PATH,
                          settings.FDSN_WADL_METHOD_TOKEN))

        app = create_app(config_dict=app_config)
        api.init_app(app)
        return app

    # setup_app ()

# class StationLiteWebservice


# ----------------------------------------------------------------------------
def main():
    """
    main function for EIDA stationlite webservice
    """

    app = StationLiteWebservice(log_id='STL')

    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            positional_required_args=['db_url'],
            config_section=settings.EIDA_STATIONLITE_CONFIG_SECTION,
            interpolation=None)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(ExitCodes.EXIT_ERROR)

    return app.run()

# main ()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()

# ---- END OF <app.py> ----
