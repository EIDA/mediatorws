# -*- coding: utf-8 -*-
"""
Statistics related test facilities.
"""

import time
import unittest

import redis

from eidangservices.federator.server.stats import ResponseCodeTimeSeries


class RedisTestCase(unittest.TestCase):

    db = 15

    def setUp(self):
        # requires a Redis instance serving at redis://localhost:6379/
        self.redis = redis.StrictRedis(db=self.db)

        if self.redis.dbsize():
            raise EnvironmentError('Redis database number %d is not empty, '
                                   'tests could harm your data.' % self.db)

    def tearDown(self):
        self.redis.flushdb()


class ResponseCodeTimeSeriesTestCase(RedisTestCase):

    def create_timeseries(self, *args, **kwargs):
        return ResponseCodeTimeSeries(self.redis, *args, **kwargs)

    def test_init(self):
        ts = self.create_timeseries()

        self.assertEqual(len(ts), 0)

    def test_append(self):
        ts = self.create_timeseries()

        status_codes = [200, 500, 503, 204]
        for c in status_codes:
            ts.append(c)

        self.assertEqual([c for c, score in ts],
                         [str(c) for c in reversed(status_codes)])

    def test_ttl(self):
        ttl = 0.1
        ts = self.create_timeseries(ttl=ttl)

        status_codes = [200, 500, 503, 204]
        for c in status_codes:
            ts.append(c)

        time.sleep(ttl)
        self.assertEqual([c for c, score in ts], [])

    def test_window_size(self):
        size = 3
        ts = self.create_timeseries(window_size=size)

        status_codes = [200, 500, 503, 204]
        for c in status_codes:
            ts.append(c)

        self.assertEqual([c for c, score in ts],
                         [str(c) for c in reversed(status_codes[1:])])

        self.assertEqual(len(self.redis.zrange(ts.key, 0, -1)), 3)

    def test_gc(self):
        ttl = 0.4
        ts = self.create_timeseries(ttl=ttl)

        status_codes = [200, 500, 503, 204]
        for c in status_codes:
            ts.append(c)
            time.sleep(ttl / len(status_codes))

        ts.gc()
        self.assertEqual(len(self.redis.zrange(ts.key, 0, -1)), 3)

    def test_error_ratio(self):
        ts = self.create_timeseries()

        status_codes = [200, 500, 503, 204]
        for c in status_codes:
            ts.append(c)

        self.assertEqual(ts.error_ratio, 0.5)


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
