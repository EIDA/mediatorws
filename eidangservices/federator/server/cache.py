# -*- coding: utf-8 -*-
"""
Caching facilities

The module provides a similar functionality as implemented by `pallets/cachelib
<https://github.com/pallets/cachelib>`_ and `sh4nks/flask-caching
<https://github.com/sh4nks/flask-caching>`_.
"""

import redis
import string

from eidangservices.utils.error import ErrorWithTraceback


# Used to remove control characters and whitespace from cache keys.
valid_chars = set(string.ascii_letters + string.digits + "_.")
delchars = "".join(c for c in map(chr, range(256)) if c not in valid_chars)
null_control = (dict((k, None) for k in delchars),)


# -----------------------------------------------------------------------------
class CacheError(ErrorWithTraceback):
    """Base cache error ({})."""


class Cache:
    """
    Generic API for cache objects.
    """

    def __init__(self, config=None):

        if not isinstance(config, (dict, type(None))):
            raise TypeError("Invalid type for 'config'.")

        self._config = config

        if config:
            self.init_cache(config=config)

    def init_cache(self, config={}):

        config.setdefault('CACHE_TYPE', 'null')
        config.setdefault('CACHE_KWARGS', {})

        self._set_cache(config)

    def _set_cache(self, config):

        cache_map = {
            'null': NullCache,
            'redis': RedisCache,
        }

        cache_obj = cache_map[config['CACHE_TYPE']]
        self._cache = cache_obj(**config['CACHE_KWARGS'])

    def get(self, *args, **kwargs):
        return self._cache.get(*args, **kwargs)

    def set(self, *args, **kwargs):
        return self._cache.set(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._cache.delete(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self._cache.__contains__(*args, **kwargs)


# -----------------------------------------------------------------------------
class CachingBackend:
    """
    Base class for cache backend implementations.
    """

    def __init__(self, default_timeout=300, **kwargs):
        """
        :param default_timeout: The default timeout (in seconds) that is used
        if no timeout is specified in :py:meth:`set`. A timeout of 0 indicates
        that the cache never expires.
        """
        self._default_timeout = default_timeout

    def get(self, key):
        """
        Look up ``key`` in the cache and return the value for it.

        :param key: The key to be looked up
        :returns: The value if it exists and is readable, else ``None``.
        """

        return None

    def delete(self, key):
        """
        Delete ``key`` from the cache.

        :param key: The key to delete
        :returns: Whether the key existed and has been deleted.
        :rtype: boolean
        """

        return True

    def set(self, key, value, timeout=None):
        """
        Add a new ``key: value`` to the cache. The value is overwritten in case
        the ``key`` is already cached.

        :param key: The key to be set
        :param value: The value to be cached
        :param timeout: The cache timeout for the key in seconds. If not
            specified the default timeout is used. A timeout of 0 indicates
            that the cache never expires.

        :returns: ``True`` if the key has been updated and ``False`` for
            backend errors.
        rtype: boolean
        """

        return True

    def __contains__(self, key):
        """
        Validate if a key exists in the cache without returning it. The data is
        neither loaded nor deserialized.

        :param key: Key to validate
        """

        raise NotImplementedError


class NullCache(CachingBackend):
    """
    A cache that doesn't cache.
    """

    def __contains__(self, key):
        return False


class RedisCache(CachingBackend):
    """
    Implementation of a `Redis <https://redis.io/>`_ caching backend.
    """

    def __init__(self, url, default_timeout=300, key_prefix=None, **kwargs):
        super().__init__(default_timeout)

        self.redis = redis.Redis.from_url(url)
        self.key_prefix = key_prefix or ""

    def _create_key_prefix(self):
        if isinstance(self.key_prefix, str):
            return self.key_prefix
        return self.key_prefix()

    def _normalize_timeout(self, timeout):
        if timeout is None:
            return self._default_timeout
        return timeout

    def get(self, key):
        return self._deserialize(
            self.redis.get(self._create_key_prefix() + key))

    def delete(self, key):
        return self.redis.delete(self._create_key_prefix() + key)

    def set(self, key, value, timeout=None):
        key = self._create_key_prefix() + key
        value = self._serialize(value)

        timeout = self._normalize_timeout(timeout)

        if timeout == 0:
            return self.redis.set(name=key, value=value)
        else:
            return self.redis.setex(
                name=key, value=value, time=timeout)

    def __contains__(self, key):
        return self.redis.exists(self._create_key_prefix() + key)

    def _serialize(self, value):
        return value

    def _deserialize(self, value):
        return value
