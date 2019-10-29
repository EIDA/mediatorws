# -*- coding: utf-8 -*-
"""
StationLite output format facilities.
"""

import eidangservices as eidangws


class OutputStream:
    """
    Base class for the StationLite ouput stream format.

    :param list routes: List of :py:class:`eidangservices.utils.Route` objects
    """
    def __init__(self, routes=[]):
        self.routes = routes

    @classmethod
    def create(cls, format, **kwargs):
        if format == 'post':
            return PostStream(**kwargs)
        elif format == 'get':
            return GetStream(**kwargs)
        else:
            raise KeyError('Invalid output format chosen.')

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
            for se in stream_epoch_lst:
                retval += '{}?{}\n'.format(url, self._deserialize(se))

        return retval
