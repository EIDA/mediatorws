# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <fdsnws.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices is distributed in the hope that it will be useful,
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
# 2017/11/20        V0.1    Daniel Armbruster
#
# =============================================================================
"""
EIDA NG webservices utility test facilities.
"""

import datetime
import unittest

from unittest import mock

import flask # noqa
import marshmallow as ma

from werkzeug.exceptions import HTTPException
from werkzeug.datastructures import MultiDict
from webargs.flaskparser import parser

from eidangservices.utils import fdsnws, schema, sncl


# -----------------------------------------------------------------------------
class FDSNWSParserMixinTestCase(unittest.TestCase):

    def test_parse_dict_single(self):
        arg_dict = MultiDict({'f': 'value',
                              'net': 'CH',
                              'sta': 'DAVOX',
                              'start': '2017-01-01',
                              'end': '2017-01-07'})

        reference_result = [{
            'net': 'CH',
            'sta': 'DAVOX',
            'loc': '*',
            'cha': '*',
            'start': '2017-01-01',
            'end': '2017-01-07'}]

        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_streamepochs_from_argdict(arg_dict)

        self.assertEqual(test_dict['stream_epochs'], reference_result)

    # test_parse_dict_single ()

    def test_parse_dict_multiple(self):
        arg_dict = MultiDict({'f': 'value',
                              'net': 'CH',
                              'sta': 'DAVOX,BALST',
                              'start': '2017-01-01',
                              'end': '2017-01-07'})

        reference_result = [{
            'net': 'CH',
            'sta': 'DAVOX',
            'loc': '*',
            'cha': '*',
            'start': '2017-01-01',
            'end': '2017-01-07'}, {
            'net': 'CH',
            'sta': 'BALST',
            'loc': '*',
            'cha': '*',
            'start': '2017-01-01',
            'end': '2017-01-07'}]

        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_streamepochs_from_argdict(arg_dict)

        self.assertEqual(test_dict['stream_epochs'], reference_result)

    # test_parse_dict_multiple ()

    def test_postfile_single(self):
        postfile = "f=value\nNL HGN ?? * 2013-10-10 2013-10-11"

        reference_result = {
            'f': 'value',
            'stream_epochs': [{
                'net': 'NL',
                'sta': 'HGN',
                'loc': '??',
                'cha': '*',
                'start': '2013-10-10',
                'end': '2013-10-11'}]}

        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_postfile(postfile)

        self.assertEqual(test_dict, reference_result)

    # test_postfile_single ()

    def test_postfile_multiple(self):
        postfile = ("f=value\n"
                    "CH DAVOX * * 2017-01-01 2017-01-07\n"
                    "CH BALST * * 2017-01-01 2017-01-07")

        reference_result = {
            'f': 'value',
            'stream_epochs': [{
                'net': 'CH',
                'sta': 'DAVOX',
                'loc': '*',
                'cha': '*',
                'start': '2017-01-01',
                'end': '2017-01-07'}, {
                'net': 'CH',
                'sta': 'BALST',
                'loc': '*',
                'cha': '*',
                'start': '2017-01-01',
                'end': '2017-01-07'}]}

        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_postfile(postfile)

        self.assertEqual(test_dict, reference_result)

    # test_postfile_multiple ()

    def test_postfile_invalid(self):
        postfile = "f=value\nNL HGN * 2013-10-10 2013-10-11"

        reference_result = {
            'f': 'value',
            'stream_epochs': []}

        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_postfile(postfile)

        self.assertEqual(test_dict, reference_result)

    # test_postfile_invalid ()

    def test_postfile_empty(self):
        postfile = ''
        reference_result = {'stream_epochs': []}
        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_postfile(postfile)

        self.assertEqual(test_dict, reference_result)

    # test_postfile_empty ()

    def test_postfile_equal(self):
        postfile = '='
        reference_result = {'stream_epochs': []}
        test_dict = fdsnws.FDSNWSParserMixin.\
            _parse_postfile(postfile)

        self.assertEqual(test_dict, reference_result)

    # test_postfile_equal ()

# class FDSNWSParserMixinTestCase


