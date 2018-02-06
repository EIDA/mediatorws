# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <route.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-federator).
# 
# eida-federator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version.
#
# eida-federator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----
# 
# Copyright (c) Daniel Armbruster (ETH), Fabian Euchner (ETH)
#
# REVISION AND CHANGES
# 2017/11/23        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Federator routing test facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import *

import functools
import io
import logging
import sys
import time
import unittest
#import warnings

import multiprocessing as mp

from queue import Empty

from eidangservices import settings
from eidangservices.federator.server import combine, misc, route

from future import standard_library
standard_library.install_aliases()

import urllib.request
import urllib.parse

try:
    # Python 2.x
    import mock
except ImportError:
    # Python 3.x
    import unittest.mock as mock


def _acquire_lock(url, lock_for=1):
    """
    try to acquire a lock
    :param str url: url the lock is created for
    :param lock_for: time in seconds the lock is acquired for
    """
    url_to_lock = urllib.parse.urlsplit(url).geturl()
    url_lock = misc.URLConnectionLock(url_to_lock,
            path_lockdir=settings.PATH_LOCKDIR)

    gotten = url_lock.acquire(blocking=False)  
    time.sleep(lock_for)
    if gotten:
        url_lock.release()

# _acquire_lock ()

def _connect(func, queue):
    """
    :param func: function to be decorated
    :param :py:class:`multiprocessing.Queue` queue: queue exceptions will be
    stored for child exceptions
    """
    try: 
        func()  
    except Exception as e:
        queue.put(e)

# _catch_exception(func, queue)


# -----------------------------------------------------------------------------
class ConnectionTestCase(unittest.TestCase):

    def setUp(self):
        self.url = b'https://www.ethz.ch/'
        self.timeout = settings.EIDA_FEDERATOR_DEFAULT_ROUTING_TIMEOUT
        self.num_retries = 3
        self.retry_wait = 0.1
        self.logger = logging.getLogger()
        self.logger.addHandler(logging.NullHandler())

    def tearDown(self):
        self.url = None
        self.timeout = None
        self.num_retries = None
        self.retry_wait = None
        self.logger = None

    @mock.patch('urllib.request.urlopen')
    def test_status_code_200(self, mock_urlopen):
        mock_urlopen.return_value.getcode.return_value = 200
        fd = route.connect(mock_urlopen, self.url, None, self.timeout,
            self.num_retries, self.retry_wait, False) 
        self.assertEqual(fd.getcode(), 200)
        mock_urlopen.assert_called_with(self.url, None, self.timeout)

    # test_status_code_200 ()

    @mock.patch('urllib.request.urlopen')
    def test_status_code_204(self, mock_urlopen):
        mock_urlopen.return_value.getcode.return_value = 204
        fd = route.connect(mock_urlopen, self.url, None, self.timeout,
            self.num_retries, self.retry_wait, False) 
        self.assertEqual(fd.getcode(), 204)
        mock_urlopen.assert_called_with(self.url, None, self.timeout)

    # test_status_code_204 ()

    @mock.patch('urllib.request.urlopen')
    def test_status_code_ok(self, mock_urlopen):
        mock_urlopen.return_value.getcode.return_value = 305
        fd = route.connect(mock_urlopen, self.url, None, self.timeout,
            self.num_retries, self.retry_wait, False) 
        self.assertEqual(fd.getcode(), 305)
        mock_urlopen.assert_called_with(self.url, None, self.timeout)

    # test_status_code_ok ()

    @mock.patch('urllib.request.urlopen')
    def test_ok_retrying_but_locked(self, mock_urlopen):
        mock_urlopen.return_value.getcode.return_value = 305
        # TODO(damb): Python 3.5: ResourceWarning is raised even though the
        #warnings.simplefilter("ignore", ResourceWarning)
        connect = functools.partial(route.connect, mock_urlopen, self.url,
                None, self.timeout, self.num_retries, self.retry_wait, True)
        
        error_queue = mp.Queue()

        locking_process = mp.Process(target=_acquire_lock, args=(self.url,))
        connecting_process = mp.Process(target=_connect,
                args=(connect, error_queue))
        
        locking_process.start()
        connecting_process.start()

        connecting_process.join()
        locking_process.join()

        with self.assertRaises(route.Error):
            error = error_queue.get(timeout=1)
            raise error

    # test_ok_retrying_but_locked ()

    @mock.patch('urllib.request.urlopen')
    def test_http_error_4xx(self, mock_urlopen):
        status_code = 400
        mock_urlopen.return_value.getcode.return_value = status_code
        mock_urlopen.side_effect=urllib.request.HTTPError(self.url, status_code,
                'Mock-HTTPError', {}, None)
        with self.assertRaises(urllib.request.HTTPError) as e:
            fd = route.connect(mock_urlopen, self.url, None, self.timeout,
                self.num_retries, self.retry_wait, False)
        self.assertEqual(e.exception.code, status_code)
        mock_urlopen.assert_called_with(self.url, None, self.timeout)

    # test_http_error_4xx ()

    @mock.patch('urllib.request.urlopen')
    def test_http_error_5xx(self, mock_urlopen):
        status_code = 500
        mock_urlopen.return_value.getcode.return_value = status_code
        fd = route.connect(mock_urlopen, self.url, None, self.timeout,
            self.num_retries, self.retry_wait, False)
        self.assertEqual(fd.getcode(), status_code)
        mock_urlopen.assert_called_with(self.url, None, self.timeout)

    # test_http_error_5xx ()
    
    @mock.patch('urllib.request.urlopen')
    def test_url_error(self, mock_urlopen):
        status_code = 400
        mock_urlopen.return_value.getcode.return_value = status_code
        mock_urlopen.side_effect=urllib.request.URLError('Mock-URLError')
        with self.assertRaises(urllib.request.URLError) as e:
            fd = route.connect(mock_urlopen, self.url, None, self.timeout,
                self.num_retries, self.retry_wait, False)
        mock_urlopen.assert_called_with(self.url, None, self.timeout)

    # test_url_error ()

