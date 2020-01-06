#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch EIDA NG Federator.
"""

import argparse
import collections
import copy
import inspect
import json
import os
import sys
import tempfile
import traceback

from urllib.parse import urlsplit

from flask_restful import Api

from eidangservices import settings
from eidangservices.federator import __version__
from eidangservices.federator.server import create_app
from eidangservices.federator.server.cache import Cache
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


def resource_config(config_dict):
    """
    Parse a federator resource configuration dictionary.

    :param str config_dict: Serialized (JSON) configuration dictionary
    :retval: Interpolated resource configuration dictionary
    :rtype: dict
    """

    def dict_merge(d1, d2, strict=True):
        """
        Recursively merge dictionaries. Performes an in-place merge of
        `d2` into `d1`.

        :param bool strict: Merge keys from `d2` only if available in `d1`.
            Besides attribute validation is performed. Else an
            :py:class:`~argparse.ArgumentTypeError` is raised.
        """

        for k, v in d2.items():
            if (isinstance(d1.get(k), dict) and
                    isinstance(v, collections.Mapping)):
                dict_merge(d1[k], d2[k], strict=strict)
            elif strict and k not in d1:
                raise argparse.ArgumentTypeError(
                    'Invalid resource config key: {!r}.'.format(k))
            else:
                d1[k] = d2[k]

            if (strict and k == 'request_strategy' and
                    v not in settings.EIDA_FEDERATOR_REQUEST_STRATEGIES):
                raise argparse.ArgumentTypeError(
                    'Invalid request strategy: {!r}'.format(v))

            if (strict and k == 'request_method' and
                    v not in settings.EIDA_FEDERATOR_REQUEST_METHODS):
                raise argparse.ArgumentTypeError(
                    'Invalid request method: {!r}'.format(v))

            if (strict and k == 'proxy_netloc'):
                # validate proxy_netloc
                if v is None:
                    continue

                try:
                    r = urlsplit(v)
                    if (not r.netloc or r.scheme or r.path or r.query or
                            r.fragment):
                        raise ValueError(
                            'Invalid network location. (Format: '
                            '//[user[:password]@]host[:port])')
                except Exception as err:
                    raise argparse.ArgumentTypeError(str(err))
                else:
                    v = '//' + r.netloc

    try:
        config_dict = json.loads(config_dict)
    except Exception:
        raise argparse.ArgumentTypeError(
            'Invalid resource configuration dictionary syntax.')

    retval = copy.deepcopy(settings.EIDA_FEDERATOR_RESOURCE_CONFIG)
    dict_merge(retval, config_dict)
    return retval


def cache_config(arg):
    try:
        config_dict = json.loads(arg)
    except Exception as err:
        raise argparse.ArgumentTypeError(
            'Invalid cache configuration dictionary syntax ({}).'.format(err))

    allowed_keys = set(settings.EIDA_FEDERATOR_CACHE_CONFIG)
    difference = set(config_dict) - allowed_keys

    if difference:
        return argparse.ArgumentTypeError('Invalid key: {!r}'.format())

    try:
        cache_type = config_dict['CACHE_TYPE']
    except KeyError:
        raise argparse.ArgumentTypeError('Missing cache type.')
    else:
        if cache_type not in Cache.CACHE_MAP:
            raise argparse.ArgumentTypeError(
                'Invalid cache type: {!r}'.format(cache_type))

    config_dict.setdefault('CACHE_KWARGS', {})
    allowed_args = set(inspect.getfullargspec(
        Cache.CACHE_MAP[cache_type]).args[1:])
    difference = set(config_dict['CACHE_KWARGS']) - allowed_args

    if difference:
        raise argparse.ArgumentTypeError(
            'Invalid cache configuration parameter: {!r}; '
            'Valid args for CACHE_TYPE={!r}: {!r}'.format(
                difference, cache_type, allowed_args))

    return config_dict


def keeptempfile_config(arg):
    """
    Populate the corresponding :code:`enum` value from the CLI configuration.
    """
    return getattr(KeepTempfiles, arg.upper().replace('-', '_'))


def _pos_number(arg, vtype):
    try:
        arg = vtype(arg)
    except ValueError as err:
        raise argparse.ArgumentTypeError(err)

    if arg <= 0:
        raise argparse.ArgumentTypeError(
            'Only positive numbers allowed.')
    return arg


def pos_int(arg):
    return _pos_number(arg, int)


def pos_float(arg):
    return _pos_number(arg, float)


def percent(arg):
    try:
        arg = float(arg)
    except ValueError as err:
        raise argparse.ArgumentTypeError(err)

    if arg < 0 or arg > 100:
        raise argparse.ArgumentTypeError('Invalid percentage.')
    return arg


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
        parser.add_argument('-S', '--storage-url', type=str,
                            dest='storage', metavar='URL',
                            default=settings.
                            EIDA_FEDERATOR_DEFAULT_STORAGE_URL,
                            help="Storage URL (Redis) (default: %(default)s)")
        parser.add_argument('-w', '--cretry-budget-window-size', type=pos_int,
                            dest='cretry_budget_window_size', metavar='SIZE',
                            default=settings.
                            EIDA_FEDERATOR_DEFAULT_RETRY_BUDGET_CLIENT_WSIZE,
                            help=('Rolling window size for the per client '
                                  'retry-budget related response code time '
                                  'series. (default: %(default)s)'))
        parser.add_argument('-t', '--cretry-budget-ttl', type=pos_float,
                            dest='cretry_budget_ttl', metavar='TTL',
                            default=settings.
                            EIDA_FEDERATOR_DEFAULT_RETRY_BUDGET_CLIENT_TTL,
                            help=('TTL in seconds for response codes with '
                                  'respect to the per client retry-budget '
                                  'ralated response code time series. The '
                                  'value defines when request should be '
                                  'forwarded to endpoints, again. '
                                  '(default: %(default)s)'))
        parser.add_argument('-e', '--cretry-budget-error-ratio',
                            type=percent, dest='cretry_budget_eratio',
                            metavar='PERCENT',
                            default=settings.
                            EIDA_FEDERATOR_DEFAULT_RETRY_BUDGET_CLIENT,
                            help=('Per client retry-budget error ratio in '
                                  'percent. Defines the error ratio above '
                                  'requests to datacenters (DC) are dropped. '
                                  '(default: %(default)s)'))
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
        parser.add_argument('--resource-config', type=resource_config,
                            metavar='DICT', dest='resource_config',
                            default=settings.EIDA_FEDERATOR_RESOURCE_CONFIG,
                            help=('Resource configuration dictionary '
                                  '(JSON syntax). Note, that bulk request '
                                  'strategies force the request method to '
                                  '"POST". (default: %(default)s)'))
        parser.add_argument('--tmpdir', type=str, default='',
                            help='directory for temp files')
        parser.add_argument('--cache-config', type=cache_config,
                            dest='cache_config', metavar='DICT',
                            default=settings.EIDA_FEDERATOR_CACHE_CONFIG,
                            help=('Cache configuration dictionary '
                                  '(JSON syntax) (default: %(default)s'))
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
            REDIS_URL=self.args.storage,
            FED_RESOURCE_CONFIG=self.args.resource_config,
            FED_KEEP_TEMPFILES=keeptempfile_config(self.args.keep_tempfiles),
            FED_CRETRY_BUDGET_WINDOW_SIZE=self.args.cretry_budget_window_size,
            FED_CRETRY_BUDGET_TTL=self.args.cretry_budget_ttl,
            FED_CRETRY_BUDGET_ERATIO=self.args.cretry_budget_eratio,
            TMPDIR=tempfile.gettempdir())

        if self.args.cache_config:
            app_config.update(self.args.cache_config)

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
