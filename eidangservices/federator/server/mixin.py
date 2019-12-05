# -*- coding: utf-8 -*-

from eidangservices.federator.server import response_code_stats


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
