# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <combiner.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/11/15        V0.1    Daniel Armbruster
#
# =============================================================================

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
    u"#Network|Station|Latitude|Longitude|Elevation|SiteName|StartTime|EndTime"
    FIRST_SNIPPED = \
    u"NL|HGN|50.764|5.9317|135.0|HEIMANSGROEVE, NETHERLANDS|2001-06-06T00:00:00|"
    SECOND_SNIPPED = \
    u"II|BFO|48.3319|8.3311|589.0|Black Forest Observatory, Schiltach, Germany|1996-05-29T00:00:00|"

    def setUp(self):
        self.ofd = io.StringIO()

    def tearDown(self):
        self.ofd.close()
        
    def test_single_snipped(self):
        c = combine.StationTextCombiner()
        snip = self.HEADER_SNIPPED+'\n'+self.FIRST_SNIPPED 
        ifd = io.StringIO(snip)
        c.combine(ifd)
        c.dump(self.ofd)
        self.assertEqual(snip, self.ofd.getvalue())

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
                self.ofd.getvalue())
         
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
        result = json.dumps(json.loads(self.ofd.getvalue()), sort_keys=True)
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
        result = json.dumps(json.loads(self.ofd.getvalue()), sort_keys=True)

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
