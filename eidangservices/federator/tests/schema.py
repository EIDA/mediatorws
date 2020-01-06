# -*- coding: utf-8 -*-
"""
Field and schema related test facilities.
"""

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
            'nodata': '204', }

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

    def test_rect_and_circular(self):
        s = schema.StationSchema()
        test_data = {'minlatitude': 0., 'latitude': 45.}
        with self.assertRaises(ma.ValidationError):
            _ = s.load(test_data)


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
