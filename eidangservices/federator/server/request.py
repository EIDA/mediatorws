# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <request.py>
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
# 2018/03/28        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA federator request handling facilities
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

from future.standard_library import install_aliases
install_aliases()

import functools

from urllib.parse import urlparse, urlunparse

import requests

from eidangservices import settings, utils
from eidangservices.utils.schema import StreamEpochSchema
from eidangservices.federator import __version__


class RequestHandlerBase(object):
    """
    RequestHandler base class implementation.

    :param str url: URL
    :param dict query_params: Dictionary of query parameters
    :param list stream_epochs: List of
        :py:class:`eidangservices.utils.sncl.StreamEpoch` objects

    """
    HEADERS = {"user-agent": "EIDA-Federator/" + __version__,
               # force no encoding, because eida-federator currently cannot
               # handle this
               "Accept-Encoding": ""}

    def __init__(self, url, query_params={}, stream_epochs=[]):
        if isinstance(url, bytes):
            url = url.decode('utf-8')
        url = urlparse(url)
        self._scheme = url.scheme
        self._netloc = url.netloc
        self._path = url.path.rstrip(
            settings.FDSN_QUERY_METHOD_TOKEN).rstrip('/')

        self._query_params = query_params
        self._stream_epochs = stream_epochs

    # __init__ ()

    @property
    def url(self):
        return urlunparse(
            (self._scheme,
             self._netloc,
             '{}/{}'.format(self._path, settings.FDSN_QUERY_METHOD_TOKEN),
             '',
             '',
             ''))

    @property
    def stream_epochs(self):
        return self._stream_epochs

    @property
    def payload_get(self):
        raise NotImplementedError

    @property
    def payload_post(self):
        data = '\n'.join('{}={}'.format(p, v)
                         for p, v in self._query_params.items())
        return ['{}\n{}'.format(data, stream_epoch)
                for stream_epoch in self._stream_epochs]

    # payload_post ()

    def get(self):
        raise NotImplementedError

    def post(self):
        return [functools.partial(requests.post, self.url, data=p)
                for p in self.payload_post]

    def __str__(self):
        return ', '.join(["scheme={}".format(self._scheme),
                          "netloc={}".format(self._netloc),
                          "path={}.".format(self._path),
                          "qp={}".format(self._query_params)])

    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, self)

# class RequestHandlerBase


class RoutingRequestHandler(RequestHandlerBase):
    """
    Representation of a `eidaws-routing` request handler.

    .. note::

        Since both `eidaws-routing` and `eida-stationlite` implement the same
        interface :py:class:`RoutingRequestHandler` may be used for both
        webservices.
    """
    QUERY_PARAMS = set(('service',
                        'level',
                        'minlatitude', 'minlat',
                        'maxlatitude', 'maxlat',
                        'minlongitude', 'minlon',
                        'maxlongitude', 'maxlon'))

    class GET(object):
        """
        Utility class emulating a GET request.
        """
        method = 'GET'

    # class GET

    def __init__(self, url, query_params={}, stream_epochs=[]):
        super().__init__(url, query_params, stream_epochs)

        self._query_params = dict(
            (p, v) for p, v in self._query_params.items()
            if p in self.QUERY_PARAMS)

        self._query_params['format'] = 'post'

    # __init__ ()

    @property
    def payload_get(self):
        se_schema = StreamEpochSchema(many=True, context={'request': self.GET})

        qp = self._query_params
        qp.update(utils.convert_sncl_dicts_to_query_params(
                  se_schema.dump(self._stream_epochs)))
        return qp

    # payload_get ()

    @property
    def payload_post(self):
        data = '\n'.join('{}={}'.format(p, v)
                         for p, v in self._query_params.items())

        return '{}\n{}'.format(
            data, '\n'.join(str(se) for se in self._stream_epochs))

    # payload_post ()

    def get(self):
        return functools.partial(requests.get, self.url,
                                 params=self.payload_get, headers=self.HEADERS)

    def post(self):
        return functools.partial(requests.post, self.url,
                                 data=self.payload_post, headers=self.HEADERS)

# class RoutingURL


class GranularFdsnRequestHandler(RequestHandlerBase):
    """
    Representation of a FDSN webservice request handler.
    """
    QUERY_PARAMS = set(('service',
                        'nodata',
                        'minlatitude', 'minlat',
                        'maxlatitude', 'maxlat',
                        'minlongitude', 'minlon',
                        'maxlongitude', 'maxlon'))

    def __init__(self, url, stream_epoch, query_params={}):
        super().__init__(url, query_params, [stream_epoch])
        self._query_params = dict((p, v)
                                  for p, v in self._query_params.items()
                                  if p not in self.QUERY_PARAMS)
    # __init__ ()

    @property
    def payload_post(self):
        data = '\n'.join('{}={}'.format(p, v)
                         for p, v in self._query_params.items())
        return '{}\n{}'.format(data, self.stream_epochs[0])

    def post(self):
        return functools.partial(requests.post, self.url,
                                 data=self.payload_post, headers=self.HEADERS)

# class GranularFdsnRequestHandler


# ---- END OF <request.py> ----
