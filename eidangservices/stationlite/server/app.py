# -*- coding: utf-8 -*-
"""
EIDA NG stationlite server.
"""

# import logging
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


# ----------------------------------------------------------------------------
class StationLiteWebserviceBase(App):
    """
    Base production implementation of the EIDA StationLite webservice.
    """
    DB_PRAGMAS = ['PRAGMA case_sensitive_like=on']
    PROG = 'eida-stationlite'

    def build_parser(self, parents=[]):
        """
        Set up the commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(
            prog=self.PROG,
            description='Launch EIDA stationlite web service.',
            parents=parents)
        # optional arguments
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)

        # positional arguments
        parser.add_argument('db_url', type=url, metavar='URL',
                            help=('DB URL indicating the database dialect and '
                                  'connection arguments. For SQlite only a '
                                  'absolute file path is supported.'))

        return parser

    def run(self):
        """
        Run application.
        """
        # configure SQLAlchemy logging
        # log_level = self.logger.getEffectiveLevel()
        # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

        exit_code = ExitCodes.EXIT_SUCCESS
        try:
            self.logger.info('{}: Version v{}'.format(self.PROG, __version__))
            self.logger.debug('Configuration: {!r}'.format(self.args))
            app = self.setup_app()

            if self.args.db_url.startswith('sqlite'):
                configure_sqlite(self.DB_PRAGMAS)

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

    def setup_app(self):
        """
        Setup and configure the Flask app with its API.

        :returns: The configured Flask application instance.
        :rtype: :py:class:`flask.Flask`
        """

        api = Api()
        app_config = {
            'PROPAGATE_EXCEPTIONS': True,
            'SQLALCHEMY_DATABASE_URI': self.args.db_url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
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


class StationLiteWebserviceTest(StationLiteWebserviceBase):
    """
    Test implementation of the EIDA StationLite webservice.
    """

    PROG = 'eida-stationlite-test'

    def build_parser(self, parents=[]):
        """
        Set up the commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = super().build_parser(parents)
        parser.add_argument('-p', '--port', metavar='PORT', type=int,
                            default=settings.
                            EIDA_STATIONLITE_DEFAULT_SERVER_PORT,
                            help='server port')

        return parser

    def run(self):
        """
        Run application.
        """
        exit_code = ExitCodes.EXIT_SUCCESS
        try:
            self.logger.info('{}: Version v{}'.format(self.PROG, __version__))
            self.logger.debug('Configuration: {!r}'.format(self.args))
            app = self.setup_app()

            if self.args.db_url.startswith('sqlite'):
                configure_sqlite(self.DB_PRAGMAS)

            # run local Flask WSGI server (not for production)
            self.logger.info('Serving with local WSGI server.')
            app.run(threaded=True, port=self.args.port,
                    debug=(os.environ.get('DEBUG') == 'True'),
                    use_reloader=True, passthrough_errors=True)

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


StationLiteWebservice = StationLiteWebserviceBase


# ----------------------------------------------------------------------------
def _main(app):
    """
    main function executor for EIDA stationlite webservice
    """
    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            positional_required_args=['db_url'],
            config_section=settings.EIDA_STATIONLITE_CONFIG_SECTION)

    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(ExitCodes.EXIT_ERROR)

    return app.run()


def main_test():
    return _main(StationLiteWebserviceTest(log_id='STL'))


def main_prod():
    return _main(StationLiteWebservice(log_id='STL'))


main = main_prod


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main_test()
