# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <error.py>
# -----------------------------------------------------------------------------
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#  3. The name of the author may not be used to endorse or promote
#     products derived from this software without specific prior
#     written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----
#
# Copyright (c) Daniel Armbruster (ETH), Fabian Euchner (ETH)
# Copyright (c) 2015-2018 The Borg Collective (see AUTHORS file)
# Copyright (c) 2010-2014 Jonas Borgström <jonas@borgstrom.se>
#
# REVISION AND CHANGES
# 2018/02/12        V0.1    Daniel Armbruster
# =============================================================================
"""
Error and exception facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

from eidangservices.utils import ExitCodes

class Error(Exception):
    """Error base class"""

    # if we raise such an Error and it is only catched by the uppermost
    # exception handler (that exits short after with the given exit_code),
    # it is always a (fatal and abrupt) EXIT_ERROR, never just
    # a warning.
    exit_code = ExitCodes.EXIT_ERROR
    # show a traceback?
    traceback = False

    def __init__(self, *args):
        super().__init__(*args)
        self.args = args

    def get_message(self):
        return type(self).__doc__.format(*self.args)

    __str__ = get_message

# class Error

class ErrorWithTraceback(Error):
    """Error with traceback."""
    traceback = True


# ---- END OF <error.py> ----
