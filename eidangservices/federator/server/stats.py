# -*- coding: utf-8 -*-
"""
Facilities related with statistics.
"""

import abc
import os
import time
import uuid

from copy import deepcopy
from urllib.parse import urlsplit

from eidangservices.utils.error import ErrorWithTraceback


class StatsError(ErrorWithTraceback):
    """Base Stats error ({})."""


class RedisCollection(metaclass=abc.ABCMeta):
    """
    Abstract class providing backend functionality for Redis collections.
    """

    ENCODING = 'utf-8'

    def __init__(self, redis, key=None, **kwargs):
        self.redis = redis

        self.key = key or self._create_key()

    def _transaction(self, fn, *extra_keys, **kwargs):
        """
        Helper simplifying code within a watched transaction.

        Takes *fn*, function treated as a transaction. Returns whatever
        *fn* returns. :code:`self.key` is watched. *fn* takes *pipe* as the
        only argument.

        :param fn: Closure treated as a transaction.
        :type fn: function *fn(pipe)*
        :param extra_keys: Optional list of additional keys to watch.
        :type extra_keys: list
        :rtype: whatever *fn* returns
        """
        results = []

        def trans(pipe):
            results.append(fn(pipe))

        self.redis.transaction(trans, self.key, *extra_keys, **kwargs)
        return results[0]

    @abc.abstractmethod
    def _data(self, pipe=None, **kwargs):
        """
        Helper for getting the time series data within a transaction.

        :param pipe: Redis pipe in case creation is performed as a part
                     of transaction.
        :type pipe: :py:class:`redis.client.StrictPipeline` or
                    :py:class:`redis.client.StrictRedis`
        """

    def _clear(self, pipe=None):
        """
        Helper for clear operations.

        :param pipe: Redis pipe in case creation is performed as a part
                     of transaction.
        :type pipe: :py:class:`redis.client.StrictPipeline` or
                    :py:class:`redis.client.StrictRedis`
        """

        redis = pipe or self.redis
        redis.delete(self.key)

    @staticmethod
    def _create_key():
        """
        Creates a random Redis key for storing this collection's data.

        :rtype: string

        .. note::
            :py:func:`uuid.uuid4` is used. If you are not satisfied with its
            `collision probability
            <http://stackoverflow.com/a/786541/325365>`_, make your own
            implementation by subclassing and overriding this method.
        """
        return uuid.uuid4().hex


class ResponseCodeTimeSeries(RedisCollection):
    """
    Distributed collection implementing a response code time series. The
    timeseries is implemented based on Redis' `sorted set
    <https://redis.io/topics/data-types>`_ following the pattern described at
    `redislabs.com
    <https://redislabs.com/redis-best-practices/time-series/sorted-set-time-series/>`_.

    ..warning::
        The ``window_size`` of the collection can't be enforced when multiple
        processes are accessing its corresponding Redis collection.
    """

    KEY_DELIMITER = b':'
    _DEFAULT_TTL = 3600  # seconds
    _DEFAULT_WINDOW_SIZE = 10000

    ERROR_CODES = (500, 503)

    def __init__(self, redis, key=None, **kwargs):
        super().__init__(redis, key, **kwargs)

        self.ttl, self.window_size = self._validate_ctor_args(
            kwargs.get('ttl', self._DEFAULT_TTL),
            kwargs.get('window_size', self._DEFAULT_WINDOW_SIZE))

    @property
    def error_ratio(self):
        """
        Returns the error ratio of the response code time series. Values are
        between ``0`` (no errors) and ``1`` (errors only).
        """
        data = self._data(ttl=self.ttl)
        num_errors = len(
            [code for code, t in data if int(code) in self.ERROR_CODES])

        if not data:
            return 0

        return num_errors / len(data)

    def __len__(self, pipe=None, **kwargs):
        return len(self._data(pipe, **kwargs))

    def __iter__(self, pipe=None):
        return iter(self._data(pipe=pipe, ttl=self.ttl))

    def gc(self, pipe=None, **kwargs):
        """
        Discard deprecated values from the time series.
        """
        redis = pipe or self.redis

        ttl = kwargs.get('ttl') or self.ttl
        thres = time.time() - ttl

        redis.zremrangebyscore(self.key, '-inf', thres)

    def clear(self, pipe=None, **kwargs):
        self._clear(pipe=pipe)

    def append(self, value):
        """
        Append *value* to the time series.

        :param int value: Response code to be appended
        """
        hash(value)

        def append_trans(pipe):
            self._append_helper(value, pipe)

        self._transaction(append_trans, watch_delay=0.1)

    def _append_helper(self, value, pipe, **kwargs):

        score = time.time()
        member = self._serialize(value, score)

        pipe.zadd(self.key, {member: score})

        num_items = pipe.zcount(self.key, '-inf', '+inf')

        # check window size restriction
        if (self.window_size is None) or (num_items <= self.window_size):
            return

        pipe.zremrangebyrank(self.key, 0, 0)

    def _data(self, pipe=None, **kwargs):
        """
        Helper for getting the time series data within a transaction.

        :param pipe: Redis pipe in case creation is performed as a part
                     of transaction.
        :type pipe: :py:class:`redis.client.StrictPipeline` or
                    :py:class:`redis.client.StrictRedis`
        """
        redis = pipe or self.redis
        ttl = kwargs.get('ttl') or self.ttl

        now = time.time()
        items = redis.zrevrangebyscore(self.key, now, now - ttl,
                                       withscores=True)

        if not items:
            return []

        return [(self._deserialize(member), score)
                for member, score in items]

    def _deserialize(self, value, **kwargs):
        retval = value.split(self.KEY_DELIMITER)[0]
        return retval.decode(self.ENCODING)

    def _serialize(self, value, score, **kwargs):
        return (str(value).encode(self.ENCODING) +
                self.KEY_DELIMITER +
                str(score).encode(self.ENCODING) +
                # add 8 random bytes
                os.urandom(8))

    @staticmethod
    def _validate_ctor_args(ttl, window_size):
        if ttl < 0 or window_size < 0:
            raise ValueError('Negative value specified.')
        return ttl, window_size


