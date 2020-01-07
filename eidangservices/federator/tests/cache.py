# -*- coding: utf-8 -*-
"""
Cache related test facilities.
"""

import os
import shutil
import tempfile
import time
import unittest

from eidangservices.federator.server.cache import FileSystemCache


class FileSystemCacheTestCase(unittest.TestCase):

    def setUp(self):
        self.cache_dir = os.path.join(tempfile.gettempdir(), '__fed_fs_cache')

    def tearDown(self):
        try:
            shutil.rmtree(self.cache_dir)
        except OSError:
            pass

    def test_init(self):
        fs_cache = FileSystemCache(cache_dir=self.cache_dir)

        self.assertEqual(fs_cache._file_count, 0)

    def test_set_get_delete(self):
        fs_cache = FileSystemCache(cache_dir=self.cache_dir)
        fs_cache.set('key0', 'bar')
        fs_cache.set('key1', 'hello world')

        self.assertEqual(fs_cache._file_count, 2)

        self.assertEqual(fs_cache.get('key0'), b'bar')
        self.assertEqual(fs_cache.get('key1'), b'hello world')

        fs_cache.delete('key1')

        self.assertEqual(fs_cache._file_count, 1)
        self.assertEqual(fs_cache.get('key0'), b'bar')

    def test_threshold(self):
        fs_cache = FileSystemCache(cache_dir=self.cache_dir, threshold=4)

        # XXX(damb): Removal is firstly initiated if the cache contains
        # (threshold + 2) files.
        fs_cache.set('key0', 'baz')
        fs_cache.set('key1', 'bar')
        fs_cache.set('key2', 'hello')
        fs_cache.set('key3', 'world')
        fs_cache.set('key4', 'foo')
        fs_cache.set('key5', 'foobar')

        self.assertEqual(fs_cache._file_count, 4)

    def test_timeout(self):
        fs_cache = FileSystemCache(cache_dir=self.cache_dir, default_timeout=1)
        fs_cache.set('key0', 'foo')

        time.sleep(1)

        self.assertEqual(fs_cache.get('key0'), None)
        self.assertEqual(fs_cache._file_count, 1)
