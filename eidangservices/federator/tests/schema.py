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

from builtins import * # noqa

import unittest

import marshmallow as ma

from eidangservices.federator.server import schema


# -----------------------------------------------------------------------------
# schema related test cases

class StationSchemaTestCase(unittest.TestCase):

    def test_geographic_opts(self):
        self.maxDiff = None
        s = schema.StationSchema()
        reference_result = {
            'service': 'station',
            'format': 'xml',
            'level': 'station',
            'minlatitude': '0.0',
            'maxlatitude': '45.0',
            'includerestricted': 'true',
            'matchtimeseries': 'false',
            'nodata': '204',
            'includeavailability': 'false'}

        test_datasets = [{'minlatitude': 0.,
                          'maxlatitude': 45.,
                          'nodata': 204},
                         {'minlat': 0.,
                          'maxlat': 45.,
                          'nodata': 204}]

        result = s.dump(s.load(test_datasets[0]))
        self.assertEqual(result, reference_result)
        result = s.dump(s.load(test_datasets[1]))
        self.assertEqual(result, reference_result)

    # test_geographic_opts ()

    def test_rect_and_circular(self):
        s = schema.StationSchema()
        test_data = {'minlatitude': 0., 'latitude': 45.}
        with self.assertRaises(ma.ValidationError):
            result = s.load(test_data)

# class StationSchemaTestCase


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <schema.py> ----
