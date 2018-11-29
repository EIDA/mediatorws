# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <strict.py>
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
EIDA NG webservices strict module test facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import unittest

import flask # noqa
import marshmallow as ma

from werkzeug.datastructures import OrderedMultiDict

from eidangservices.utils import strict

try:
    import mock
except ImportError:
    import unittest.mock as mock


# -----------------------------------------------------------------------------
class KeywordParserTestCase(unittest.TestCase):

    class TestSchema(ma.Schema):
        f = ma.fields.Str()

    # class TestSchema

    class TestReq(object):
        pass

    # class TestReq

    def test_parse_arg_keys(self):
        arg_dict = OrderedMultiDict()
        arg_dict.add('f', 'val')
        arg_dict.add('b', 'val')
        arg_dict.add('x', 'val')

        reference_result = tuple(['f', 'b', 'x'])

        test_result = strict.KeywordParser.\
            _parse_arg_keys(arg_dict)

        self.assertEqual(test_result, reference_result)

    # test_parse_arg_keys ()

    def test_parse_postfile(self):
        postfile = "f=val\nb=val\nx=val"

        test_result = strict.KeywordParser.\
            _parse_postfile(postfile)

        self.assertIn('f', test_result)
        self.assertIn('b', test_result)
        self.assertIn('x', test_result)
        self.assertEqual(3, len(test_result))

    # test_parse_postfile ()

    def test_parse_postfile_equal(self):
        postfile = "="

        with self.assertRaises(strict.ValidationError):
            test_result = strict.KeywordParser.\
                _parse_postfile(postfile)

    # test_parse_postfile_equal ()

    def test_parse_postfile_empty(self):
        postfile = ""

        reference_result = tuple()

        test_result = strict.KeywordParser.\
            _parse_postfile(postfile)

        self.assertEqual(test_result, reference_result)

    # test_parse_postfile_empty ()

    def test_parse_postfile_with_sncl(self):
        postfile = "NL HGN * 2013-10-10 2013-10-11"

        reference_result = tuple()

        test_result = strict.KeywordParser.\
            _parse_postfile(postfile)

        self.assertEqual(test_result, reference_result)

    # test_parse_postfile_with_sncl ()

    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_get_invalid(self, mock_request_factory):
        request = self.TestReq()
        request.method = 'GET'
        request.args = OrderedMultiDict()
        request.args.add('f', 'val')
        request.args.add('b', 'val')

        mock_request_factory.return_value = request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('query',)
        )
        def viewfunc():
            pass

        with self.assertRaises(strict.ValidationError):
            viewfunc()

    # test_with_strict_args_get_invalid ()

    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_get_valid(self, mock_request_factory):
        request = self.TestReq()
        request.method = 'GET'
        request.args = OrderedMultiDict({'f': 'val'})

        mock_request_factory.return_value = request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('query',)
        )
        def viewfunc():
            pass

        viewfunc()

    # test_with_strict_args_get_valid ()

    @mock.patch('flask.Request')
    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_post_valid(
        self, mock_request_factory, mock_request
    ):
        test_str = b"f=val\nNL HGN ?? * 2013-10-10 2013-10-11"
        mock_request.method = 'POST'
        mock_request.get_data.return_value = test_str.decode('utf-8')
        mock_request.content_length = len(test_str)

        mock_request_factory.return_value = mock_request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('form',)
        )
        def viewfunc():
            pass

        viewfunc()

    # test_with_strict_args_post_valid ()

    @mock.patch('flask.Request')
    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_post_invalid(
        self, mock_request_factory, mock_request
    ):
        test_str = b"f=val\nb=val\nNL HGN ?? * 2013-10-10 2013-10-11"
        mock_request.method = 'POST'
        mock_request.get_data.return_value = test_str.decode('utf-8')
        mock_request.content_length = len(test_str)

        mock_request_factory.return_value = mock_request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('form',)
        )
        def viewfunc():
            pass

        with self.assertRaises(strict.ValidationError):
            viewfunc()

    # test_with_strict_args_post_invalid ()

    @mock.patch('flask.Request')
    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_post_only_sncl(
        self, mock_request_factory, mock_request
    ):
        test_str = b"NL HGN ?? * 2013-10-10 2013-10-11"
        mock_request.method = 'POST'
        mock_request.get_data.return_value = test_str.decode('utf-8')
        mock_request.content_length = len(test_str)

        mock_request_factory.return_value = mock_request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('form',)
        )
        def viewfunc():
            pass

        viewfunc()

    # test_with_strict_args_post_only_sncl ()

    @mock.patch('flask.Request')
    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_post_empty(
        self, mock_request_factory, mock_request
    ):
        test_str = b""
        mock_request.method = 'POST'
        mock_request.get_data.return_value = test_str.decode('utf-8')
        mock_request.content_length = len(test_str)

        mock_request_factory.return_value = mock_request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('form',)
        )
        def viewfunc():
            pass

        viewfunc()

    # test_with_strict_args_post_empty ()

    @mock.patch('flask.Request')
    @mock.patch(
        'eidangservices.utils.strict.flask_keywordparser.get_default_request'
    )
    def test_with_strict_args_post_equal(
        self, mock_request_factory, mock_request
    ):
        test_str = b"="
        mock_request.method = 'POST'
        mock_request.get_data.return_value = test_str.decode('utf-8')
        mock_request.content_length = len(test_str)

        mock_request_factory.return_value = mock_request

        @strict.with_strict_args(
            self.TestSchema(),
            locations=('form',)
        )
        def viewfunc():
            pass

        with self.assertRaises(strict.ValidationError):
            viewfunc()

    # test_with_strict_args_post_equal ()

# class KeywordParserTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__': # noqa
    unittest.main()

# ---- END OF <strict.py> ----
