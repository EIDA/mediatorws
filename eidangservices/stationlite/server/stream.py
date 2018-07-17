# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <stream.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
#
# eida-stationlite is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# eida-stationlite is distributed in the hope that it will be useful,
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
#
# REVISION AND CHANGES
# 2018/05/03        V0.1    Daniel Armbruster
# =============================================================================
"""
StationLite output format facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import eidangservices as eidangws


class OutputStream(object):
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

    # create ()

    def __str__(self):
        raise NotImplementedError

# class OutputStream


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
        retval =''
        for url, stream_epoch_lst in self.routes:
            if retval:
                retval += '\n\n'
            retval += url + '\n' + '\n'.join(self._deserialize(se)
                                             for se in stream_epoch_lst)

        if retval:
            retval += '\n'

        return retval

    # __str__ ()

# class PostStream


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
        retval =''
        for url, stream_epoch_lst in self.routes:
            for se in stream_epoch_lst:
                retval += '{}?{}\n'.format(url, self._deserialize(se))

        return retval

    # __str__ ()

# class GetStream


# ---- END OF <stream.py> ----
