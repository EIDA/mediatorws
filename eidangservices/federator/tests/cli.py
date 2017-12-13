# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <cli.py>
# -----------------------------------------------------------------------------
#
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
# REVISION AND CHANGES
# 2017/11/13        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Federator CLI tests.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import *

import os
import tempfile
import unittest

from eidangservices import settings
from eidangservices.utils import ExitCodes
from eidangservices.federator.server.app import build_parser

try:
    import mock
except ImportError:
    import unittest.mock as mock

# -----------------------------------------------------------------------------
class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def tearDown(self):
        self.parser = None

    def test_start_local(self):
        # test default argument
        args = self.parser.parse_args([])
        self.assertEqual(args.start_local, False)
        args = self.parser.parse_args(['--start-local'])
        self.assertEqual(args.start_local, True)

    # test_start_local ()

    def test_port(self):
        # test default argument
        args = self.parser.parse_args([])
        self.assertEqual(args.port, settings.EIDA_FEDERATOR_DEFAULT_SERVER_PORT)
        args = self.parser.parse_args(['-p', '5001'])
        self.assertEqual(args.port, 5001)
        args = self.parser.parse_args(['--port', '5001'])
        self.assertEqual(args.port, 5001)

    # test_port ()
    
    @mock.patch('sys.stderr', open(os.devnull, 'w'))
    def test_routing(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.routing, settings.DEFAULT_ROUTING_SERVICE)
        args = self.parser.parse_args(['-R', 'eth'])
        self.assertEqual(args.routing, 'eth')
        args = self.parser.parse_args(['--routing', 'eth'])
        self.assertEqual(args.routing, 'eth')
        with self.assertRaises(SystemExit) as cm:
            args = self.parser.parse_args(['--routing', 'hte'])
            # NOTE(damb): Supress output with
            # python -m unittest -b federator.tests.test_cli.CLITestCase
        self.assertEqual(cm.exception.code, ExitCodes.EXIT_ERROR)

    # test_routing ()

    def test_retries(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.retries, 
                settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRIES)
        args = self.parser.parse_args(['-r', '12'])
        self.assertEqual(args.retries, 12)
        args = self.parser.parse_args(['--retries', '12'])
        self.assertEqual(args.retries, 12)

    # test_retries ()
        
    def test_retry_wait(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.retry_wait, 
                settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_WAIT)
        args = self.parser.parse_args(['-w', '30'])
        self.assertEqual(args.retry_wait, 30)
        args = self.parser.parse_args(['--retry-wait', '30'])
        self.assertEqual(args.retry_wait, 30)

    # test_retry_wait ()

    def test_retry_lock(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.retry_lock, 
                settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_LOCK)
        args = self.parser.parse_args(['-L'])
        self.assertEqual(args.retry_lock, True)
        args = self.parser.parse_args(['--retry-lock'])
        self.assertEqual(args.retry_lock, True)

    # test_retry_lock ()

    def test_num_threads(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.threads,
                settings.EIDA_FEDERATOR_DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS)
        args = self.parser.parse_args(['-n', '2'])
        self.assertEqual(args.threads, 2)
        args = self.parser.parse_args(['--threads', '2'])
        self.assertEqual(args.threads, 2)
    
    # test_num_threads ()

    def test_tempdir(self):
        path_tempdir = tempfile.mkdtemp()

        args = self.parser.parse_args([])
        self.assertEqual(args.tmpdir, '')
        args = self.parser.parse_args(['--tmpdir', '/path/to/dir'])
        self.assertEqual(args.tmpdir, '/path/to/dir')
    
        os.rmdir(path_tempdir)

    # test_tempdir ()

    @mock.patch('sys.stderr', open(os.devnull, 'w'))
    @mock.patch('sys.stderr', open(os.devnull, 'w'))
    def test_logging_conf(self):
        fd, path_logging_conf = tempfile.mkstemp()

        args = self.parser.parse_args(['--logging-conf', path_logging_conf])
        self.assertEqual(args.path_logging_conf, path_logging_conf)
        # TODO
        with self.assertRaises(SystemExit) as cm:
            args = self.parser.parse_args(['--logging-conf', ''])
        self.assertEqual(cm.exception.code, ExitCodes.EXIT_ERROR)

        os.remove(path_logging_conf)

    # test_logging_conf

# class CLITestCase 

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <cli.py> ----
