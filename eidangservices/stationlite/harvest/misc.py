# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
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
EIDA NG stationlite utils.

Functions which might be used as 'executables':
    - db_init() -- create and initialize a SQLite DB
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import argparse
import logging # noqa
import os
import sys
import traceback

from sqlalchemy import create_engine

from eidangservices import settings, utils
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error, ExitCodes
from eidangservices.stationlite.engine import orm

__version__ = utils.get_version("stationlite")

# ----------------------------------------------------------------------------
def path_relative(path):
    """
    check if path is relative
    """
    if os.path.isabs(path):
        raise argparse.ArgumentTypeError
    return path

# path_relative ()

# ----------------------------------------------------------------------------
class StationLiteDBInitApp(App):
    """
    Implementation of an utility application to create and initialize an SQLite
    database for EIDA StationLite.
    """
    class DBAlreadyAvailable(Error):
        """The SQLite database file '{}' is already available."""

    def build_parser(self, parents=[]):
        """
        Configure a parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(
            prog="eida-stationlite-db-init",
            description='Create and initialize a DB for EIDA StationLite.',
            parents=parents)

        # optional arguments
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)
        parser.add_argument('-o', '--overwrite', action='store_true',
                            default=False,
                            help=('overwrite the SQLite DB file if already '
                                  'existent'))

        # positional arguments
        parser.add_argument('path_db', type=path_relative, metavar='PATH',
                            help='relative path to database (SQLite) file')

        return parser

    # build_parser ()

    def run(self):
        """
        Run application.
        """
        # XXX(damb): About logging configuration. Logging for EIDA StationLite
        # is enabled by fetching the logger 'eidangservices.stationlite'.

        # output work with
        # configure SQLAlchemy logging
        # log_level = self.logger.getEffectiveLevel()
        # logging.getLogger('sqlalchemy.engine').setLevel(log_level)
        exit_code = ExitCodes.EXIT_SUCCESS
        try:
            self.logger.info('{}: Version {}'.format(type(self).__name__,
                                                     __version__))
            if not self.args.overwrite and os.path.isfile(self.args.path_db):
                raise self.DBAlreadyAvailable(self.args.path_db)

            if os.path.isfile(self.args.path_db):
                os.remove(self.args.path_db)

            engine = create_engine('sqlite:///{}'.format(self.args.path_db))
            # create db tables
            self.logger.debug('Creating database tables ...')
            orm.ORMBase.metadata.create_all(engine)

            self.logger.info(
                "DB '{}' successfully initialized.".format(self.args.path_db))

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

# class StationLiteDBInitApp

# ----------------------------------------------------------------------------
def db_init():
    """
    main function for EIDA stationlite DB initializer
    """

    app = StationLiteDBInitApp(log_id='STL')

    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            positional_required_args=['path_db'],
            config_section=settings.EIDA_STATIONLITE_HARVEST_CONFIG_SECTION)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(ExitCodes.EXIT_ERROR)

    app.run()

# db_init ()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    db_init()

# ---- END OF <misc.py> ----
