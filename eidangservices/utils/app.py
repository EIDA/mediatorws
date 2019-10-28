# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <app.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices are free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices are distributed in the hope that it will be useful,
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
# REVISION AND CHANGES
# 2018/02/09        V0.1    Daniel Armbruster
# =============================================================================
"""
Provide facilities building general purpose CLI applications.
"""

import argparse
import configparser
import logging
import logging.config
import logging.handlers  # needed for handlers defined in logging.conf
import os
import sys

from collections import OrderedDict

from eidangservices import utils
from eidangservices.utils.error import ErrorWithTraceback, ExitCodes


# ------------------------------------------------------------------------------
class CustomParser(argparse.ArgumentParser):
    """
    Custom argument parser.
    """

    def error(self, message):
        """
        Display both an error and print the help.

        :param str message: Error message to be displayed
        """
        sys.stderr.write('USAGE ERROR: %s\n' % message)
        self.print_help()
        sys.exit(ExitCodes.EXIT_ERROR)

# class CustomParser

class AppError(ErrorWithTraceback):
    """Base application error"""

class LoggingConfOptionAlreadyAvailable(AppError):
    """CLI option '--logging-conf' already defined. ({})."""

class App:
    """
    Implementation of a configurable application.

    :param str log_id: Default identifier to be used when logging
    """

    def __init__(self, log_id='EIDAWS'):
        self.parser = None
        self.args = None
        self.log_id = log_id
        self.logger = None
        self.logger_configured = False

    # __init__ ()

    def configure(self, path_default_config, config_section=None,
                  positional_required_args=[], capture_warnings=True,
                  **kwargs):
        """
        Configure the application.

        :param str path_default_config: Path to the default configuration file
        :param str config_section: Name of the configuration section in the
            configuration file.
        :param list positional_required_args: List of :py:mod:`argparse`
            :code:`dest` values of positional required commandline arguments.
            If such a parameter was found in the configuration file it is
            **always** appended to the parameters parsed
        :param bool capture_warnings: Capture warnings
        :param interpolation: Interpolation behaviour. :code:`None` can be used
            to turn off interpolation completely. If enabled values are
            interpolated using environment variables, too.
        :type interpolation: None or :py:class:`configparser.Interpolation`
        :param kwargs: Additional keyword value parameters passed to the
            unterlying configuration file parser
        """
        c_parser = self._build_configfile_parser(path_default_config)
        args, remaining_argv = c_parser.parse_known_args()

        defaults = {}
        if path_default_config and config_section:
            config_parser = configparser.ConfigParser(**kwargs)
            config_parser.read(args.config_file)
            env_dict=None
            interpolation = kwargs.get('interpolation',
                                       configparser.BasicInterpolation())
            if (interpolation and
                    isinstance(interpolation,
                               configparser.BasicInterpolation)):
                # filter out variables containing a '%'; else interpolation
                # fails
                env_dict = {k: v for k, v in os.environ.items()
                            if v.find('%') == -1}
            try:
                defaults = dict(config_parser.items(
                    config_section, vars=env_dict))
            except Exception as err:
                import warnings
                warnings.warn(
                    "Exception while parsing config file: {}.".format(err))

        self.parser = self.build_parser(parents=[c_parser])
        # XXX(damb): Make sure that the default logger has an argument
        # path_logging_conf
        try:
            self.parser.add_argument('--logging-conf',
                                     dest='path_logging_conf',
                                     metavar='LOGGING_CONF',
                                     type=utils.real_file_path,
                                     help="path to a logging configuration "
                                     "file")
        except argparse.ArgumentError as err:
            raise LoggingConfOptionAlreadyAvailable(err)

        # fetch positional arguments from config file and keep them ordered
        positional_required = OrderedDict()
        for dest in positional_required_args:
            try:
                positional_required[dest] = defaults[dest]
                defaults.pop(dest)
            except KeyError:
                pass

        # set defaults taken from configuration file
        self.parser.set_defaults(**defaults)
        # set the config_file default explicitly since adding the c_parser as a
        # parent would change the args.config_file to
        # default=PATH_EIDANGWS_CONF within the child parser
        try:
            self.parser.set_defaults(config_file=args.config_file)
        except AttributeError:
            pass

        try:
            def _error(msg):
                sys.exit(ExitCodes.EXIT_ERROR)

            error_func = self.parser.error
            self.parser.error = _error
            self.args = self.parser.parse_args(remaining_argv)

        except SystemExit as err:
            # append positional required arguments if parsing at a first glance
            # failed
            if err.code == 0:
                # terminate normally (for e.g. [-h|--help])
                sys.exit(ExitCodes.EXIT_SUCCESS)

            for v in positional_required.values():
                remaining_argv.append(v)

            self.parser.error = error_func
            self.args = self.parser.parse_args(remaining_argv)

        self._setup_logger()
        if not self.logger_configured:
            self.logger = logging.getLogger()
            self.logger.addHandler(logging.NullHandler())

        logging.captureWarnings(capture_warnings)

        return self.args

    # configure ()

    def _build_configfile_parser(self, path_default_config):
        c_parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False)

        if path_default_config:
            c_parser.add_argument(
                "-c", "--config", dest="config_file",
                default=path_default_config,
                metavar="PATH",
                type=utils.realpath,
                help="path to EIDA Webservice configuration file " +
                     "(default: '%(default)s')")

        return c_parser

    # _build_configfile_parser ()

    def _setup_logger(self):
        """
        Initialize the logger of the application.

        In case the initialization was not successful a fallback logger (using
        :py:class:`logging.handlers.SyslogHandler`) is set up.
        """
        if self.args.path_logging_conf:
            try:
                logging.config.fileConfig(self.args.path_logging_conf)
                self.logger = logging.getLogger()
                self.logger_configured = True
                self.logger.info('Using logging configuration read from "%s"',
                                 self.args.path_logging_conf)
            except Exception as err:
                print('WARNING: Setup logging failed for "%s" with "%s".' %
                      (self.args.path_logging_conf, err), file=sys.stderr)
                self._setup_fallback_logger()
                self.logger.warning('Setup logging failed with %s. '
                                    'Using fallback logging configuration.' %
                                    err)
    # _setup_logger ()

    def _setup_fallback_logger(self):
        """Setup a fallback logger."""
        # NOTE(damb): Provide fallback syslog logger.
        self.logger = logging.getLogger()
        fallback_handler = logging.handlers.SysLogHandler('/dev/log',
                                                          'local0')
        fallback_handler.setLevel(logging.WARN)
        fallback_formatter = logging.Formatter(
            fmt=("<"+self.log_id+
                 "> %(asctime)s %(levelname)s %(name)s %(process)d "
                 "%(filename)s:%(lineno)d - %(message)s"),
            datefmt="%Y-%m-%dT%H:%M:%S%z")
        fallback_handler.setFormatter(fallback_formatter)
        self.logger.addHandler(fallback_handler)
        self.logger_configured = True

    # _setup_fallback_logger ()

    def build_parser(self, parents=[]):
        """
        Abstract method to configure a parser. This method must be implemented
        by clients.

        :param list parents: List of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        raise NotImplementedError

    # build_parser ()

    def run(self):
        """
        Abstract method to run application. The method must be implemented by
        clients.
        """
        raise NotImplementedError

    # run ()

# class App


# ---- END OF <app.py> ----