class ResponseCodeStats:
    """
    Container for datacenter response code statistics handling.
    """

    DEFAULT_PREFIX = b'stats:response-codes'

    def __init__(self, redis, prefix=None, **kwargs):

        self.redis = redis
        self.kwargs_series = kwargs

        self._prefix = prefix or self.DEFAULT_PREFIX
        if isinstance(self._prefix, str):
            self._prefix = self._prefix.encode(RedisCollection.ENCODING)

        self._map = {}

    def add(self, url, code, **kwargs):
        """
        Add ``code`` to a response code time series specified by ``url``.
        """
        kwargs_series = deepcopy(self.kwargs_series)
        kwargs_series.update(kwargs)

        key = self._create_key_from_url(url, prefix=self._prefix)

        if key not in self._map:
            self._map[key] = ResponseCodeTimeSeries(
                redis=self.redis, key=key, **kwargs_series)

        self._map[key].append(code)

    def gc(self, url, lazy_load=True):
        """
        Discard deprecated values from a response code time series specified by
        ``url``.

        :param bool lazy_load: Lazily load the response code time series to be
            garbage collected
        """
        key = self._create_key_from_url(url, prefix=self._prefix)

        if lazy_load and key not in self._map:
            # lazy loading
            self._map[key] = ResponseCodeTimeSeries(
                redis=self.redis, key=key, **self.kwargs_series)

        self._map[key].gc()

    def clear(self, url):
        key = self._create_key_from_url(url, prefix=self._prefix)

        try:
            self._map[key].clear()
        except KeyError as err:
            raise StatsError(err)

    def get_error_ratio(self, url, lazy_load=True):
        """
        Return the error ratio of a response code time series specified by
        ``url``.

        :param bool lazy_load: Lazily load the response code time series the
            error ratio is computed from
        """

        key = self._create_key_from_url(url, prefix=self._prefix)

        if lazy_load and key not in self._map:
            # lazy loading
            self._map[key] = ResponseCodeTimeSeries(
                redis=self.redis, key=key, **self.kwargs_series)

        return self._map[key].error_ratio

    def __contains__(self, url):
        return self._create_key_from_url(url) in self._map

    def __getitem__(self, key):
        return self._map[key]

    @staticmethod
    def _create_key_from_url(url, prefix=None):
        delimiter = ResponseCodeTimeSeries.KEY_DELIMITER

        if isinstance(url, str):
            url = url.encode(RedisCollection.ENCODING)

        split_result = urlsplit(url)
        args = [split_result.path, split_result.netloc]

        if prefix:
            args.insert(0, prefix)

        return delimiter.join(args)
