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
#
# REVISION AND CHANGES
# 2017/12/13        V0.1    Daniel Armbruster
# =============================================================================
"""
Field and schema related test facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import datetime
import unittest

import flask # noqa
import marshmallow as ma

from eidangservices.utils import schema, sncl
from eidangservices.settings import FDSNWS_QUERY_LIST_SEPARATOR_CHAR

try:
    import mock
except ImportError:
    import unittest.mock as mock


SEP = FDSNWS_QUERY_LIST_SEPARATOR_CHAR

# -----------------------------------------------------------------------------
# field related test cases

class FieldTestCase(unittest.TestCase): # noqa
    """
    Base class for all field test cases.
    """

    class TestSchema:
        pass

    def setUp(self):
        self.schema = self.TestSchema()

    def tearDown(self):
        self.schema = None

    def _valid(self, data, reference_result, method=None):
        if not method:
            method = self.schema.load
        for v in data:
            result = method(v)
            self.assertEqual(reference_result, result)

    def _invalid(self, data, method=None):
        if not method:
            method = self.schema.load
        for v in data:
            with self.assertRaises(ma.ValidationError):
                method(v)

# class FieldTestCase


class PercentageFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.Percentage()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {u'f': 20.0}
        valid = [dict(f=20), dict(f=20.)]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=-1), dict(f=105), dict(f="foo")]
        self._invalid(invalid)

# class PercentageFieldTestCase


class NotEmptyStringFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.NotEmptyString()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': 'foo'}
        data = [dict(f='foo')]
        self._valid(data, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=1), dict(f='')]
        self._invalid(invalid)

# class NotEmptyStringFieldTestCase


class NotEmptyIntFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.NotEmptyInt()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': 123}
        valid = [dict(f=123), dict(f=123.), dict(f='123')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f='foo'), dict(f='')]
        self._invalid(invalid)

# class NotEmptyIntFieldTestCase


class NotEmptyFloatFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.NotEmptyFloat()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': 123.}
        valid = [dict(f=123), dict(f=123.), dict(f='123')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f='foo'), dict(f='')]
        self._invalid(invalid)

# class NotEmptyFloatFieldTestCase


class LatitudeFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.Latitude()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': -45.}
        valid = [dict(f=-45), dict(f=-45.), dict(f='-45')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=-100), dict(f=100), dict(f=''), dict(f='foo')]
        self._invalid(invalid)

# class LatitudeFieldTestCase


class LongitudeFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.Longitude()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': -45.}
        valid = [dict(f=-45), dict(f=-45.), dict(f='-45')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=-200), dict(f=200), dict(f=''), dict(f='foo')]
        self._invalid(invalid)

# class LongitudeFieldTestCase


class RadiusFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.Longitude()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': 90.}
        valid = [dict(f=90), dict(f=90.), dict(f='90')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=-200), dict(f=200), dict(f=''), dict(f='foo')]
        self._invalid(invalid)

# class RadiusFieldTestCase


class FDSNWSBoolFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.FDSNWSBool()

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': True}
        valid = [dict(f='true'), dict(f=True), dict(f=1)]
        self._valid(valid, reference_result)
        reference_result = {'f': False}
        valid = [dict(f='false'), dict(f=False), dict(f=0)]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f='True'), dict(f='yes'),
                   dict(f='False'), dict(f='no'), dict(f='')]
        self._invalid(invalid)

# class FDSNWSBoolFieldTestCase


class FDSNWSDateTimeFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.FDSNWSDateTime(format='fdsnws')

        class Meta:
            strict = True

    def test_field_valid(self):
        reference_result = {'f': datetime.datetime(2017, 1, 1)}
        valid = [dict(f='2017-01-01'),
                 dict(f='2017-01-01T00:00:00'),
                 dict(f='2017-01-01T00:00:00.000'),
                 dict(f='2017-01-01T00:00:00.000000')]
        self._valid(valid, reference_result)

        reference_result = {'f': datetime.datetime(
            2017, 1, 1, 1, 1, 1, 123000)}
        valid = [dict(f='2017-01-01T01:01:01.123')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=123),
                   dict(f='foo'),
                   dict(f='2017-01'),
                   dict(f='2017-01-01T01:01:01.123456+00:01')]
        self._invalid(invalid)

# class FDSNWSDateTimeFieldTestCase


# -----------------------------------------------------------------------------
class StreamEpochSchemaTestCase(unittest.TestCase):

    def _load(self, s, dataset):
        return s.load(dataset)

    def _dump(self, s, dataset):
        return dict(s.dump(dataset))

    @mock.patch('flask.Request')
    def test_sncl_get(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # no time definitions
        reference_result = {
            'network': 'CH?*',
            'station': 'DAVOX?*',
            'location': '*?ABC',
            'channel': 'AZ?*'}
        test_dataset = {'network': 'CH?*', 'sta': 'DAVOX?*', 'loc': '*?ABC',
                        'cha': 'AZ?*'}
        test_dataset = self._load(s, test_dataset)
        result = self._dump(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_get_invalid_net(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        test_dataset = {'net': 'C-', 'sta': 'DAVO?'}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_invalid_sta(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        test_dataset = {'net': '?*', 'sta': 'DAVO,', 'loc': '--'}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_invalid_cha(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'cha': 'BH,'}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_valid_loc_minus(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define multiple channels
        reference_result = {
            'network': '*',
            'station': '*',
            'location': '--',
            'channel': '*'}
        test_dataset = {'loc': '--'}
        test_dataset = self._load(s, test_dataset)
        result = self._dump(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_get_valid_loc_space(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define multiple channels
        reference_result = {
            'network': '*',
            'station': '*',
            'location': '  ',
            'channel': '*'}
        test_dataset = {'loc': '  '}
        test_dataset = self._load(s, test_dataset)
        result = self._dump(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_get_start(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # only starttime definition
        reference_result = {
            'network': 'CH',
            'station': 'DAVOX',
            'location': '*',
            'channel': '*',
            'starttime': '2017-01-01T00:00:00'}

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'start': '2017-01-01'}
        test_dataset = self._load(s, test_dataset)
        result = self._dump(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_get_end(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # only endtime definition
        reference_result = {
            'network': 'CH',
            'station': 'DAVOX',
            'location': '*',
            'channel': '*',
            'endtime': '2017-01-01T00:00:00'}

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'end': '2017-01-01'}
        test_dataset = self._load(s, test_dataset)
        result = self._dump(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_get_start_end(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define both starttime and endtime
        reference_result = {
            'network': 'CH',
            'station': 'DAVOX',
            'location': '*',
            'channel': '*',
            'starttime': '2017-01-01T00:00:00',
            'endtime': '2017-02-01T00:00:00'}

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'start': '2017-01-01',
                        'end': '2017-02-01'}
        test_dataset = self._load(s, test_dataset)
        result = self._dump(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_get_starts(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define multiple times
        test_dataset = {'net': 'CH', 'sta': 'DAVOX',
                        'start': '2017-01-01,2017-01-02',
                        'end': '2017-02-01'}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_start_future(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define starttime in future
        future = datetime.datetime.now() + datetime.timedelta(1)
        future = future.isoformat()
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'start': future}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_start_future_wfcatalog(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request,
                                              'service': 'eidaws-wfcatalog'})

        # define starttime in future
        future = datetime.datetime.now() + datetime.timedelta(1)
        future = future.isoformat()
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'start': future}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_end_future(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define endtime in future
        now = datetime.datetime.utcnow()
        tomorrow = now + datetime.timedelta(1)
        tomorrow_str = tomorrow.isoformat()

        test_dataset = {'net': 'CH', 'sta': 'DAVOX',
                        'start': now.isoformat(),
                        'end': tomorrow_str}
        result = self._load(s, test_dataset)
        self.assertEqual(result.endtime, None)

    @mock.patch('flask.Request')
    def test_sncl_get_end_future_wfcatalog(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request,
                                              'service': 'eidaws-wfcatalog'})

        # define endtime in future
        now = datetime.datetime.utcnow()
        tomorrow = now + datetime.timedelta(1)
        tomorrow_str = tomorrow.isoformat()

        test_dataset = {'net': 'CH', 'sta': 'DAVOX',
                        'start': now.isoformat(),
                        'end': tomorrow_str}
        result = self._load(s, test_dataset)
        self.assertEqual(result.endtime, tomorrow)

    @mock.patch('flask.Request')
    def test_sncl_get_end_lt_start(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define endtime <= starttime
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'end': '2017-01-01',
                        'start': '2017-02-01'}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_get_end_lt_start_wfcatalog(self, mock_request):
        # request.method == 'GET'
        mock_request.method = 'GET'
        s = schema.StreamEpochSchema(context={'request': mock_request,
                                              'service': 'eidaws-wfcatalog'})

        # define endtime <= starttime
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'end': '2017-01-01',
                        'start': '2017-02-01'}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_post(self, mock_request):
        # request.method == 'POST'
        mock_request.method = 'POST'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # valid values - single SNCL line
        reference_result = sncl.StreamEpoch(
            stream=sncl.Stream(network='CH', station='DAVOX'),
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 2))

        test_dataset = {
            'net': 'CH',
            'sta': 'DAVOX',
            'loc': '*',
            'cha': '*',
            'start': '2017-01-01',
            'end': '2017-01-02'}
        result = self._load(s, test_dataset)
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_sncl_post_missing_time(self, mock_request):
        # request.method == 'POST
        mock_request.method = 'POST'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # define a invalid SNCL
        test_dataset = {
            'net': 'CH',
            'sta': 'DAVOX',
            'loc': '*',
            'cha': '*',
            'start': '2017-01-01'}
        with self.assertRaises(ma.ValidationError):
            self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_post_start_lt_end(self, mock_request):
        # request.method == 'POST'
        mock_request.method = 'POST'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # invalid time definition
        test_dataset = {
            'net': 'CH',
            'sta': 'DAVOX',
            'loc': '*',
            'cha': '*',
            'start': '2017-01-02',
            'end': '2017-01-01'}
        with self.assertRaises(ma.ValidationError):
            self._load(s, test_dataset)

    @mock.patch('flask.Request')
    def test_sncl_post_start_end_future(self, mock_request):
        # request.method == 'POST'
        mock_request.method = 'POST'
        s = schema.StreamEpochSchema(context={'request': mock_request})

        # both starttime and endtime in future
        today = datetime.datetime.now()
        tomorrow = today + datetime.timedelta(1)
        tomorrow_str = tomorrow.isoformat()
        dat = today + datetime.timedelta(2)
        dat_str = dat.isoformat()

        test_dataset = {'net': 'CH',
                        'sta': 'DAVOX',
                        'loc': '*',
                        'cha': '*',
                        'start': tomorrow_str,
                        'end': dat_str}
        with self.assertRaises(ma.ValidationError):
            self._load(s, test_dataset)

# class StreamEpochSchemaTestCase


class ManyStreamEpochSchemaTestCase(unittest.TestCase):

    @mock.patch('flask.Request')
    def test_many_sncls(self, mock_request):
        # request.method == 'POST'
        mock_request.method = 'POST'
        s = schema.ManyStreamEpochSchema(context={'request': mock_request})

        reference_result = [sncl.StreamEpoch(
            stream=sncl.Stream(network='CH', station='DAVOX'),
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 31)),
            sncl.StreamEpoch(
                stream=sncl.Stream(network='GR',
                                   station='BFO',
                                   channel='BH?'),
                starttime=datetime.datetime(2017, 1, 1),
                endtime=datetime.datetime(2017, 1, 31))]
        test_dataset = {'stream_epochs': [
                        {'net': 'CH', 'sta': 'DAVOX',
                         'start': '2017-01-01', 'end': '2017-01-31'},
                        {'net': 'GR', 'sta': 'BFO', 'cha': 'BH?',
                         'start': '2017-01-01', 'end': '2017-01-31'}
                        ]}
        result = s.load(test_dataset)['stream_epochs']
        self.assertEqual(result, reference_result)

    @mock.patch('flask.Request')
    def test_post_missing_sncl(self, mock_request):
        # request.method == 'POST'
        mock_request.method = 'POST'
        s = schema.ManyStreamEpochSchema(context={'request': mock_request})

        test_dataset = []
        with self.assertRaises(ma.ValidationError):
            s.load(test_dataset)

# class ManyStreamEpochSchemaTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__': # noqa
    unittest.main()

# ---- END OF <schema.py> ----
