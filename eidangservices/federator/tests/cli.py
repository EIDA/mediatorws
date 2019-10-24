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

from builtins import * # noqa

import os
import tempfile
import unittest

from eidangservices import settings
from eidangservices.federator.server.app import FederatorWebservice

try:
    import mock
except ImportError:
    import unittest.mock as mock

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

    # test_routing ()

    def test_tempdir(self):
        path_tempdir = tempfile.mkdtemp()

        args = self.parser.parse_args([])
        self.assertEqual(args.tmpdir, '')
        args = self.parser.parse_args(['--tmpdir', '/path/to/dir'])
        self.assertEqual(args.tmpdir, '/path/to/dir')

        os.rmdir(path_tempdir)

    # test_tempdir ()

# class CLITestCase


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <cli.py> ----