# class ConnectionTestCase


class DownloadTaskTestCase(unittest.TestCase):

    def setUp(self):
        # target url
        self.url = route.TargetURL(
            urllib.parse.urlparse('https://www.ethz.ch/'), [])
        self.stream_epochs = ['CH BASLT * * 2017-01-01 2017-01-02',
                              'CH DAVOX * * 2017-01-01 2017-01-02']
        self.combiner = combine.Combiner.create('text')
        self.timeout = settings.EIDA_FEDERATOR_DEFAULT_ROUTING_TIMEOUT
        self.num_retries = 3
        self.retry_wait = 5
        self.logger = logging.getLogger()
        self.logger.addHandler(logging.NullHandler())

    def tearDown(self):
        self.url = None
        self.stream_epochs = None
        self.combiner = None
        self.timeout = None
        self.num_retries = None
        self.retry_wait = None
        self.logger = None


    # XXX(damb): Test fails under Python2 since federator.server.route does not
    # use future yet. The test will be executed as soon as federator uses
    # requests instead of urllib
    @unittest.skipIf(sys.version_info < (3, 4),
            'federator.server.route does not use future yet')
    @mock.patch('eidangservices.federator.server.route.connect')
    def test_splitting(self, mock_connect):

        class HTTPResponseOK(io.BytesIO):
            """
            Utility urllib HTTP reponse object.
            """
        
            def getcode(self):
                return 200

            def info(self):
                return {'Content-Type': settings.MIMETYPE_TEXT}
        
        # class HTTPResponseOK

        reference_result = (
            '#Network|Station|Latitude|Longitude|Elevation|SiteName|'
            'StartTime|EndTime\n'
            'CH|BALST|47.33578|7.69498|863.0|Balsthal, SO|'
            '2000-06-16T00:00:00|\n'
            'CH|DAVOX|46.7805|9.87952|1830.0|Davos, Dischmatal, GR|'
            '2002-07-24T00:00:00|')


        download = route.DownloadTask(
            self.url,
            self.stream_epochs,
            combiner=self.combiner,
            timeout=self.timeout,
            num_retries=self.num_retries,
            retry_wait=self.retry_wait,
            retry_lock=False)

        first_connect_response = HTTPResponseOK(
            b'CH|BALST|47.33578|7.69498|863.0|Balsthal, '
            b'SO|2000-06-16T00:00:00|\n')
        second_connect_response = HTTPResponseOK(
            b'CH|DAVOX|46.7805|9.87952|1830.0|Davos, Dischmatal, '
            b'GR|2002-07-24T00:00:00|')
        side_effect = [urllib.request.HTTPError('Mock-URL', 413, 'Mock-Error',
                                                {}, None),
                       first_connect_response, second_connect_response]
        mock_connect.side_effect = side_effect

        download()
        ofd = io.BytesIO()
        self.combiner.dump(ofd)
        self.assertEqual(ofd.getvalue().decode('utf-8'), reference_result)
        # TODO(damb): check mock calls; will be implemented as soon as we are
        # using the requests library
        #print(mock_connect.mock_calls)


# class DownloadTaskTestCase

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <route.py> ----
