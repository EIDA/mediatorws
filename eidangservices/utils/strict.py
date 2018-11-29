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
# EDIA NG webservices is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----
#
# Copyright (c) Sven Marti (ETH), Daniel Armbruster (ETH), Fabian Euchner (ETH)
#
# REVISION AND CHANGES
# 2018/06/05        V0.1    Sven Marti
# =============================================================================
"""
Keywordparser facilities for EIDA NG webservices.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import functools
import inspect
import logging

from webargs.flaskparser import parser as flaskparser
from marshmallow import Schema, exceptions

from eidangservices import settings
from eidangservices.utils.error import Error


class KeywordParserError(Error):
    """Base KeywordParser error ({})."""


class ValidationError(KeywordParserError, exceptions.ValidationError):
    """ValidationError: {}."""


def _callable_or_raise(obj):
    """
    Makes sure an object is callable if it is not ``None``. If not
    callable, a ValueError is raised.
    """
    if obj and not callable(obj):
        raise ValueError("{0!r} is not callable.".format(obj))
    return obj

# _callable_or_raise ()

# -----------------------------------------------------------------------------
class KeywordParser(object):
    """
    Base class for keyword parsers.
    """

    LOGGER = 'strict.keywordparser'

    __location_map__ = {
        'query': 'parse_querystring',
        'form': 'parse_form'}

    def __init__(self, error_handler=None):
        self.error_callback = _callable_or_raise(error_handler)
        self.logger = logging.getLogger(self.LOGGER)

    # __init__ ()

    @staticmethod
    def _parse_arg_keys(arg_dict):
        """
        :param dict arg_dict: Dictionary like structure to be parsed

        :returns: Tuple with argument keys
        :rtype: tuple
        """

        return tuple(arg_dict.keys())

    # _parse_arg_keys ()

    @staticmethod
    def _parse_postfile(postfile):
        """
        Parse all argument keys from a POST request file.

        :param str postfile: Postfile content

        :returns: Tuple with parsed keys.
        :rtype: tuple
        """
        argmap = {}

        for line in postfile.split('\n'):
            _line = line.split(
                settings.FDSNWS_QUERY_VALUE_SEPARATOR_CHAR)
            if len(_line) != 2:
                continue

            if all(w == '' for w in _line):
                raise ValidationError('RTFM :)')

            argmap[_line[0]] = _line[1]

        return tuple(argmap.keys())

    # _parse_postfile ()

    def parse_querystring(self, req):
        """
        Parse argument keys from :code:`req.args`.

        :param req: Request object to be parsed
        :type req: :py:class:`flask.Request`
        """

        return self._parse_arg_keys(req.args)

    # parse_querystring ()

    def parse_form(self, req):
        """
        :param req: Request object to be parsed
        :type req: :py:class:`flask.Request`
        """
        try:
            parsed_list = self._parse_postfile(self._get_data(req))
        except ValidationError as err:
            if self.error_callback:
                self.error_callback(err, req)
            else:
                self.handle_error(err, req)

        return parsed_list

    # parse_form ()

    def get_default_request(self):
        """
        Template function for getting the default request.
        """

        raise NotImplementedError

    # get_default_request ()

    def parse(self, func, schemas, locations):
        """
        Validate request query parameters.

        :param schemas: Marshmallow Schemas to validate request after
        :type schemas: tuple/list of :py:class:`marshmallow.Schema`
            or :py:class:`marshmallow.Schema`
        :param locations:
        :type locations: tuple of str

        Calls `handle_error` with :py:class:`ValidationError`.
        """

        req = self.get_default_request()

        if inspect.isclass(schemas):
            schemas = [schemas()]
        elif isinstance(schemas, Schema):
            schemas = [schemas]

        valid_fields = set()
        for schema in [s() if inspect.isclass(s) else s for s in schemas]:
            valid_fields.update(schema.fields.keys())

        parsers = []
        for l in locations:
            try:
                f = self.__location_map__[l]
                if inspect.isfunction(f):
                    function = f
                else:
                    function = getattr(self, f)
                parsers.append(function)
            except KeyError:
                raise ValueError('Invalid location: {!r}'.format(l))

        @functools.wraps(func)
        def decorator(*args, **kwargs):

            req_args = set()

            for f in parsers:
                req_args.update(f(req))

            invalid_args = req_args.difference(valid_fields)
            if invalid_args:
                err = ValidationError(
                    'Invalid request query parameters: {}'.format(
                        invalid_args))

                if self.error_callback:
                    self.error_callback(err, req)
                else:
                    self.handle_error(err, req)

            return func(*args, **kwargs)

        # decorator ()

        return decorator

    # parse ()

    def with_strict_args(self, schemas, locations=None):
        """
        Wrapper of :py:func:`parse`.
        """
        return functools.partial(self.parse,
                                 schemas=schemas,
                                 locations=locations)

    # with_strict_args ()

    def _get_data(self, req, as_text=True,
                  max_content_length=settings.MAX_POST_CONTENT_LENGTH):
        """
        Savely reads the buffered incoming data from the client.

        :param req: Request the raw data is read from
        :type req: :py:class:`flask.Request`
        :param bool as_text: If set to :code:`True` the return value will be a
            decoded unicode string.
        :param int max_content_length: Max bytes accepted

        :returns: Byte string or rather unicode string, respectively. Depending
            on the :code:`as_text` parameter.
        """
        if req.content_length > max_content_length:
            err = ValidationError(
                'Request too large: {} bytes > {} bytes '.format(
                    req.content_length, max_content_length))

            if self.error_callback:
                self.error_callback(err, req)
            else:
                self.handle_error(err, req)

        return req.get_data(cache=True, as_text=as_text)

    # _get_data ()

    def handle_error(self, error, req):
        """
        Called if an error occurs while parsing strict args.
        By default, just logs and raises ``error``.

        :param Exception error: an Error to be handled
        :param Request req: request object

        :raises: error
        :rtype: Exception
        """
        self.logger.error(error)
        raise error

    # handle_error ()

    def error_handler(self, func):
        """
        Decorator that registers a custom error handling function. The
        function should received the raised error, request object used
        to parse the request. Overrides the parser's ``handle_error``
        method.

        Example: ::

            from strict import flask_keywordparser

            class CustomError(Exception):
                pass


            @flask_keywordparser.error_handler
            def handle_error(error, req):
                raise CustomError(error.messages)

        :param callable func: The error callback to register.
        """
        self.error_callback = func
        return func

# class KeywordParser


# -----------------------------------------------------------------------------
class FlaskKeywordParser(KeywordParser):
    """
    Flask implementation of :py:class:`KeywordParser`.
    """

    def get_default_request(self):
        """
        Returns the flask default request

        :returns: :py:class:`flask.Request`
        """

        return flaskparser.get_default_request()

    # get_default_request ()

# class FlaskKeywordParser


flask_keywordparser = FlaskKeywordParser()
with_strict_args = flask_keywordparser.with_strict_args


# ---- END OF <strict.py> ----
