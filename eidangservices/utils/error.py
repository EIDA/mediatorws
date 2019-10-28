# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <error.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices are free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices are distributed in the hope that it will be useful,
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
# 2018/02/12        V0.1    Daniel Armbruster
# =============================================================================
"""
Error and exception facilities.
"""


class ExitCodes:
    """
    Enum for exit codes.
    """
    EXIT_SUCCESS = 0
    EXIT_WARNING = 1
    EXIT_ERROR = 2

# class ExitCodes


class Error(Exception):
    """Error base class"""

    # if we raise such an Error and it is only catched by the uppermost
    # exception handler (that exits short after with the given exit_code),
    # it is always a (fatal and abrupt) EXIT_ERROR, never just
    # a warning.
    exit_code = ExitCodes.EXIT_ERROR
    # show a traceback?
    traceback = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_message(self):
        return type(self).__doc__.format(*self.args)

    __str__ = get_message

# class Error

class ErrorWithTraceback(Error):
    """Error with traceback."""
    traceback = True


# ---- END OF <error.py> ----
