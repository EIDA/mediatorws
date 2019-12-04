# -*- coding: utf-8 -*-

from eidangservices.federator.server import response_code_stats


class ResponseCodeStatsMixin:
    """
    Adds the :py:attr:`response_code_stats` property to a object.
    """

    @property
    def response_code_stats(self):
        return response_code_stats

    def get_stats_error_ratio(self, url):
        """
        Return the error ratio of a response code time series referenced by
        ``url``.

        :param str url: URL indicating the response code time series to be
            garbage collected

        :returns: Error ratio in percent
        :rtype: float
        """
        return 100 * self.response_code_stats.get_error_ratio(url)

    def update_stats(self, url, code):
        """
        Add ``code`` to the response code time series referenced by
        ``url``.

        :param str url: URL indicating the response code time series to be
            garbage collected
        :param int code: HTTP status code to be appended
        """
        self.response_code_stats.add(url, code)

    def gc_stats(self, url):
        """
        Garbage collect the response code time series referenced by ``url``.

        :param str url: URL indicating the response code time series to be
            garbage collected
        """
        self.response_code_stats.gc(url)
