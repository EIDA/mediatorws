# -*- coding: utf-8 -*-
"""
Field and schema related test facilities.
"""

import unittest

from marshmallow import ValidationError

from eidangservices.stationlite.server import schema


# -----------------------------------------------------------------------------
class StationLiteSchemaTestCase(unittest.TestCase):

    def create_schema(self, *args, **kwargs):
        return schema.StationLiteSchema(*args, **kwargs)

    def test_geographic_opts(self):
        s = self.create_schema()
        reference_result = {
            'access': 'any',
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

    def test_proxy_netloc(self):
        s = self.create_schema()

        reference_result = {
            'access': 'any',
            'alternative': 'false',
            'service': 'dataselect',
            'format': 'post',
            'level': 'channel',
            'nodata': 204,
            'proxynetloc': 'www.example.com:8888',
            'minlatitude': -90.0,
            'maxlatitude': 90.0,
            'minlongitude': -180.0,
            'maxlongitude': 180.0,
        }

        self.assertEqual(
            s.load({'proxynetloc': '//www.example.com:8888'}),
            reference_result)

    def test_proxy_netloc_err(self):
        s = self.create_schema()

        with self.assertRaises(ValidationError):
            s.load({'proxynetloc': 'www.example.com:8888'})

    def test_proxy_netloc_missing(self):
        s = self.create_schema()

        reference_result = {
            'access': 'any',
            'alternative': 'false',
            'service': 'dataselect',
            'format': 'post',
            'level': 'channel',
            'nodata': 204,
            'proxynetloc': None,
            'minlatitude': -90.0,
            'maxlatitude': 90.0,
            'minlongitude': -180.0,
            'maxlongitude': 180.0,
        }

        self.assertEqual(s.load({}), reference_result)

    def test_proxy_netloc_none(self):
        s = self.create_schema()

        reference_result = {
            'access': 'any',
            'alternative': 'false',
            'service': 'dataselect',
            'format': 'post',
            'level': 'channel',
            'nodata': 204,
            'proxynetloc': None,
            'minlatitude': -90.0,
            'maxlatitude': 90.0,
            'minlongitude': -180.0,
            'maxlongitude': 180.0,
        }

        self.assertEqual(s.load({'proxynetloc': None}), reference_result)

    def test_access_dataselect(self):
        s = self.create_schema()

        self.assertEqual(s.load({'access': 'any'})['access'], 'any')
        self.assertEqual(s.load({'access': 'closed'})['access'], 'closed')
        self.assertEqual(s.load({'access': 'open'})['access'], 'open')

    def test_access_other(self):
        s = self.create_schema()

        self.assertEqual(
            s.load({'service': 'station', 'access': 'any'})['access'], 'any')
        with self.assertRaises(ValidationError):
            s.load({'service': 'station', 'access': 'closed'})
        with self.assertRaises(ValidationError):
            s.load({'service': 'station', 'access': 'open'})

        self.assertEqual(
            s.load({'service': 'wfcatalog', 'access': 'any'})['access'], 'any')
        with self.assertRaises(ValidationError):
            s.load({'service': 'wfcatalog', 'access': 'closed'})
        with self.assertRaises(ValidationError):
            s.load({'service': 'wfcatalog', 'access': 'open'})


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
