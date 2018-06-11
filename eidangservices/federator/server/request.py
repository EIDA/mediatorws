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

import contextlib
import functools
import io

from urllib.parse import urlparse, urlunparse

import requests

from eidangservices import settings, utils
from eidangservices.utils.error import Error
from eidangservices.utils.schema import StreamEpochSchema


# NOTE(damb): RequestError instances carry the response, too.
class RequestsError(requests.exceptions.RequestException, Error):
    """Base request error ({})."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ClientError(RequestsError):
    """Response code not OK ({})."""

class NoContent(RequestsError):
    """The request '{}' is returning no content ({})."""


@contextlib.contextmanager
def binary_request(request,
                   timeout=settings.EIDA_FEDERATOR_ENDPOINT_TIMEOUT):
    """
    Make a request.
    """
    try:
        with request(timeout=timeout) as r:

            if r.status_code in settings.FDSN_NO_CONTENT_CODES:
                raise NoContent(r.url, r.status_code, response=r)

            r.raise_for_status()
            if r.status_code != 200:
                raise ClientError(r.status_code, response=r)

            yield io.BytesIO(r.content)

    except (NoContent, ClientError) as err:
        raise err
    except requests.exceptions.RequestException as err:
        raise RequestsError(err, response=err.response)

# binary_request ()

@contextlib.contextmanager
def raw_request(request,
                timeout=settings.EIDA_FEDERATOR_ENDPOINT_TIMEOUT):
    """
    Make a request. Return the raw, streamed response.
    """
    try:
        with request(stream=True, timeout=timeout) as r:

            if r.status_code in settings.FDSN_NO_CONTENT_CODES:
                raise NoContent(r.url, r.status_code, response=r)

            r.raise_for_status()
            if r.status_code != 200:
                raise ClientError(r.status_code, response=r)

            yield r.raw

    except (NoContent, ClientError) as err:
        raise err
    except requests.exceptions.RequestException as err:
        raise RequestsError(err, response=err.response)

# raw_request ()

def stream_request(request,
                   timeout=settings.EIDA_FEDERATOR_ENDPOINT_TIMEOUT,
                   chunk_size=1024,
                   decode_unicode=False,
                   method='iter_content'):
    """
    Generator function making a streamed request.

    :param int timeout: Timeout in seconds
    :param int chunksize: Chunksize in bytes
    :param bool decode_unicode: Content will be decoded using the best
    available encoding based on the response.
    :param string method: Streaming depending on method. Valid values are
    `iter_content` (default), `iter_lines`, `raw`

    .. note::

        `method=iter_content` may lead to significant performance issues. Use
        `method=raw` instead.
    """
    METHODS = ('iter_content', 'iter_lines', 'raw')
    if method not in METHODS:
        raise ValueError('Invalid method chosen: {!r}.'.format(method))

    try:
        with request(stream=True, timeout=timeout) as r:

            if r.status_code in settings.FDSN_NO_CONTENT_CODES:
                raise NoContent(r.url, r.status_code, response=r)

            r.raise_for_status()
            if r.status_code != 200:
                raise ClientError(r.status_code, response=r)

            if method == 'raw':
                for chunk in r.raw.stream(chunk_size,
                                          decode_content=decode_unicode):
                    yield chunk

            elif method == 'iter_lines':
                for line in r.iter_lines(chunk_size=chunk_size,
                                         decode_unicode=decode_unicode):
                    yield line
            else:
                for chunk in r.iter_content(chunk_size=chunk_size,
                                            decode_unicode=decode_unicode):
                    yield chunk

    except (NoContent, ClientError) as err:
        raise err
    except requests.exceptions.RequestException as err:
        raise RequestsError(err, response=err.response)

# binary_stream_request ()

# -----------------------------------------------------------------------------
class RequestHandlerBase(object):
    """
    RequestHandler base class implementation.

    :param str url: URL
    :param dict query_params: Dictionary of query parameters
    :param list stream_epochs: List of
    :cls:`eidangservices.utils.sncl.StreamEpoch` objects
    """
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
    Representation of a eidaws-routing request handler.
    """
    QUERY_PARAMS = set(('service',
                        'minlatitude',
                        'maxlatitude',
                        'minlongitude',
                        'maxlongitude'))

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
        qp.update(utils.convert_scnl_dicts_to_query_params(
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
                                 params=self.payload_get)

    def post(self):
        return functools.partial(requests.post, self.url,
                                 data=self.payload_post)

# class RoutingURL


class GranularFdsnRequestHandler(RequestHandlerBase):
    """
    Representation of a FDSN webservice request handler.
    """
    QUERY_PARAMS = set(('service', ))

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
                                 data=self.payload_post)

# class GranularFdsnRequestHandler


# ---- END OF <request.py> ----
