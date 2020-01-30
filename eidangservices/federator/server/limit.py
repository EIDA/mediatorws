# -*- coding: utf-8 -*-
"""
Facilities to limit the number of concurrent endpoint requests.
"""

# import contextlib
import logging
import time

import requests

from urllib.parse import urlsplit

from eidangservices.utils.error import ErrorWithTraceback


def _extract_service_from_fdsnws_url(url):
    r = urlsplit(url)
    path = r.path.split('/')
    if len(path) != 5:
        raise ValueError('Invalid URL: {!r}'.format(url))

    return path[2]


# -----------------------------------------------------------------------------
class RequestLimitingError(ErrorWithTraceback):
    """Request limiting base error ({})."""


class TimeoutError(RequestLimitingError):
    """Timeout after {} seconds."""


# -----------------------------------------------------------------------------
class PoolManager:
    """
    Container for :py:class:`RequestSlotPool` objects
    """

    def __init__(self, redis, url_alimit):
        self.redis = redis

        self._url_alimit = url_alimit

        self._pool_map = {}

    def acquire(self, url, timeout=5, **kwargs):
        """
        :param str url: URL the request slot is acquired for
        """

        self._set_default_pool(url)
        self._pool_map[url].acquire(timeout=timeout, **kwargs)

    def release(self, url):
        """
        :param str URL: URL the request slot is released for
        """

        self._pool_map[url].release()

    def __getitem__(self, url):
        self._set_default_pool(url)
        return self._pool_map[url]

    def _set_default_pool(self, url):
        if url not in self._pool_map:
            self._pool_map[url] = RequestSlotPool(
                self.redis, url, self._url_alimit)


class RequestSlotPool:
    """
    Implementation of a request slot pool object. The implementation is based
    on `Redis <https://redis.io/>`_'.
    """

    LOGGER = 'flask.app.limit.pool'

    class _RequestSlot:
        """
        Implementation of a request slot object.

        .. note:: Currently, a :py:class:`RequestSlotPool.RequestSlot` cannot
            time out.
        """

        def __init__(self, key, poll_interval=0.05):
            """
            :param float poll_interval: Polling interval in seconds when
                acquiring a request slot.
            """

            self.key = key

            self._poll_interval = poll_interval

        def acquire(self, redis, maxsize, timeout=-1):
            """
            :param int maxsize: Maximum number of slots allowed
            :param float timeout: Timeout in seconds. Disabled if set to -1.
            """

            def client_side_incr(pipe):
                current_value = int(pipe.get(self.key))
                if maxsize is None or maxsize > current_value:
                    next_value = current_value + 1
                    pipe.multi()
                    pipe.set(self.key, next_value)


            if maxsize != 0:

                deadline = time.time() + timeout
                def check_if_timed_out(timeout):
                    if timeout == -1:
                        return False
                    else:
                        return time.time() > deadline

                timeout_passed = False

                while True:

                    resp = redis.transaction(client_side_incr, self.key)
                    if resp and resp[-1]:
                        break

                    if check_if_timed_out(timeout):
                        timeout_passed = True
                        break

                    time.sleep(self._poll_interval)

                return not timeout_passed

            else:
                return False

        def release(self, redis, maxsize):
            """
            Release the slot.
            """

            if maxsize != 0:
                redis.decr(self.key)

    def __init__(self, redis, url, url_alimit,
                 key_prefix='request-semaphore:'):
        """
        :param str url: URL the pool is mapped to
        :param str url_alimit: URL to the configuration service providing
            access limit information.
        """
        self.logger = logging.getLogger(self.LOGGER)

        self.redis = redis
        self.url = url
        self.url_alimit = url_alimit
        self.key = key_prefix + url

        service = _extract_service_from_fdsnws_url(self.url)
        maxsize = self._get_maxsize({'service': service})
        # self._maxsize = None if maxsize == -1 else maxsize
        self._maxsize = 5

        self._init_redis(self.key)

        self._slots = []

    def acquire(self, timeout=-1, **kwargs):

        slot = self._RequestSlot(self.key, **kwargs)

        acquired = slot.acquire(self.redis, self._maxsize, timeout=timeout)
        if acquired:
            self._slots.append(slot)
        else:
            self.logger.warning(
                'No slots available, discarding connection: '
                '{!r}'.format(self.url))

            return False

        self.logger.debug(
            'Acquired slot {!r} for connection: {!r}'.format(slot, self.url))

        return True

    def release(self):
        """
        Release a slot.
        """

        try:
            slot = self._slots.pop()
        except IndexError:
            pass
        else:
            slot.release(self.redis, self._maxsize)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()

    def _init_redis(self, key):
        self.redis.set(key, 0)

    def _get_maxsize(self, query_params, default_maxsize=None):
        """
        Fetch the access limit configuration for ``url``

        :param dict query_params: Query parameters send to the access limiting
            service.
        :param int default_maxsize: Default access limit returned in case of
            errors. Unlimited access is granted if ``default_maxsize=-1``.
        """

        if hasattr(self, '_maxsize'):
            return self._maxsize

        maxsize = default_maxsize

        try:
            resp = requests.get(self.url_alimit, params=query_params)
            resp.raise_for_status()
        except requests.exceptions.RequestException as err:
            self.logger.warning(
                'Access limit service unreachable: {!r}'.format(err))
            return maxsize

        if resp.status_code != 200:
            self.logger.warning(
                "Invalid response: url={!r}, resp={!r}".format(resp.url, resp))
            return maxsize

        maxsize = default_maxsize
        for line in resp.text.split('\n'):

            line = line.rstrip()

            if line:
                _line = line.split(' ')

                if _line and _line[0] == self.url:
                    try:
                        maxsize = int(_line[1])

                        if maxsize < -1:
                            raise ValueError(maxsize)

                    except (IndexError, ValueError) as err:
                        self.logger.warning(
                            'Invalid access limit configuration '
                            '(url={!r}): {}'.format(self.url, err))
                    finally:
                        break

        else:
            self.logger.warning(
                'Missing access limit configuration for URL: {!r}'.format(
                    self.url))

        return maxsize

    def __str__(self):
        return ', '.join(['url={!r}'.format(self.url),
                          'maxsize={!r}'.format(
                              self._maxsize if hasattr(self, '_maxsize') else
                              None)])

    def __repr__(self):
        return '<{}: {}>'.format(type(self).__name__, self)
