# -*- coding: utf-8 -*-
"""
Federator CLI tests.
"""

import os
import tempfile
import unittest

from unittest import mock

from eidangservices import settings
from eidangservices.federator.server.app import FederatorWebservice


# -----------------------------------------------------------------------------
class CLITestCase(unittest.TestCase):

    def setUp(self):
        self.parser = FederatorWebservice().build_parser()

    def tearDown(self):
        self.parser = None

    @mock.patch('sys.stderr', open(os.devnull, 'w'))
    def test_routing(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.routing,
                         settings.EIDA_FEDERATOR_DEFAULT_ROUTING_URL)
        args = self.parser.parse_args(
            ['-R', 'http://eida.ethz.ch/eidaws/routing/1/'])
        self.assertEqual(args.routing, 'http://eida.ethz.ch/eidaws/routing/1/')
        args = self.parser.parse_args(
            ['--routing-url', 'http://eida.ethz.ch/eidaws/routing/1/'])
        self.assertEqual(args.routing, 'http://eida.ethz.ch/eidaws/routing/1/')

    def test_tempdir(self):
        path_tempdir = tempfile.mkdtemp()

        args = self.parser.parse_args([])
        self.assertEqual(args.tmpdir, '')
        args = self.parser.parse_args(['--tmpdir', '/path/to/dir'])
        self.assertEqual(args.tmpdir, '/path/to/dir')

        os.rmdir(path_tempdir)


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
