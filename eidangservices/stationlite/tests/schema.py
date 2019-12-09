# -*- coding: utf-8 -*-
"""
Field and schema related test facilities.
"""

import unittest

from eidangservices.stationlite.server import schema


# -----------------------------------------------------------------------------
class StationLiteSchemaTestCase(unittest.TestCase):

    def test_geographic_opts(self):
        self.maxDiff = None
        s = schema.StationLiteSchema()
        reference_result = {
            'alternative': 'false',
            'service': 'dataselect',
            'format': 'post',
            'level': 'channel',
            'minlatitude': '0.0',
            'maxlatitude': '45.0',
            'minlongitude': '-180.0',
            'maxlongitude': '180.0',
            'proxynetloc': 'None',
            'nodata': '204',
        }

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


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
