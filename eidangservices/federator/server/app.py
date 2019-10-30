#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch EIDA NG Federator.
"""

import argparse
import copy
import json
import os
import sys
import tempfile
import traceback

from flask_restful import Api

from eidangservices import settings
from eidangservices.federator import __version__
from eidangservices.federator.server import create_app
from eidangservices.federator.server.misc import KeepTempfiles
from eidangservices.federator.server.routes.misc import (
    DataselectVersionResource, StationVersionResource,
    WFCatalogVersionResource, DataselectWadlResource,
    StationWadlResource, WFCatalogWadlResource)
from eidangservices.federator.server.routes.dataselect import \
    DataselectResource
from eidangservices.federator.server.routes.station import StationResource
from eidangservices.federator.server.routes.wfcatalog import WFCatalogResource
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error, ExitCodes


def thread_config(config_dict):
    """
    Parse a federator thread configuration dictionary.

    :param str config_dict: Configuration dictionary
    :retval: dict
    """
    try:
        config_dict = json.loads(config_dict)
    except Exception:
        raise argparse.ArgumentTypeError(
            'Invalid thread configuration dictionary syntax.')
    retval = copy.deepcopy(settings.EIDA_FEDERATOR_THREAD_CONFIG)
    try:
        for k, v in config_dict.items():
            if k not in settings.EIDA_FEDERATOR_THREAD_CONFIG:
                raise ValueError(
                    'Invalid thread configuration key {!r}.'.format(k))
            retval[k] = int(v)
    except ValueError as err:
        raise argparse.ArgumentTypeError(err)

    return retval


def keeptempfile_config(arg):
    """
    Populate the corresponding :code:`enum` value from the CLI configuration.
    """
    return getattr(KeepTempfiles, arg.upper().replace('-', '_'))


# -----------------------------------------------------------------------------
class FederatorWebserviceBase(App):
    """
    Base production implementation of the EIDA Federator webservice.
    """
    PROG = 'eida-federator'

    def build_parser(self, parents=[]):
        """
        Set up the commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """

        parser = CustomParser(
            prog=self.PROG,
            description='Launch EIDA federator web service.',
            parents=parents)

        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)
        parser.add_argument('-R', '--routing-url', type=str, metavar='URL',
                            default=settings.
                            EIDA_FEDERATOR_DEFAULT_ROUTING_URL,
                            dest='routing',
                            # TODO(damb): Perform integrity check.
                            help=("stationlite routing service url "
                                  "(including identifier) "
                                  "(default: %(default)s)"))
        parser.add_argument('-r', '--endpoint-resources', nargs='+',
                            type=str, metavar='ENDPOINT',
                            default=sorted(
                                settings.EIDA_FEDERATOR_DEFAULT_RESOURCES),
                            choices=sorted(
                                settings.EIDA_FEDERATOR_DEFAULT_RESOURCES),
                            help=('Whitespace-separated list of endpoint '
                                  'resources to be configured. '
                                  '(default: %(default)s) '
                                  '(choices: {%(choices)s})'))
        parser.add_argument('-t', '--endpoint-threads', type=thread_config,
                            metavar='DICT', dest='thread_config',
                            default=settings.EIDA_FEDERATOR_THREAD_CONFIG,
                            help=('Endpoint download thread configuration '
                                  'dictionary (JSON syntax). '
                                  '(default: %(default)s)'))
        parser.add_argument('--tmpdir', type=str, default='',
                            help='directory for temp files')
        parser.add_argument('--keep-tempfiles', dest='keep_tempfiles',
                            choices=sorted(
                                [str(c).replace('KeepTempfiles.', '').lower().
                                    replace('_', '-') for c in KeepTempfiles]),
                            default='none', type=str,
                            help=('Keep temporary files the service is '
                                  'generating. (default: %(default)s) '
                                  '(choices: {%(choices)s})'))

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

            try:
                from mod_wsgi import version  # noqa
                self.logger.info('Serving with mod_wsgi.')
            except Exception:
                pass

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
        Build the Flask app.

        :rtype :py:class:`flask.Flask`
        """

        if self.args.tmpdir:
            tempfile.tempdir = self.args.tmpdir

        api = Api()

        if 'fdsnws-station' in self.args.endpoint_resources:
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

        if 'fdsnws-dataselect' in self.args.endpoint_resources:
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

        if 'eidaws-wfcatalog' in self.args.endpoint_resources:
            api.add_resource(WFCatalogResource, "%s%s" %
                             (settings.EIDA_WFCATALOG_PATH,
                              settings.FDSN_QUERY_METHOD_TOKEN))

            # version method
            api.add_resource(WFCatalogVersionResource, "%s%s" %
                             (settings.EIDA_WFCATALOG_PATH,
                              settings.FDSN_VERSION_METHOD_TOKEN))

            # application.wadl method
            api.add_resource(WFCatalogWadlResource, "%s%s" %
                             (settings.EIDA_WFCATALOG_PATH,
                              settings.FDSN_WADL_METHOD_TOKEN))

        app_config = dict(
            # TODO(damb): Pass log_level to app.config!
            PROPAGATE_EXCEPTIONS=True,
            ROUTING_SERVICE=self.args.routing,
            FED_THREAD_CONFIG=self.args.thread_config,
            FED_KEEP_TEMPFILES=keeptempfile_config(self.args.keep_tempfiles),
            TMPDIR=tempfile.gettempdir())

        app = create_app(config_dict=app_config)
        api.init_app(app)
        return app


class FederatorWebserviceTest(FederatorWebserviceBase):
    """
    Test implementation of the EIDA Federator webservice.
    """
    PROG = 'eida-federator-test'

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
                            EIDA_FEDERATOR_DEFAULT_SERVER_PORT,
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


FederatorWebservice = FederatorWebserviceBase


# -----------------------------------------------------------------------------
def _main(app):
    """
    main function executor for EIDA Federator
    """
    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            config_section=settings.EIDA_FEDERATOR_CONFIG_SECTION)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(ExitCodes.EXIT_ERROR)

    return app.run()


def main_test():
    return _main(FederatorWebserviceTest(log_id='FED'))


def main_prod():
    return _main(FederatorWebservice(log_id='FED'))


main = main_prod


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main_test()
