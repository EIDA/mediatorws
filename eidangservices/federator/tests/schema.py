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

import datetime
import marshmallow as ma
import unittest

from eidangservices.federator.tests.helpers import GETRequest, POSTRequest

from eidangservices.settings import FDSNWS_QUERY_LIST_SEPARATOR_CHAR
from eidangservices.federator.server import schema


SEP = FDSNWS_QUERY_LIST_SEPARATOR_CHAR 

# -----------------------------------------------------------------------------
# field related test cases

class FieldTestCase(unittest.TestCase):
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
            self.assertEqual(reference_result, result.data)

    def _invalid(self, data, method=None):
        if not method:
            method = self.schema.load
        for v in data:
            with self.assertRaises(ma.ValidationError):
                result = method(v)

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
        reference_result = {u'f': 'foo'}
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
        reference_result = {u'f': 123}
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
        reference_result = {u'f': 123.}
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
        reference_result = {u'f': -45.}
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
        reference_result = {u'f': -45.}
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
        reference_result = {u'f': 90.}
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
        reference_result = {u'f': True}
        valid = [dict(f='true'), dict(f=True), dict(f=1)]
        self._valid(valid, reference_result)
        reference_result = {u'f': False}
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
        valid=[dict(f='2017-01-01'), 
                dict(f='2017-01-01T00:00:00'), 
                dict(f='2017-01-01T00:00:00.000'), 
                dict(f='2017-01-01T00:00:00.000000')]
        self._valid(valid, reference_result)

        reference_result = {'f': datetime.datetime(2017, 1, 1, 1, 1, 1, 123000)}
        valid=[dict(f='2017-01-01T01:01:01.123')]
        self._valid(valid, reference_result)

    def test_field_invalid(self):
        invalid = [dict(f=123), 
                dict(f='foo'), 
                dict(f='2017-01'), 
                dict(f='2017-01-01T01:01:01.123456+00:01')]
        self._invalid(invalid)

# class FDSNWSDateTimeFieldTestCase


class RequestListFieldTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.RequestList(ma.fields.Str())

        class Meta:
            strict = True

    def test_one_el_serialize(self):
        self.schema.context['request'] = GETRequest
        # test single element
        reference_result = {'f': 'foo'}
        valid = dict(f=['foo'])
        self.assertEqual(reference_result, dict(self.schema.dump(valid).data))

    def test_multi_el_serialize(self):
        reference_result = {'f': ['foo', 'bar']}
        valid = dict(f=['foo', 'bar'])
        self.assertEqual(reference_result, dict(self.schema.dump(valid).data))

# class RequestListFieldTestCase


class DelimitedRequestListTestCase(FieldTestCase):

    class TestSchema(ma.Schema):
        f = schema.DelimitedRequestList(ma.fields.Str())

        class Meta:
            strict = True

    def test_one_el_serialize(self):
        self.schema.context['request'] = GETRequest
        # test single element
        reference_result = {'f': 'foo'}
        valid = dict(f=['foo'])
        self.assertEqual(reference_result, dict(self.schema.dump(valid).data))

    def test_multi_el_serialize(self):
        self.schema.context['request'] = GETRequest
        reference_result = {'f': 'foo'+SEP+'bar'}
        valid = dict(f=['foo', 'bar'])
        self.assertEqual(reference_result, dict(self.schema.dump(valid).data))

# class DelimitedRequestListTestCase

# -----------------------------------------------------------------------------
# schema related test cases

class SNCLSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.schema = schema.SNCLSchema()

    def tearDown(self):
        self.schema = None

    def _load(self, dataset):
        return dict(self.schema.load(dataset).data) 

    def _dump(self, dataset):
        return dict(self.schema.dump(dataset).data)

    def test_sncl_get(self):
        # request.method == 'GET'
        self.schema.context['request'] = GETRequest
        # no delimited list definitions + no time definitions
        reference_result = {
                'network': 'CH', 
                'station': 'DAVOX',
                'location': '*',
                'channel': '*'}
        test_dataset = {'net': 'CH', 'sta': 'DAVOX'}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)

        # define multiple networks
        reference_result = {
                'network': 'CH,II', 
                'station': 'DAVOX',
                'location': '*',
                'channel': '*'}
        test_dataset = {'net': 'CH,II', 'sta': 'DAVOX'}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)
       
        # define multiple stations
        reference_result = {
                'network': 'CH', 
                'station': 'DAVOX,BALST',
                'location': '*',
                'channel': '*'}
        test_dataset = {'net': 'CH', 'sta': 'DAVOX,BALST'}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)

        # define multiple channels
        reference_result = {
                'network': 'CH', 
                'station': 'DAVOX',
                'location': '*',
                'channel': 'BH?,LHZ'}
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'channel': 'BH?,LHZ'}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)


        # only starttime definition
        reference_result = {
                'network': 'CH', 
                'station': 'DAVOX',
                'location': '*',
                'channel': '*',
                'starttime': '2017-01-01T00:00:00'}

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'start': ['2017-01-01']}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)

        # only endtime definition
        reference_result = {
                'network': 'CH', 
                'station': 'DAVOX',
                'location': '*',
                'channel': '*',
                'endtime': '2017-01-01T00:00:00'}

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'end': ['2017-01-01']}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)

        # define both starttime and endtime
        reference_result = {
                'network': 'CH', 
                'station': 'DAVOX',
                'location': '*',
                'channel': '*',
                'starttime': '2017-01-01T00:00:00',
                'endtime': '2017-02-01T00:00:00'}

        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'start': ['2017-01-01'], 
                'end': ['2017-02-01']}
        test_dataset = self._load(test_dataset)
        result = self._dump(test_dataset)
        self.assertEqual(result, reference_result)

        # define multiple times
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 
                'start': ['2017-01-01', '2017-01-02'], 
                'end': ['2017-02-01']}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(test_dataset)

        # define starttime in future
        future = datetime.datetime.now() + datetime.timedelta(1)
        future = future.isoformat()
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 
                'start': [future]}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(test_dataset)

        # define endtime in future
        now = datetime.datetime.utcnow() 
        tomorrow = now + datetime.timedelta(1)
        tomorrow_str = tomorrow.isoformat()


        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 
                'end': [tomorrow_str]}
        result = self._load(test_dataset)
        self.assertAlmostEqual(result['endtime'][0], now,
                delta=datetime.timedelta(seconds=1))

        # define endtime <= starttime
        test_dataset = {'net': 'CH', 'sta': 'DAVOX', 'end': ['2017-01-01'], 
                'start': ['2017-02-01']}
        with self.assertRaises(ma.ValidationError):
            test_dataset = self._load(test_dataset)


    def test_sncl_post(self):
        # request.method == 'POST'
        self.schema.context['request'] = POSTRequest
        
        # valid values - single SNCL line
        reference_result = {
                'network': ['CH'], 
                'station': ['DAVOX'],
                'location': ['*'],
                'channel': ['*'],
                'starttime': [datetime.datetime(2017,01,01)],
                'endtime': [datetime.datetime(2017,01,02)]}
        
        test_dataset = {
                'net': 'CH', 
                'sta': 'DAVOX',
                'loc': '*',
                'cha': '*',
                'start': ['2017-01-01'],
                'end': ['2017-01-02']}
        result = self._load(test_dataset)
        self.assertEqual(result, reference_result)

        # define a invalid SNCL
        test_dataset = {
                'net': 'CH,II', 
                'sta': 'DAVOX,BFO',
                'loc': '*,*',
                'cha': '*,*',
                'start': ['2017-01-01', '2017-01-01'],
                'end': ['2017-01-02']}
        with self.assertRaises(ma.ValidationError):
            result = self._load(test_dataset)

        # missing time definition
        test_dataset = {
                'net': 'CH', 
                'sta': 'DAVOX',
                'loc': '*',
                'cha': '*',
                'start': [],
                'end': []}
        with self.assertRaises(ma.ValidationError):
            self._load(test_dataset)

        # invalid time definition
        test_dataset = {
                'net': 'CH', 
                'sta': 'DAVOX',
                'loc': '*',
                'cha': '*',
                'start': [None],
                'end': ['2017-01-01']}
        with self.assertRaises(ma.ValidationError):
            self._load(test_dataset)

        # both starttime and endtime in future (not caught)
        today = datetime.datetime.now()
        tomorrow = today + datetime.timedelta(1)
        tomorrow_str = tomorrow.isoformat()
        dat = today + datetime.timedelta(2)
        dat_str = dat.isoformat()
        reference_result = {
                'network': ['CH'], 
                'station': ['DAVOX'],
                'location': ['*'],
                'channel': ['*'],
                'starttime': [tomorrow],
                'endtime': [dat]}
        test_dataset = {
                'net': 'CH', 
                'sta': 'DAVOX',
                'loc': '*',
                'cha': '*',
                'start': [tomorrow_str],
                'end': [dat_str]}
        result = self._load(test_dataset)
        self.assertEqual(result, reference_result)

# class SNCLSchemaTestCase


class StationSchemaTestCase(unittest.TestCase):

    def setUp(self):
        self.schema = schema.StationSchema()

    def tearDown(self):
        self.schema = None

    def test_geographic_opts(self):
        reference_result = {'service': 'station',
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


#suite = unittest.TestLoader().loadTestsFromNames([
#    'PercentageFieldTestCase'
#    ])

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <schema.py> ----
