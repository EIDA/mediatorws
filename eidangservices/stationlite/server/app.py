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

import os
import sys
import traceback

from flask_restful import Api

from eidangservices import settings, utils
from eidangservices.stationlite.server import create_app
from eidangservices.stationlite.engine import db, orm
from eidangservices.stationlite.server.routes.stationlite import \
    StationLiteResource
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error, ErrorWithTraceback


__version__ = utils.get_version("stationlite")

# ----------------------------------------------------------------------------
DEFAULT_DBFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '../example/db/stationlite_2017-10-20.db')

# ----------------------------------------------------------------------------
class StationLiteWebservice(App):
    """
    Implementation of the EIDA StationLite webservice.
    """

    def build_parser(self, parents=[]):
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
        parser.add_argument('-D', '--db', type=utils.real_file_path,
                            default=DEFAULT_DBFILE, required=True,
                            help='Database (SQLite) file.')
        parser.add_argument('--debug', action='store_true', default=False,
                            help="Run in debug mode.")

        return parser

    # build_parser ()

    def run(self):
        """
        Run application.
        """

        # TODO(damb):
        #   - implement WSGI compatibility
        exit_code = utils.ExitCodes.EXIT_SUCCESS
        try:
            app = self.setup_app()
        
            if self.args.start_local:
                # run local Flask WSGI server (not for production)
                self.logger.info('Serving with local WSGI server.')
                app.run(threaded=True, debug=self.args.debug, port=self.args.port)
        
            # TODO(damb): prepare also for mod_wsgi
            pass
        except Error as err:
            self.logger.error(err)
            exit_code = utils.ExitCodes.EXIT_ERROR
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.critical('Local Exception: %s' % err)
            self.logger.critical('Traceback information: ' +
                                 repr(traceback.format_exception(
                                     exc_type, exc_value, exc_traceback)))
            exit_code = utils.ExitCodes.EXIT_ERROR

        sys.exit(utils.ExitCodes.EXIT_ERROR)

    # run ()

    def setup_app(self):
        """
        Setup and configure the Flask app with its API.

        :returns: The configured Flask application instance.
        :rtype :py:class:`flask.Flask`:
        """

        errors = {
            'NODATA': {
                'message': "Empty dataset.",
                'status': 204,
            },
        }

        api = Api(errors=errors)
        app_config = {
            'PORT': self.args.port,
            'DB': self.args.db,
            'SQLALCHEMY_DATABASE_URI':  "sqlite:///{}".format(self.args.db)
        }
        api.add_resource(
            StationLiteResource, "%s%s" %
            (settings.EIDA_ROUTING_PATH, settings.FDSN_QUERY_METHOD_TOKEN))
        
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
            config_section=settings.EIDA_STATIONLITE_HARVEST_CONFIG_SECTION)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(utils.ExitCodes.EXIT_ERROR)

    app.run()

# main ()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()

# ---- END OF <app.py> ----
