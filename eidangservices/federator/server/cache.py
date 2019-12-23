# -*- coding: utf-8 -*-
"""
Caching facilities

The module provides a similar functionality as implemented by `pallets/cachelib
<https://github.com/pallets/cachelib>`_ and `sh4nks/flask-caching
<https://github.com/sh4nks/flask-caching>`_.
"""

import errno
import gzip
import hashlib
import os
import redis
import string
import tempfile

from time import time

from eidangservices.utils.error import ErrorWithTraceback

# Used to remove control characters and whitespace from cache keys.
valid_chars = set(string.ascii_letters + string.digits + "_.")
delchars = "".join(c for c in map(chr, range(256)) if c not in valid_chars)
null_control = (dict((k, None) for k in delchars),)


# -----------------------------------------------------------------------------
class CacheError(ErrorWithTraceback):
    """Base cache error ({})."""


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
        return gzip.compress(value.encode('utf-8'))

    def _deserialize(self, value):
        """
        The complementary method of :py:meth:`_serialize`. Can be called with
        ``None``.
        """

        if value is None:
            return None

        return gzip.decompress(value)


class FileSystemCache(CachingBackend):
    """
    Implementation of a file system caching backend. The implementation is
    based on `pallets/cachelib <https://github.com/pallets/cachelib>`_.

    Make absolutely sure that nobody but this cache stores files there or
    otherwise the cache will randomly delete files therein.
    """

    # used for temporary files by the FileSystemCache
    _fs_transaction_suffix = '.__fed_cache'
    # keep amount of files in a cache element
    _fs_count_file = '__fed_cache_count'

    def __init__(self, cache_dir, threshold=10000, default_timeout=300,
                 mode=0o600):
        super().__init__(default_timeout)

        self._path = cache_dir
        self._threshold = threshold
        self._mode = mode

        try:
            os.makedirs(self._path)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise CacheError(err)

        # If there are many files and a zero threshold,
        # the list_dir can slow initialisation massively
        if self._threshold != 0:
            self._update_count(value=len(self._list_dir()))

    @property
    def _file_count(self):
        count = self.get(self._fs_count_file) or b'0'
        return int(count.decode('utf-8'))

    def _update_count(self, delta=None, value=None):
        # If we have no threshold, don't count files
        if self._threshold == 0:
            return

        if delta:
            new_count = self._file_count + delta
        else:
            new_count = value or 0
        self.set(self._fs_count_file, str(new_count), mgmt_element=True)

    def _normalize_timeout(self, timeout):
        if timeout is None:
            timeout = self._default_timeout

        if timeout != 0:
            timeout = time() + timeout

        return int(timeout)

    def _list_dir(self):
        """
        Return a list of (fully qualified) cache filenames.
        """
        mgmt_files = [self._get_filename(name).split('/')[-1]
                      for name in (self._fs_count_file,)]
        return [os.path.join(self._path, fn) for fn in os.listdir(self._path)
                if not fn.endswith(self._fs_transaction_suffix) and
                fn not in mgmt_files]

    def _get_filename(self, key):
        if isinstance(key, str):
            key = key.encode('utf-8')  # XXX unicode review
        hash = hashlib.md5(key).hexdigest()
        return os.path.join(self._path, hash)

    def _prune(self):
        if self._threshold == 0 or not self._file_count > self._threshold:
            return

        entries = self._list_dir()
        now = time()
        for idx, fname in enumerate(entries):
            try:
                remove = False
                with open(fname, 'rb') as ifd:
                    expires = int(ifd.readline().rstrip())
                remove = (expires != 0 and expires <= now) or idx % 3 == 0

                if remove:
                    os.remove(fname)
            except (IOError, OSError, ValueError):
                pass

        self._update_count(value=len(self._list_dir()))

    def get(self, key):
        filename = self._get_filename(key)
        try:
            with open(filename, 'rb') as ifd:
                t = int(ifd.readline().rstrip())
                if t == 0 or t >= time():
                    return self._deserialize(ifd.read())
                else:
                    os.remove(filename)
                    return None
        except (IOError, OSError):
            return None

    def delete(self, key, mgmt_element=False):
        try:
            os.remove(self._get_filename(key))
        except (IOError, OSError):
            return False
        else:
            # Management elements should not count towards threshold
            if not mgmt_element:
                self._update_count(delta=-1)
            return True

    def set(self, key, value, timeout=None, mgmt_element=False):
        # Management elements have no timeout
        if mgmt_element:
            timeout = 0

        # Don't prune on management element update, to avoid loop
        else:
            self._prune()

        timeout = self._normalize_timeout(timeout)
        filename = self._get_filename(key)
        try:
            fd, tmp = tempfile.mkstemp(suffix=self._fs_transaction_suffix,
                                       dir=self._path)
            with os.fdopen(fd, 'wb') as ofd:
                ofd.write("{}\n".format(timeout).encode('utf-8'))
                ofd.write(self._serialize(value))

            os.rename(tmp, filename)
            os.chmod(filename, self._mode)
        except (IOError, OSError):
            return False
        else:
            # Management elements should not count towards threshold
            if not mgmt_element:
                self._update_count(delta=1)
            return True

    def __contains__(self, key):
        filename = self._get_filename(key)
        try:
            with open(filename, 'rb') as ifd:
                t = int(ifd.readline().rstrip())
                if t == 0 or t >= time():
                    return True
                else:
                    os.remove(filename)
                    return False
        except (IOError, OSError, ValueError):
            return False

    def _serialize(self, value):
        return gzip.compress(value.encode('utf-8'))

    def _deserialize(self, value):
        """
        The complementary method of :py:meth:`_serialize`.
        """

        return gzip.decompress(value)


# -----------------------------------------------------------------------------
class Cache:
    """
    Generic API for cache objects.
    """
    CACHE_MAP = {
        'null': NullCache,
        'redis': RedisCache,
        'fs': FileSystemCache,
    }

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
        cache_obj = self.CACHE_MAP[config['CACHE_TYPE']]
        self._cache = cache_obj(**config['CACHE_KWARGS'])

    def get(self, *args, **kwargs):
        return self._cache.get(*args, **kwargs)

    def set(self, *args, **kwargs):
        return self._cache.set(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._cache.delete(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self._cache.__contains__(*args, **kwargs)
