# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <request.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA webservices.
#
# EIDA webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA webservices is distributed in the hope that it will be useful,
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
# 2018/06/18        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA webservice request handling facilities
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import contextlib
import io

import requests

from eidangservices import settings
from eidangservices.utils.error import Error


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

# ---- END OF <request.py> ----
