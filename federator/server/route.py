# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <route.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/10/19        V0.1    Daniel Armbruster; most of the code is based on
#                           https://github.com/GEOFON/fdsnws_scripts/blob/ \
#                               master/fdsnws_fetch.py
# =============================================================================
"""
Federator routing facility
"""

import datetime
import json
import logging
import socket
import struct
import sys
import threading
import time

from multiprocessing.pool import ThreadPool

from federator import settings
from federator.server.combine import Combiner

try:
    # Python 2.x
    import Queue
    import urllib2
    import urlparse
    import urllib
except ImportError:
    # Python 3.x
    import queue as Queue
    import urllib.request as urllib2
    import urllib.parse as urlparse
    import urllib.parse as urllib

try:
    # Python 3.2 and earlier
    from xml.etree import cElementTree as ET  # NOQA
except ImportError:
    from xml.etree import ElementTree as ET  # NOQA


# -----------------------------------------------------------------------------
# TODO(damb): Provide a generic error class.
class Error(Exception):
    pass

class AuthNotSupported(Exception):
    pass


class TargetURL(object):
    def __init__(self, url, qp):
        self.__scheme = url.scheme
        self.__netloc = url.netloc
        self.__path = url.path.rstrip('query').rstrip('/')
        self.__qp = dict(qp)

    def wadl(self):
        path = self.__path + '/application.wadl'
        return urlparse.urlunparse((self.__scheme,
                                    self.__netloc,
                                    path,
                                    '',
                                    '',
                                    ''))

    def auth(self):
        path = self.__path + '/auth'
        return urlparse.urlunparse(('https',
                                    self.__netloc,
                                    path,
                                    '',
                                    '',
                                    ''))

    def post(self):
        path = self.__path + '/query'
        return urlparse.urlunparse((self.__scheme,
                                    self.__netloc,
                                    path,
                                    '',
                                    '',
                                    ''))

    def post_qa(self):
        path = self.__path + '/queryauth'
        return urlparse.urlunparse((self.__scheme,
                                    self.__netloc,
                                    path,
                                    '',
                                    '',
                                    ''))

    def post_params(self):
        return self.__qp.items()

    def __str__(self):
        return '<TargetURL: scheme=%s, netloc=%s, path=%s, qp=%s>' % \
            (self.__scheme, self.__netloc, self.__path, self.__qp)

# class TargetURL


class RoutingURL(object):

    GET_PARAMS = set((
        'network',
        'station',
        'location',
        'channel',
        'starttime',
        'endtime',
        'service',
        'alternative'))

    POST_PARAMS = set(('service', 'alternative'))

    def __init__(self, url, qp):
        self.__scheme = url.scheme
        self.__netloc = url.netloc
        self.__path = url.path.rstrip('query').rstrip('/')
        self.__qp = dict(qp)

    def get(self):
        path = self.__path + '/query'
        qp = [(p, v) for (p, v) in self.__qp.items() if p in self.GET_PARAMS]
        qp.append(('format', 'post'))
        query = urllib.urlencode(qp)
        return urlparse.urlunparse((self.__scheme,
                                    self.__netloc,
                                    path,
                                    '',
                                    query,
                                    ''))

    def post(self):
        path = self.__path + '/query'
        return urlparse.urlunparse((self.__scheme,
                                    self.__netloc,
                                    path,
                                    '',
                                    '',
                                    ''))

    def post_params(self):
        qp = [(p, v) for (p, v) in self.__qp.items() if p in self.POST_PARAMS]
        qp.append(('format', 'post'))
        return qp

    def target_params(self):
        return [(p, v) for (p, v) in self.__qp.items() 
                if p not in self.GET_PARAMS]

    def __str__(self):
        return '<RoutingURL: scheme=%s, netloc=%s, path=%s, qp=%s>' % \
            (self.__scheme, self.__netloc, self.__path, self.__qp)

# class RoutingURL

# -----------------------------------------------------------------------------
msglock = threading.Lock()

def msg(s, verbose=True):
    if verbose:
        with msglock:
            sys.stderr.write(s + '\n')
            sys.stderr.flush()

