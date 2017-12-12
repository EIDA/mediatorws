# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <combiner.py>
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
# 2017/11/15        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Federator combiner test facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import *

import io
import json
import os
import unittest

from eidangservices.federator.server import combine

# -----------------------------------------------------------------------------
# constants
PATH_TESTDATA = os.path.join(os.path.dirname(__file__), "data")

# -----------------------------------------------------------------------------
class CombinerTestCase(unittest.TestCase):
    def test_combiner_factory(self):
        c = combine.Combiner.create('miniseed', qp={})
        # NOTE(damb): The solution with the temporary file is just a temporary
        # workaround.
        # XXX(damb): workaround: close the temporary file manually;
        c.tempfile_ofd.close()
        self.assertTrue(isinstance(c, combine.MseedCombiner))
        c = combine.Combiner.create('text', qp={})
        self.assertTrue(isinstance(c, combine.StationTextCombiner))
        c = combine.Combiner.create('xml', qp={})
        self.assertTrue(isinstance(c, combine.StationXMLCombiner))
        c = combine.Combiner.create('json', qp={})
        self.assertTrue(isinstance(c, combine.WFCatalogJSONCombiner))
        with self.assertRaises(KeyError):
            c = combine.Combiner.create('else', qp={})

# class CombinerTestCase


class StationTextCombinerTestCase(unittest.TestCase):
    HEADER_SNIPPED = \
    "#Network|Station|Latitude|Longitude|Elevation|SiteName|StartTime|EndTime"
    FIRST_SNIPPED = \
    "NL|HGN|50.764|5.9317|135.0|HEIMANSGROEVE, NETHERLANDS|2001-06-06T00:00:00|"
    SECOND_SNIPPED = \
    "II|BFO|48.3319|8.3311|589.0|Black Forest Observatory, Schiltach, Germany|1996-05-29T00:00:00|"

    def setUp(self):
        self.ofd = io.BytesIO()

    def tearDown(self):
        self.ofd.close()
        
    def test_single_snipped(self):
        c = combine.StationTextCombiner()
        snip = self.HEADER_SNIPPED+'\n'+self.FIRST_SNIPPED 
        ifd = io.StringIO(snip)
        c.combine(ifd)
        c.dump(self.ofd)
        self.assertEqual(snip, self.ofd.getvalue().decode("utf-8"))

    def test_combine(self):
        c = combine.StationTextCombiner()
        ifd = io.StringIO(self.HEADER_SNIPPED+'\n'+self.FIRST_SNIPPED+'\n')
        c.combine(ifd)
        ifd.close()
        ifd = io.StringIO(self.HEADER_SNIPPED+'\n'+self.SECOND_SNIPPED)
        c.combine(ifd)
        ifd.close()
        c.dump(self.ofd)
        self.assertEqual(self.HEADER_SNIPPED+'\n'
                +self.FIRST_SNIPPED+'\n'
                +self.SECOND_SNIPPED, 
                self.ofd.getvalue().decode("utf-8"))
         
# class StationTextCombinerTestCase


class WFCatalogJSONCombinerTestCase(unittest.TestCase):

    PATH_FIRST_SNIPPED = os.path.join(PATH_TESTDATA, 
            "ODC-WFCATALOG-2017-11-15T15_27_08.164Z.json")
    PATH_SECOND_SNIPPED = os.path.join(PATH_TESTDATA, 
            "ODC-WFCATALOG-2017-11-15T15_49_00.633Z.json")

    def setUp(self):
        self.ofd = io.BytesIO()

    def tearDown(self):
        self.ofd.close()
        
    def test_single_snipped(self):
        c = combine.WFCatalogJSONCombiner()
        snip = ''
        with open(self.PATH_FIRST_SNIPPED) as fd:
            snip = json.load(fd)
            fd.seek(0)
            c.combine(fd)
        c.dump(self.ofd)
        result = json.dumps(json.loads(self.ofd.getvalue().decode("utf-8")),
                            sort_keys=True)
        self.assertEqual(json.dumps(snip, sort_keys=True), result)

    def test_combine(self):
        c = combine.WFCatalogJSONCombiner()
        first_snip = ''
        with open(self.PATH_FIRST_SNIPPED) as fd_first:
            first_snip = json.load(fd_first)
            fd_first.seek(0)
            c.combine(fd_first)
        second_snip = ''
        with open(self.PATH_SECOND_SNIPPED) as fd_second:
            second_snip = json.load(fd_second)
            fd_second.seek(0)
            c.combine(fd_second)
        c.dump(self.ofd)
        result = json.dumps(json.loads(self.ofd.getvalue().decode("utf-8")),
                            sort_keys=True)

        reference_result = first_snip
        reference_result.extend(second_snip)
        reference_result = json.dumps(reference_result, sort_keys=True)
        self.assertEqual(reference_result, result)

# class WFCatalogJSONCombinerTestCase


class MseedCombinerTestCase(unittest.TestCase):
    # TODO(damb)
    pass

# class MseedCombinerTestCase 


class StationXMLCombinerTestCase(unittest.TestCase):
    # TODO(damb)
    pass

# class StationXMLCombinerTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <combiner.py> ----
