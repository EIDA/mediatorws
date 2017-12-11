# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
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
# 2017/11/20        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Federator utility test facilities.
"""
from __future__ import (absolute_import, division, print_function,
        unicode_literals)

from builtins import *

import datetime
import io
import mock
import unittest

import flask
import marshmallow as ma

from werkzeug.exceptions import HTTPException
from werkzeug.datastructures import MultiDict
from webargs.flaskparser import parser

from eidangservices.federator.server import schema, misc
from eidangservices.federator.tests.helpers import POSTRequest

# -----------------------------------------------------------------------------
class FDSNWSParserTestCase(unittest.TestCase):

    class TestSchema(ma.Schema):
        f = ma.fields.Str()

        class Meta:
            strict = True

    # class TestŜchema


    class TestRequest(object):
        """emulates flask.Request"""
        data = None

        def __init__(self, data):
            self.stream = io.StringIO(data)

    # class TestRequest


    def setUp(self):
        self.sncls_schema = schema.ManySNCLSchema()

    def tearDown(self):
        self.sncls_schema = None

    @mock.patch('flask.Request')
    def test_get_single(self, mock_request):
        mock_request.args = MultiDict({'f': 'value',
                                       'net': 'CH',
                                       'sta': 'DAVOX',
                                       'start': '2017-01-01',
                                       'end': '2017-01-07'})
        reference_sncls = [misc.SNCL(network='CH',
                                    station='DAVOX',
                                    location='*',
                                    channel='*',
                                    starttime=datetime.datetime(2017, 01, 01),
                                    endtime=datetime.datetime(2017, 01, 07))]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = misc.fdsnws_parser.parse(self.sncls_schema, mock_request,
                                         locations=('query',))['sncls']
        self.assertEqual(sncls, reference_sncls)

    # test_get_single ()

    @mock.patch('flask.Request')
    def test_get_multiple(self, mock_request):
        mock_request.args = MultiDict({'f': 'value',
                                       'net': 'CH',
                                       'sta': 'DAVOX,BALST',
                                       'start': '2017-01-01',
                                       'end': '2017-01-07'})
        reference_sncls = [misc.SNCL(network='CH',
                                     station='DAVOX',
                                     location='*',
                                     channel='*',
                                     starttime=datetime.datetime(2017, 01, 01),
                                     endtime=datetime.datetime(2017, 01, 07)),
                           misc.SNCL(network='CH',
                                     station='BALST',
                                     location='*',
                                     channel='*',
                                     starttime=datetime.datetime(2017, 01, 01),
                                     endtime=datetime.datetime(2017, 01, 07))]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = misc.fdsnws_parser.parse(self.sncls_schema, mock_request,
                                         locations=('query',))['sncls']
        self.assertEqual(sncls, reference_sncls)

    # test_get_multiple () 

    @mock.patch('flask.Request')
    def test_get_missing(self, mock_request):
        mock_request.args = MultiDict({'f': 'value'})
        reference_sncls = [misc.SNCL(network='*',
                                     station='*',
                                     location='*',
                                     channel='*',
                                     starttime=None,
                                     endtime=None)]

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        sncls = misc.fdsnws_parser.parse(self.sncls_schema, mock_request,
                                         locations=('query',))['sncls']
        self.assertEqual(sncls, reference_sncls)

    # test_get_missing ()

    @mock.patch('flask.Request')
    def test_get_invalid(self, mock_request):
        mock_request.args = MultiDict({'f': 'value',
                                       'net': 'CH!, GR'})

        test_args = parser.parse(self.TestSchema(), mock_request,
                                 locations=('query',))
        self.assertEqual(dict(test_args), {'f': 'value'})

        with self.assertRaises(HTTPException):
            misc.fdsnws_parser.parse(self.sncls_schema, mock_request,
                                     locations=('query',))['sncls']

    # test_get_invalid 

    def test_post_single(self):
        self.sncls_schema.context = {'request': POSTRequest()}

        reference_sncls = [misc.SNCL(network='NL',
                                    station='HGN',
                                    location='??',
                                    channel='*',
                                    starttime=datetime.datetime(2013, 10, 10),
                                    endtime=datetime.datetime(2013, 10, 11))]
        test_request = self.TestRequest(
                "f=value\nNL HGN ?? * 2013-10-10 2013-10-11")
        test_args = misc.fdsnws_parser.parse(self.TestSchema(), test_request,
                                             locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        sncls = misc.fdsnws_parser.parse(self.sncls_schema, test_request,
                                         locations=('form',))['sncls']
        self.assertEqual(sncls, reference_sncls)

    # test_post_single ()

    def test_post_multiple(self):
        self.sncls_schema.context = {'request': POSTRequest()}

        reference_sncls = [misc.SNCL(network='NL',
                                    station='HGN',
                                    location='??',
                                    channel='*',
                                    starttime=datetime.datetime(2013, 10, 10),
                                    endtime=datetime.datetime(2013, 10, 11)),
                           misc.SNCL(network='GR',
                                    station='BFO',
                                    location='*',
                                    channel='*',
                                    starttime=datetime.datetime(2017, 01, 01),
                                    endtime=datetime.datetime(2017, 01, 31))]

        test_request = self.TestRequest(
                "f=value\nNL HGN ?? * 2013-10-10 2013-10-11\n"
                "GR BFO * * 2017-01-01 2017-01-31")
        test_args = misc.fdsnws_parser.parse(self.TestSchema(), test_request,
                                             locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        sncls = misc.fdsnws_parser.parse(self.sncls_schema, test_request,
                                         locations=('form',))['sncls']
        self.assertEqual(sncls, reference_sncls)

    # test_post_multiple ()

    def test_post_empty(self):
        self.sncls_schema.context = {'request': POSTRequest()}

        test_request = self.TestRequest("")
        with self.assertRaises(HTTPException):
            sncls = misc.fdsnws_parser.parse(self.sncls_schema, test_request,
                                             locations=('form',))['sncls']

    # test_post_empty ()

    def test_post_missing(self):
        self.sncls_schema.context = {'request': POSTRequest()}

        test_request = self.TestRequest("f=value\n")
        test_args = misc.fdsnws_parser.parse(self.TestSchema(), test_request,
                                             locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        with self.assertRaises(HTTPException):
            misc.fdsnws_parser.parse(self.sncls_schema, test_request,
                                     locations=('form',))

    # test_post_missing ()

    def test_post_invalid(self):
        self.sncls_schema.context = {'request': POSTRequest()}

        test_request = self.TestRequest(
                "f=value\nNL HGN * 2013-10-10 2013-10-11")
        test_args = misc.fdsnws_parser.parse(self.TestSchema(), test_request,
                                             locations=('form',))
        self.assertEqual(dict(test_args), {'f': 'value'})
        with self.assertRaises(HTTPException):
            sncls = misc.fdsnws_parser.parse(self.sncls_schema, test_request,
                                             locations=('form',))['sncls']

    # test_post_invalid ()

# class FDSNWSParserTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <misc.py> ----
