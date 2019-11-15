# -*- coding: utf-8 -*-
"""
EIDA webservice request handling facilities.
"""

import contextlib
import io

import requests

from eidangservices import settings
from eidangservices.utils import logger
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
                   timeout=settings.EIDA_FEDERATOR_ENDPOINT_TIMEOUT,
                   logger=logger):
    """
    Make a request.

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param float timeout: Timeout in seconds

    :rtype: io.BytesIO
    """
    try:
        with request(timeout=timeout) as r:

            logger.debug('Request URL (absolute, encoded): {!r}'.format(r.url))
            logger.debug('Response headers: {!r}'.format(r.headers))

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


@contextlib.contextmanager
def raw_request(request,
                timeout=settings.EIDA_FEDERATOR_ENDPOINT_TIMEOUT):
    """
    Make a request. Return the raw, streamed response.

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param float timeout: Timeout in seconds
    :rtype: io.BytesIO
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


def stream_request(request,
                   timeout=settings.EIDA_FEDERATOR_ENDPOINT_TIMEOUT,
                   chunk_size=1024,
                   decode_unicode=False,
                   method='iter_content'):
    """
    Generator function making a streamed request.

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param float timeout: Timeout in seconds
    :param int chunksize: Chunksize in bytes
    :param bool decode_unicode: Content will be decoded using the best
        available encoding based on the response.
    :param string method: Streaming depending on method. Valid values are
        `iter_content` (default), `iter_lines`, `raw`

    .. note::

        :code:`method=iter_content` may lead to significant performance issues.
        Use :code:`method=raw` instead.
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
