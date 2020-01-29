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
        self._pool_map.setdefault(
            url, RequestSlotPool(self.redis, url, self._url_alimit))


class RequestSlotPool:
    """
    Implementation of a request slot pool object. The implementation is based
    on `Redis <https://redis.io/>`_'.
    """

    LOGGER = 'flask.app.limit.pool'

    class RequestSlot:
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

            try_until = time.time() + timeout

            def client_side_incr(pipe):
                current_value = pipe.get(self.key)
                if maxsize == -1 or maxsize < current_value:
                    next_value = current_value + 1
                    pipe.multi()
                    pipe.set(self.key, next_value)

            def check_if_timed_out(timeout):
                if timeout == -1:
                    return True
                else:
                    return time.time() < try_until

            timeout_passed = False
            while True:

                resp = redis.transaction(client_side_incr, self.key)
                if len(resp) == 2 and all(resp):
                    break

                if check_if_timed_out(timeout):
                    timeout_passed = True
                    break

                time.sleep(self._poll_interval)

            return not timeout_passed

        def release(self, redis):
            """
            Release the slot.
            """

            redis.decr(self.key)

    def __init__(self, redis, url, url_alimit, key_prefix='request-slot:'):
        """
        :param str url: URL the pool is mapped to
        :param str url_alimit: URL to the configuration service providing
            access limit information.
        """
        self.redis = redis
        self.url = url
        self.url_alimit = url_alimit
        self.key = key_prefix + url

        service = _extract_service_from_fdsnws_url(self.url)
        self._maxsize = self._get_alimit({'service': service})

        if self._maxsize > -1:
            self._init_redis(self.key)

        self._pool = []

        self.logger = logging.getLogger(self.LOGGER)

    def acquire(self, timeout=-1, **kwargs):

        slot = self.RequestSlot(self.url, **kwargs)

        if (self._maxsize == -1 or
                slot.acquire(self.redis, self._maxsize, timeout=timeout)):
            self._pool.append(slot)
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
        Release a slot from a pool.
        """

        if not self._pool:
            raise RuntimeError('Missing slot, releasing not possible.')

        slot = self._pool.pop()
        slot.release(self.redis)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()

    def _init_redis(self, key):
        self.redis.set(key, 0)

    def _get_alimit(self, query_params, default_alimit=-1):
        """
        Fetch the access limit configuration for ``url``

        :param dict query_params: Query parameters send to the access limiting
            service.
        :param int default_alimit: Default access limit returned in case of
            errors. Unlimited access is granted if ``default_alimit=-1``.
        """

        if self._alimit:
            return self._alimit

        alimit = default_alimit

        try:
            resp = requests.get(self.url_alimit, params=query_params)
            resp.raise_for_status()
        except requests.exceptions.RequestException as err:
            self.logger.warning(
                'Access limit service unreachable: {!r}'.format(err))
            return alimit

        if resp.status != 200:
            self.logger.warning(
                "Invalid response: url={!r}, resp={!r}".format(resp.url, resp))
            return alimit

        alimit = default_alimit
        for line in resp.text.split('\n'):

            line = line.rstrip()

            if line:
                _line = line.split(' ')

                if _line and _line[0] == self.url:
                    try:
                        alimit = int(_line[1])
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

        return alimit
