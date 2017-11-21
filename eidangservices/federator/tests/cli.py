# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <cli.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/11/13        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Federator CLI tests.
"""

import os
import tempfile
import unittest

from eidangservices import settings
from eidangservices.federator.server.__main__ import build_parser
from eidangservices.federator.server.misc import ExitCodes

class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def tearDown(self):
        self.parser = None

    def test_port(self):
        # test default argument
        args = self.parser.parse_args([])
        self.assertEqual(args.port, settings.EIDA_FEDERATOR_DEFAULT_SERVER_PORT)
        args = self.parser.parse_args(['-p', '5001'])
        self.assertEqual(args.port, 5001)
        args = self.parser.parse_args(['--port', '5001'])
        self.assertEqual(args.port, 5001)

    # test_port ()
    
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

    def test_logging_conf(self):
        fd, path_logging_conf = tempfile.mkstemp()

        args = self.parser.parse_args(['--logging-conf', path_logging_conf])
        self.assertEqual(args.path_logging_conf, path_logging_conf)
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