class FDSNWSFlaskParserTestCase(unittest.TestCase):

    class TestSchema(ma.Schema):
        f = ma.fields.Str()

        class Meta:
            strict = True

    # class TestSchema

    @mock.patch('flask.request')
    def test_get_single(self, mock_request):
        mock_request.method = 'GET'
        mock_request.args = MultiDict({'f': 'value',
                                       'net': 'CH',
                                       'sta': 'DAVOX',
                                       'start': '2017-01-01',
                                       'end': '2017-01-07'})
        reference_sncls = [sncl.StreamEpoch.from_sncl(
            network='CH',
            station='DAVOX',
            location='*',
            channel='*',
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 7))]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))

        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
            context={'request': mock_request}),
            mock_request,
            locations=('query',))['stream_epochs']
        self.assertEqual(sncls, reference_sncls)

    # test_get_single ()

    @mock.patch('flask.request')
    def test_get_single_extented(self, mock_request):
        mock_request.method = 'GET'
        mock_request.args = MultiDict({'f': 'value',
                                       'network': 'CH',
                                       'station': 'DAVOX',
                                       'starttime': '2017-01-01',
                                       'endtime': '2017-01-07'})
        reference_sncls = [sncl.StreamEpoch.from_sncl(
            network='CH',
            station='DAVOX',
            location='*',
            channel='*',
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 7))]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
            context={'request': mock_request}),
            mock_request,
            locations=('query',))['stream_epochs']
        self.assertEqual(sncls, reference_sncls)

    # test_get_single_extented ()

    @mock.patch('flask.Request')
    def test_get_multiple(self, mock_request):
        mock_request.method = 'GET'
        mock_request.args = MultiDict({'f': 'value',
                                       'net': 'CH',
                                       'sta': 'DAVOX,BALST',
                                       'start': '2017-01-01',
                                       'end': '2017-01-07'})
        reference_sncls = [sncl.StreamEpoch.from_sncl(
            network='CH',
            station='DAVOX',
            location='*',
            channel='*',
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 7)),
            sncl.StreamEpoch.from_sncl(
            network='CH',
            station='BALST',
            location='*',
            channel='*',
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 7))]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
            context={'request': mock_request}),
            mock_request,
            locations=('query',))['stream_epochs']
        self.assertEqual(sncls, reference_sncls)

    # test_get_multiple ()

    @mock.patch('flask.Request')
    def test_get_missing(self, mock_request):
        mock_request.method = 'GET'
        mock_request.args = MultiDict({'f': 'value'})

        reference_sncls = [sncl.StreamEpoch(stream=sncl.Stream())]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
            context={'request': mock_request}),
            mock_request,
            locations=('query',))['stream_epochs']
        self.assertEqual(sncls, reference_sncls)

    # test_get_missing ()

    @mock.patch('flask.Request')
    def test_get_invalid(self, mock_request):
        mock_request.method = 'GET'
        mock_request.args = MultiDict({'f': 'value',
                                       'net': 'CH!, GR'})

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        with self.assertRaises(HTTPException):
            fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
                context={'request': mock_request}),
                mock_request,
                locations=('query',))['stream_epochs']

    # test_get_invalid

    @mock.patch('flask.Request')
    def test_post_single(self, mock_request):
        test_str = b"f=value\nNL HGN ?? * 2013-10-10 2013-10-11"
        mock_request.method = 'POST'
        mock_request.content_length = len(test_str)
        mock_request.get_data.return_value = test_str.decode('utf-8')

        reference_sncls = [sncl.StreamEpoch.from_sncl(
            network='NL',
            station='HGN',
            location='??',
            channel='*',
            starttime=datetime.datetime(2013, 10, 10),
            endtime=datetime.datetime(2013, 10, 11))]
        test_args = fdsnws.fdsnws_parser.parse(
            self.TestSchema(), mock_request, locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        sncls = fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
            context={'request': mock_request}),
            mock_request,
            locations=('form',))['stream_epochs']
        self.assertEqual(sncls, reference_sncls)

    # test_post_single ()

    @mock.patch('flask.Request')
    def test_post_multiple(self, mock_request):
        test_str = (b"f=value\nNL HGN ?? * 2013-10-10 2013-10-11\n"
                    b"GR BFO * * 2017-01-01 2017-01-31")
        mock_request.method = 'POST'
        mock_request.content_length = len(test_str)
        mock_request.get_data.return_value = test_str.decode('utf-8')

        reference_sncls = [sncl.StreamEpoch.from_sncl(
            network='NL',
            station='HGN',
            location='??',
            channel='*',
            starttime=datetime.datetime(2013, 10, 10),
            endtime=datetime.datetime(2013, 10, 11)),
            sncl.StreamEpoch.from_sncl(
            network='GR',
            station='BFO',
            location='*',
            channel='*',
            starttime=datetime.datetime(2017, 1, 1),
            endtime=datetime.datetime(2017, 1, 31))]

        test_args = fdsnws.fdsnws_parser.parse(self.TestSchema(), mock_request,
                                               locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        sncls = fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
            context={'request': mock_request}),
            mock_request,
            locations=('form',))['stream_epochs']
        self.assertEqual(sncls, reference_sncls)

    # test_post_multiple ()

    @mock.patch('flask.Request')
    def test_post_empty(self, mock_request):
        test_str = b""
        mock_request.method = 'POST'
        mock_request.content_length = len(test_str)
        mock_request.get_data.return_value = test_str.decode('utf-8')

        with self.assertRaises(HTTPException):
            fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
                context={'request': mock_request}),
                mock_request,
                locations=('form',))['stream_epochs']

    # test_post_empty ()

    @mock.patch('flask.Request')
    def test_post_missing(self, mock_request):
        test_str = b"f=value\n"
        mock_request.method = 'POST'
        mock_request.content_length = len(test_str)
        mock_request.get_data.return_value = test_str.decode('utf-8')

        test_args = fdsnws.fdsnws_parser.parse(self.TestSchema(), mock_request,
                                               locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        with self.assertRaises(HTTPException):
            fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
                context={'request': mock_request}),
                mock_request,
                locations=('form',))

    # test_post_missing ()

    @mock.patch('flask.Request')
    def test_post_invalid(self, mock_request):
        test_str = b"f=value\nNL HGN * 2013-10-10 2013-10-11"
        mock_request.method = 'POST'
        mock_request.content_length = len(test_str)
        mock_request.get_data.return_value = test_str.decode('utf-8')

        test_args = fdsnws.fdsnws_parser.parse(self.TestSchema(), mock_request,
                                               locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        with self.assertRaises(HTTPException):
            fdsnws.fdsnws_parser.parse(schema.ManyStreamEpochSchema(
                context={'request': mock_request}),
                mock_request,
                locations=('form',))['stream_epochs']

    # test_post_invalid ()

# class FDSNWSFlaskParserTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__': # noqa
    unittest.main()

# ---- END OF <fdsnws.py> ----
