#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <app.py>
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

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import sys
import tempfile
import traceback

from flask import Flask
from flask_restful import Api

from eidangservices import settings, utils
from eidangservices.federator.server.routes.misc import (
    DataselectVersionResource, StationVersionResource,
    WFCatalogVersionResource, DataselectWadlResource,
    StationWadlResource, WFCatalogWadlResource)
from eidangservices.federator.server.routes.dataselect import \
    DataselectResource
from eidangservices.federator.server.routes.station import StationResource
from eidangservices.federator.server.routes.wfcatalog import WFCatalogResource
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error


__version__ = utils.get_version("federator")

# -----------------------------------------------------------------------------
class FederatorWebservice(App):
    """
    Implementation of the EIDA Federator webservice.
    """

    def build_parser(self, parents=[]):
        """
        Set up the stationlite commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """

        parser = CustomParser(
            prog="eida-federator",
            description='Launch EIDA federator web service.',
            parents=parents)

        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)
        parser.add_argument('--start-local', action='store_true',
                            default=False,
                            help=("start a local WSGI server "
                                  "(not for production)"))
        parser.add_argument('-p', '--port', metavar='PORT', type=int,
                            default=settings.\
                            EIDA_FEDERATOR_DEFAULT_SERVER_PORT,
                            help=('server port (only considered when '
                                  'serving locally i.e. with --start-local)'))
        parser.add_argument('-R', '--routing-url', type=str, metavar='URL',
                            default=settings.DEFAULT_ROUTING_URL,
                            dest='routing',
                            # TODO(damb): Perform integrity check.
                            help=("routing service url (including identifier)"
                                  "(default: %(default)s)"))
        parser.add_argument("-t", "--timeout", metavar='SECONDS', type=int,
                            default=settings.\
                            EIDA_FEDERATOR_DEFAULT_ROUTING_TIMEOUT,
                            help=("routing/federating service request "
                                  "timeout in seconds (default: %(default)s)"))
        parser.add_argument("-r", "--retries", type=int,
                            default=settings.\
                            EIDA_FEDERATOR_DEFAULT_ROUTING_RETRIES,
                            help=("routing/federating service number of "
                                  "retries (default: %(default)s)"))
        parser.add_argument("-w", "--retry-wait", type=int,
                            default=settings.\
                            EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_WAIT,
                            help=("seconds to wait before each retry "
                                  "(default: %(default)s)"))
        parser.add_argument("-L", "--retry-lock", action='store_true',
                            default=settings.\
                            EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_LOCK,
                            help=("while retrying lock an URL for other "
                                  "federator instances "
                                  "(default: %(default)s)"))
        parser.add_argument("-n", "--threads", type=int,
                            default=settings.\
                            EIDA_FEDERATOR_DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS,  # noqa
                            help=("maximum number of download threads "
                                  "(default: %(default)s)"))
        parser.add_argument('--tmpdir', type=str, default='',
                            help='directory for temp files')

        return parser

    # build_parser ()

    def run(self):
        """
        Run application.
        """

        exit_code = utils.ExitCodes.EXIT_SUCCESS
        try:
            app = self.setup_app()

            if self.args.start_local:
                # run local Flask WSGI server (not for production)
                self.logger.info('Serving with local WSGI server.')
                app.run(threaded=True, debug=True, port=self.args.port)
            else:
                try:
                    from mod_wsgi import version  # noqa
                    self.logger.info('Serving with mod_wsgi.')
                except Exception:
                    pass
                return app

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

        sys.exit(exit_code)

    # run ()

    def setup_app(self):
        """
        Build the Flask app.

        :param dict args: app configuration arguments
        :rtype :py:class:`flask.Flask`:
        """
        # TODO(damb): Use StationLite webservice approach.

        errors = {
            'NODATA': {
                'message': "Empty dataset.",
                'status': 204,
            },
        }

        if self.args.tmpdir:
            tempfile.tempdir = self.args.tmpdir

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
            NUM_THREADS=self.args.threads,
            ROUTING_SERVICE=self.args.routing,
            ROUTING_TIMEOUT=self.args.timeout,
            ROUTING_RETRIES=self.args.retries,
            ROUTING_RETRY_WAIT=self.args.retry_wait,
            ROUTING_RETRY_LOCK=self.args.retry_lock,
            TMPDIR=tempfile.gettempdir())

        return app

    # setup_app()

# -----------------------------------------------------------------------------
def main():
    """
    main function for EIDA Federator
    """

    app = FederatorWebservice(log_id='FED')

    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            config_section=settings.EIDA_FEDERATOR_CONFIG_SECTION)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(utils.ExitCodes.EXIT_ERROR)

    return app.run()

# main ()


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()

# ---- END OF <app.py> ----
