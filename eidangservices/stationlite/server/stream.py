# -*- coding: utf-8 -*-
"""
StationLite output format facilities.
"""

from urllib.parse import urlsplit, urlunsplit

import eidangservices as eidangws


class OutputStream:
    """
    Base class for the StationLite ouput stream format.

    :param list routes: List of :py:class:`eidangservices.utils.Route` objects
    :param str netloc_proxy: Network location of a proxy
    """
    def __init__(self, routes=[], **kwargs):
        self.routes = routes

        self._netloc_proxy = kwargs.get('netloc_proxy')

    @classmethod
    def create(cls, format, **kwargs):
        if format == 'post':
            return PostStream(**kwargs)
        elif format == 'get':
            return GetStream(**kwargs)
        else:
            raise KeyError('Invalid output format chosen.')

    def prefix_url(self, url):
        parsed_url = urlsplit(url)._asdict()

        parsed_url_netloc = parsed_url['netloc']
        parsed_url['path'] = '/' + parsed_url_netloc + parsed_url['path']
        parsed_url['netloc'] = self._netloc_proxy
        return urlunsplit(parsed_url.values())

    def __str__(self):
        raise NotImplementedError


class PostStream(OutputStream):
    """
    StationLite output stream for `format=post`.
    """
    DESERIALIZER = eidangws.utils.schema.StreamEpochSchema(
        context={'routing': True})

    @staticmethod
    def _deserialize(stream_epoch):
        return ' '.join(PostStream.DESERIALIZER.dump(stream_epoch).values())

    def __str__(self):
        retval = ''
        for url, stream_epoch_lst in self.routes:
            # add url netloc prefix
            if self._netloc_proxy:
                url = self.prefix_url(url)

            if retval:
                retval += '\n\n'
            retval += url + '\n' + '\n'.join(self._deserialize(se)
                                             for se in stream_epoch_lst)

        if retval:
            retval += '\n'

        return retval


class GetStream(OutputStream):
    """
    StationLite output stream for `format=post`.
    """
    DESERIALIZER = eidangws.utils.schema.StreamEpochSchema(
        context={'routing': True})

    @staticmethod
    def _deserialize(stream_epoch):
        return '&'.join(['{}={}'.format(k, v) for k, v in
                         GetStream.DESERIALIZER.dump(stream_epoch).items()])

    def __str__(self):
        retval = ''
        for url, stream_epoch_lst in self.routes:
            # add url netloc prefix
            if self._netloc_proxy:
                url = self.prefix_url(url)

            for se in stream_epoch_lst:
                retval += '{}?{}\n'.format(url, self._deserialize(se))

        return retval
