# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
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
# -----------------------------------------------------------------------------
"""
Miscellaneous utils.

This file is part of the EIDA mediator/federator webservices.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import hashlib
import os
import random
import tempfile
import time

import fasteners

from eidangservices import settings

# -----------------------------------------------------------------------------
class URLConnectionLock(fasteners.InterProcessLock):
    """
    A :py:class:`fasteners.InterProcessLock` wrapper encoding the URL passed by
    means of an hash within the lockfile's filename.
    """
    def __init__(self, url, path_lockdir=settings.PATH_LOCKDIR,
                 sleep_func=time.sleep, logger=None):
        """
        :param str url: url to be encoded within the lockfile's filename
        :param str path_lockdir: lockfile directory path
        :param sleep_func: reference to a sleep function
        :param logging.Logger logger: logger instance
        """
        hashed_url = hashlib.sha224(url).hexdigest()
        path = os.path.join(path_lockdir, hashed_url)
        super(URLConnectionLock, self).__init__(path, sleep_func, logger)

    # __init__ ()

# class URLConnectionLock

# -----------------------------------------------------------------------------
def get_temp_filepath():
    """Return path of temporary file."""

    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

# get_temp_filepath ()

def choices(seq, k=1):
    return ''.join(random.choice(seq) for i in range(k))

# choices ()

# ---- END OF <misc.py> ----