def retry(urlopen, url, data, timeout, count, wait, verbose=True):
    """connect/open a URL and retry in case the URL is not reachable"""
    # TODO(damb): verbose is deprecated: logging in use.

    logger = logging.getLogger('federator.connect')
    n = 0

    while True:
        if n >= count:
            return urlopen(url, data, timeout)

        try:
            n += 1

            fd = urlopen(url, data, timeout)

            if fd.getcode() == 200 or fd.getcode() == 204:
                return fd

            logger.info(
                "retrying %s (%d) after %d seconds due to HTTP status code %d"
                % (url, n, wait, fd.getcode()))

            fd.close()
            time.sleep(wait)

        except urllib2.HTTPError as e:
            if e.code >= 400 and e.code < 500:
                raise

            logger.warn("retrying %s (%d) after %d seconds due to %s"
                % (url, n, wait, str(e)))

            time.sleep(wait)

        except (urllib2.URLError, socket.error) as e:
            logger.warn("retrying %s (%d) after %d seconds due to %s"
                % (url, n, wait, str(e)))

            time.sleep(wait)

# retry ()


def fetch(url, cred, authdata, postlines, combiner, dest, timeout,
        retry_count, retry_wait, finished, lock, verbose):
    try:
        url_handlers = []

        if cred and url.post_qa() in cred:  # use static credentials
            query_url = url.post_qa()
            (user, passwd) = cred[query_url]
            mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            mgr.add_password(None, query_url, user, passwd)
            h = urllib2.HTTPDigestAuthHandler(mgr)
            url_handlers.append(h)

        elif authdata:  # use the pgp-based auth method if supported
            wadl_url = url.wadl()
            auth_url = url.auth()
            query_url = url.post_qa()

            try:
                fd = retry(urllib2.urlopen, wadl_url, None, timeout,
                           retry_count, retry_wait, verbose)

                try:
                    root = ET.parse(fd).getroot()
                    ns = "{http://wadl.dev.java.net/2009/02}"
                    el = "resource[@path='auth']"

                    if root.find(".//" + ns + el) is None:
                        raise AuthNotSupported

                finally:
                    fd.close()

                msg("authenticating at %s" % auth_url, verbose)

                if not isinstance(authdata, bytes):
                    authdata = authdata.encode('utf-8')

                try:
                    fd = retry(urllib2.urlopen, auth_url, authdata, timeout,
                               retry_count, retry_wait, verbose)

                    try:
                        if fd.getcode() == 200:
                            up = fd.read()

                            if isinstance(up, bytes):
                                up = up.decode('utf-8')

                            try:
                                (user, passwd) = up.split(':')
                                mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                                mgr.add_password(None, query_url, user, passwd)
                                h = urllib2.HTTPDigestAuthHandler(mgr)
                                url_handlers.append(h)

                            except ValueError:
                                msg("invalid auth response: %s" % up)
                                return

                            msg("authentication at %s successful"
                                % auth_url, verbose)

                        else:
                            msg("authentication at %s failed with HTTP "
                                "status code %d" % (auth_url, fd.getcode()))

                    finally:
                        fd.close()

                except (urllib2.URLError, socket.error) as e:
                    msg("authentication at %s failed: %s" % (auth_url, str(e)))
                    query_url = url.post()

            except (urllib2.URLError, socket.error, ET.ParseError) as e:
                msg("reading %s failed: %s" % (wadl_url, str(e)))
                query_url = url.post()

            except AuthNotSupported:
                msg("authentication at %s is not supported"
                    % auth_url, verbose)

                query_url = url.post()

        else:  # fetch data anonymously
            query_url = url.post()

        opener = urllib2.build_opener(*url_handlers)

        i = 0
        n = len(postlines)
        print('postlines: %s' % postlines)

        while i < len(postlines):
            if n == len(postlines):
                msg("getting data from %s" % query_url, verbose)

            else:
                msg("getting data from %s (%d%%..%d%%)"
                    % (query_url,
                       100*i/len(postlines),
                       min(100, 100*(i+n)/len(postlines))),
                    verbose)

            print('URL post_params: %s' % url.post_params())
            postdata = (''.join((p + '=' + str(v) + '\n')
                                for (p, v) in url.post_params()) +
                        ''.join(postlines[i:i+n]))

            print(url)
            print(postdata)

            # msg("postdata:\n%s" % postdata, verbose)
            
            if not isinstance(postdata, bytes):
                postdata = postdata.encode('utf-8')

            try:
                fd = retry(opener.open, query_url, postdata, timeout,
                           retry_count, retry_wait, verbose)

                try:
                    if fd.getcode() == 204:
                        msg("received no data from %s" % query_url, verbose)

                    elif fd.getcode() != 200:
                        msg("getting data from %s failed with HTTP status "
                            "code %d" % (query_url, fd.getcode()))

                        break

                    else:
                        size = 0

                        content_type = fd.info().get('Content-Type')
                        content_type = content_type.split(';')[0]

                        if combiner and content_type == combiner.mimetype:

                            combiner.combine(fd)
                            size = combiner.buffer_size

                        else:
                            msg("getting data from %s failed: unsupported "
                                "content type '%s'" % (query_url,
                                                       content_type))

                            break

                        msg("got %d bytes (%s) from %s"
                            % (size, content_type, query_url), verbose)

                    i += n

                finally:
                    fd.close()

            except urllib2.HTTPError as e:
                if e.code == 413 and n > 1:
                    msg("request too large for %s, splitting"
                        % query_url, verbose)

                    n = -(n//-2)

                else:
                    msg("getting data from %s failed: %s"
                        % (query_url, str(e)))

                    break

            except (urllib2.URLError, socket.error, ET.ParseError) as e:
                msg("getting data from %s failed: %s"
                    % (query_url, str(e)))

                break

    finally:
        finished.put(threading.current_thread())

# fetch ()


def route(url, qp, cred, authdata, postdata, dest, timeout, retry_count,
          retry_wait, maxthreads, verbose=True):
    threads = []
    running = 0
    finished = Queue.Queue()
    lock = threading.Lock()

    query_format = qp.get('format')
    if not query_format:
        # TODO(damb): raise a proper exception
        raise

    combiner = Combiner.create(query_format, qp=qp)

    if postdata:
        # TODO(damb): To be refactored!
        # NOTE: Uses the post_params method of a RoutingURL.
        query_url = url.post()
        postdata = (''.join((p + '=' + v + '\n')
                            for (p, v) in url.post_params()) +
                    postdata)

        if not isinstance(postdata, bytes):
            postdata = postdata.encode('utf-8')

    else:
        query_url = url.get()

    msg("getting routes from %s" % query_url, verbose)

    try:
        fd = retry(urllib2.urlopen, query_url, postdata, timeout, retry_count,
                   retry_wait, verbose)

        try:
            if fd.getcode() == 204:
                raise Error("received no routes from %s" % query_url)

            elif fd.getcode() != 200:
                raise Error("getting routes from %s failed with HTTP status "
                            "code %d" % (query_url, fd.getcode()))

            else:
                urlline = None
                postlines = []

                while True:
                    line = fd.readline()
                    print('Line: %s' % line)

                    if isinstance(line, bytes):
                        line = line.decode('utf-8')

                    if not urlline:
                        urlline = line.strip()

                    elif not line.strip():
                        if postlines:
                            target_url = TargetURL(urlparse.urlparse(urlline),
                                                   url.target_params())
                            threads.append(threading.Thread(target=fetch,
                                                            args=(target_url,
                                                                  cred,
                                                                  authdata,
                                                                  postlines,
                                                                  combiner,
                                                                  dest,
                                                                  timeout,
                                                                  retry_count,
                                                                  retry_wait,
                                                                  finished,
                                                                  lock,
                                                                  verbose)))

                        urlline = None
                        postlines = []

                        if not line:
                            break

                    else:
                        postlines.append(line)

        finally:
            fd.close()

    except (urllib2.URLError, socket.error) as e:
        raise Error("getting routes from %s failed: %s" % (query_url, str(e)))

    for t in threads:
        if running >= maxthreads:
            thr = finished.get(True)
            thr.join()
            running -= 1

        t.start()
        running += 1

    while running:
        thr = finished.get(True)
        thr.join()
        running -= 1

    combiner.dump(dest)

# route ()

# -----------------------------------------------------------------------------
class EIDAWSRouter:
    """
    Implementation of the federator routing facility using EIDAWS Routing.

    ----
    References:
    https://www.orfeus-eu.org/data/eida/webservices/routing/
    """

    LOGGER = 'federator.eidaws_router'

    def __init__(self, url, query_params={}, postdata=None, dest=None, 
            timeout=settings.DEFAULT_ROUTING_TIMEOUT,
            num_retries=settings.DEFAULT_ROUTING_RETRIES,
            retry_wait=settings.DEFAULT_ROUTING_RETRY_WAIT,
            max_threads=settings.DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS):

        self.logger = logging.getLogger(self.LOGGER)
        
        # TODO(damb): to be refactored
        self.url = url
        self.query_params = query_params
        self.postdata = postdata
        self.dest = dest
        self._cred = None
        self._authdata = None
        self.timeout = timeout
        self.num_retries = num_retries
        self.retry_wait = retry_wait

        # TODO(damb): To be removed.
        self.max_threads = max_threads


        self.threads = []
        query_format = query_params.get('format')
        if not query_format:
            # TODO(damb): raise a proper exception
            raise
        self._combiner = Combiner.create(query_format, qp=query_params)

        self.__routing_table = []
        self.__thread_pool = ThreadPool(processes=max_threads)


    @property
    def cred(self):
        return self._cred

    @cred.setter
    def cred(self, user, password):
        self._cred = (user, password)

    @property
    def authdata(self):
        return self._authdata

    def _route(self, url, qp, cred, authdata, postdata, dest, timeout,
            retry_count, retry_wait, maxthreads):
        """creates the routing table"""

        running = 0
        finished = Queue.Queue()
        lock = threading.Lock()

        if postdata:
            # NOTE(damb): Uses the post_params method of a RoutingURL.
            query_url = url.post()
            postdata = (''.join((p + '=' + v + '\n')
                                for (p, v) in url.post_params()) +
                        postdata)

            if not isinstance(postdata, bytes):
                postdata = postdata.encode('utf-8')

        else:
            query_url = url.get()

        self.logger.info("getting routes from %s" % query_url)

        try:
            fd = retry(urllib2.urlopen, query_url, postdata, timeout,
                    retry_count, retry_wait)

            try:
                if fd.getcode() == 204:
                    # TODO(damb): Implement a proper error handling - raising a
                    # simple error is not useful at all.
                    raise Error("received no routes from %s" % query_url)

                elif fd.getcode() != 200:
                    raise Error("getting routes from %s failed with HTTP status "
                                "code %d" % (query_url, fd.getcode()))

                else:
                    urlline = None
                    postlines = []

                    while True:
                        line = fd.readline()

                        if isinstance(line, bytes):
                            line = line.decode('utf-8')

                        if not urlline:
                            urlline = line.strip()

                        elif not line.strip():
                            # TODO(damb): create tasks instead of directly
                            # creating thread objects.
                            if postlines:
                                target_url = TargetURL(urlparse.urlparse(urlline),
                                                       url.target_params())
                                self.threads.append(threading.Thread(target=fetch,
                                                                args=(target_url,
                                                                      cred,
                                                                      authdata,
                                                                      postlines,
                                                                      self._combiner,
                                                                      dest,
                                                                      timeout,
                                                                      retry_count,
                                                                      retry_wait,
                                                                      finished,
                                                                      lock,
                                                                      True)))

                            urlline = None
                            postlines = []

                            if not line:
                                break

                        else:
                            postlines.append(line)

            finally:
                fd.close()

        except (urllib2.URLError, socket.error) as e:
            raise Error("getting routes from %s failed: %s" % (query_url, str(e)))

        for t in self.threads:
            if running >= maxthreads:
                thr = finished.get(True)
                thr.join()
                running -= 1

            t.start()
            running += 1

        while running:
            thr = finished.get(True)
            thr.join()
            running -= 1

        self._combiner.dump(dest)

    # _route ()

    def _fetch(self):
        """fetches the results"""
        # NOTE(damb): This _fetch method is used in another way than Andres
        # fetch method. The _fetch function written by Andres is basically a
        # task.

        # apply tasks to the thread_pool
        pass

    # _fetch ()

    def __call__(self):
        self._route(self.url, self.query_params, self.cred, self.authdata,
                self.postdata, self.dest, self.timeout, self.num_retries,
                self.retry_wait, self.max_threads)
    
    # __call__ ()

# class EIDAWSRouter

# ---- END OF <route.py> ----
