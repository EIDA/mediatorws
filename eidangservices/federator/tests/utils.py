# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/11/20        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Federator utility test facilities.
"""

import datetime
import io
import unittest

import marshmallow as ma

from werkzeug.exceptions import HTTPException

from eidangservices.federator.server import schema
from eidangservices.federator.tests.helpers import POSTRequest
from eidangservices.federator.server.misc import fdsnws_parser


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
        self.sncl_schema = schema.SNCLSchema(context={'request': POSTRequest()})

    def tearDown(self):
        self.sncl_schema = None

    def test_parser(self):
        reference_sncl = {
                'network': [u'NL'],
                'station': [u'HGN'],
                'location': [u'??'],
                'channel': [u'*'],
                'starttime': [datetime.datetime(2013, 10, 10)],
                'endtime': [datetime.datetime(2013, 10, 11)]
                }
        test_request = self.TestRequest(
                u"f=value\nNL HGN ?? * 2013-10-10 2013-10-11")
        
        test_args = fdsnws_parser.parse(self.TestSchema(), test_request,
                locations=('form',))
        self.assertEqual(dict(test_args), {'f': u'value'})
        sncl_args = fdsnws_parser.parse(self.sncl_schema, test_request,
                locations=('form',))
        self.assertEqual(dict(sncl_args), reference_sncl)

    # test_parser () 

    def test_missing_sncls(self):
        test_request = self.TestRequest(
                u"f=value\n")
        test_args = fdsnws_parser.parse(self.TestSchema(), test_request,
                locations=('form',))
        self.assertEqual(dict(test_args), {'f': u'value'})

        with self.assertRaises(HTTPException):
            sncl_args = fdsnws_parser.parse(self.sncl_schema, test_request,
                    locations=('form',))

    # test_missing_sncls () 

    def test_empty_request(self):
        test_request = self.TestRequest(u"")
        with self.assertRaises(HTTPException):
            sncl_args = fdsnws_parser.parse(self.sncl_schema, test_request,
                    locations=('form',))

    # test_empty_request () 

    def test_single_sncl(self):
        reference_sncl = {
                'network': [u'NL'],
                'station': [u'HGN'],
                'location': [u'??'],
                'channel': [u'*'],
                'starttime': [datetime.datetime(2013, 10, 10)],
                'endtime': [datetime.datetime(2013, 10, 11)]
                }
        test_request = self.TestRequest(
                u"NL HGN ?? * 2013-10-10 2013-10-11")
        sncl_args = fdsnws_parser.parse(self.sncl_schema, test_request,
                locations=('form',))
        self.assertEqual(dict(sncl_args), reference_sncl)

    # test_single_sncl () 

    def test_multiple_sncls(self):
        reference_result = {
                'network': [u'NL', u'CH'],
                'station': [u'HGN', u'DAVOX'],
                'location': [u'??', u'??'],
                'channel': [u'*', u'*'],
                'starttime': [
                    datetime.datetime(2013, 10, 10),
                    datetime.datetime(2017, 10, 10)],
                'endtime': [
                    datetime.datetime(2013, 10, 11),
                    datetime.datetime(2017, 10, 11)]
                }
        test_request = self.TestRequest(
                u"NL HGN ?? * 2013-10-10 2013-10-11\n" +
                u"CH DAVOX ?? * 2017-10-10 2017-10-11")
        sncl_args = fdsnws_parser.parse(self.sncl_schema, test_request,
                locations=('form',))
        self.assertEqual(dict(sncl_args), reference_result)

    # test_multiple_sncls () 

# class FDSNWSParserTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <misc.py> ----
