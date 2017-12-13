# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <schema.py>
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
# 2017/11/16        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Field and schema related test facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import *

import unittest

import marshmallow as ma

from eidangservices.federator.server import schema


# -----------------------------------------------------------------------------
# schema related test cases

class StationSchemaTestCase(unittest.TestCase):

    def setUp(self):
        self.schema = schema.StationSchema()

    def tearDown(self):
        self.schema = None

    def test_geographic_opts(self):
        reference_result = {
                'service': 'station',
                'format': u'xml', 
                'level': u'station', 
                'minlatitude': 0.0, 
                'maxlatitude': 45.0,
                'includerestricted': True, 
                'matchtimeseries': False, 
                'nodata': 204,
                'includeavailability': False}
        test_datasets = [{'minlatitude': 0., 
                          'maxlatitude': 45.,
                          'nodata': 204}, 
                         {'minlat': 0.,
                          'maxlat': 45.,
                          'nodata': 204}]

        for dataset in test_datasets:
            result = self.schema.load(dataset).data
            self.assertEqual(result, reference_result)
        
    def test_rect_and_circular(self):
        test_data = {'minlatitude': 0., 'latitude': 45.}
        with self.assertRaises(ma.ValidationError):
            result = self.schema.load(test_data).data
            
# class StationSchemaTestCase 

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <schema.py> ----
