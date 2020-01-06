# -*- coding: utf-8 -*-

import base64
import hashlib

from eidangservices.federator.server import cache, response_code_stats
from eidangservices.federator.server.cache import null_control


class ClientRetryBudgetMixin:
    """
    Adds the :py:attr:`stats_retry_budget_client` property to a object.
    """

    @property
    def stats_retry_budget_client(self):
        return response_code_stats

    def get_cretry_budget_error_ratio(self, url):
        """
        Return the error ratio of a response code time series referenced by
        ``url``.

        :param str url: URL indicating the response code time series to be
            garbage collected

        :returns: Error ratio in percent
        :rtype: float
        """
        return 100 * self.stats_retry_budget_client.get_error_ratio(url)

    def update_cretry_budget(self, url, code):
        """
        Add ``code`` to the response code time series referenced by
        ``url``.

        :param str url: URL indicating the response code time series to be
            garbage collected
        :param int code: HTTP status code to be appended
        """
        self.stats_retry_budget_client.add(url, code)

    def gc_cretry_budget(self, url):
        """
        Garbage collect the response code time series referenced by ``url``.

        :param str url: URL indicating the response code time series to be
            garbage collected
        """
        self.stats_retry_budget_client.gc(url)


class CachingMixin:
    """
    Adds caching facilities to a
    :py:class:`~eidangservices.federator.server.process.RequestProcessor`.
    """

    @property
    def cache(self):
        return cache

    def make_cache_key(self, query_params, stream_epochs, key_prefix=None,
                       sort_args=True, hash_method=hashlib.md5,
                       exclude_params=('nodata', 'service',)):
        """
        Create a cache key from ``query_params`` and ``stream_epochs``.

        :param query_params: Mapping with requested query parameters
        :param stream_epochs: List of
            :py:class:`~eidangservices.utils.sncl.StreamEpoch` objects.
        :param key_prefix: Caching key prefix
        :param bool sort_args: Sort caching key components before creating the
            key.
        :param hash_method: Hash method used for key generation. Default is
            ``hashlib.md5``.
        :param exclude_params: Keys to be excluded from the ``query_params``
            mapping while generating the key.
        :type exclude_params: tuple of str
        """
        if sort_args:
            query_params = [(k, v) for k, v in query_params.items()
                            if k not in exclude_params]
            query_params = sorted(query_params)
            stream_epochs = sorted(stream_epochs)

        updated = "{0}{1}{2}".format(
            key_prefix or '', query_params, stream_epochs)
        updated.translate(*null_control)

        cache_key = hash_method()
        cache_key.update(updated.encode("utf-8"))
        cache_key = base64.b64encode(cache_key.digest())[:16]
        cache_key = cache_key.decode("utf-8")

        return cache_key

    def cache_stream(self, generator, cache_key, timeout=None):
        """
        Caching generator wrapper for ``generator``.
        """

        stream_buffer = []
        try:
            for chunk in generator:
                stream_buffer.append(chunk)
                yield chunk
        except GeneratorExit:
            pass
        else:
            # cache streamed response
            try:
                cache.set(
                    cache_key, "".join(stream_buffer), timeout=timeout)
            except Exception as err:
                raise err
                # TODO TODO TODO
                # Report warning
                pass

    def get_cache(self, cache_key):
        """
        Lookup ``cache_key`` from the cache.
        """

        try:
            retval = cache.get(cache_key)
            found = True

            # If the value returned by cache.get() is None, it might be
            # because the key is not found in the cache or because the
            # cached value is actually None
            if retval is None:
                found = cache_key in cache
        except Exception:
            found = False
            return None, found
        else:
            return retval, found
