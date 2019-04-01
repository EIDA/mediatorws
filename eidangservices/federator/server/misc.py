# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
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
# REVISION AND CHANGES
# 2018/05/28        V0.1    Daniel Armbruster
# -----------------------------------------------------------------------------
"""
Miscellaneous utils.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import enum
import os
import random
import tempfile
import uuid

from eidangservices.utils.error import Error, ErrorWithTraceback


class KeepTempfiles(enum.Enum):
    ALL = 0
    ON_ERRORS = 1
    NONE = 2

# class KeepTempfiles


class Context(object):
    """
    Utility implementation of a simple hierarchical context.

    :param ctx: Hashable to be used for context initialization.
    :param bool root_only: The context relies on its root context when
        handling with locks.
    """
    SEP = '::'

    class ContextError(ErrorWithTraceback):
        """Base context error ({})."""

    # TODO(damb): Make it threadsafe!

    def __init__(self, ctx=None, root_only=True):
        self._ctx = ctx if ctx else uuid.uuid4()
        try:
            hash(self._ctx)
        except TypeError as err:
            raise self.ContextError('Context unhashable ({}).'.format(err))
        self._parent_ctx = None
        self._root_only = root_only

        self._path_ctx = None
        self._child_ctxs = set()

    @property
    def locked(self):
        if not self._root_only or self._is_root:
            return bool(self._path_ctx) and os.path.isfile(self._path_ctx)
        # check if the root context is still locked
        return self._get_root_ctx().locked

    # locked ()

    @property
    def _is_root(self):
        return not self._parent_ctx

    def acquire(self, path_tempdir=tempfile.gettempdir(), hidden=True):
        """
        Acquire a temporary file for the context.

        :param str path_tempdir: Path for temporary files the lock will be
            located
        :param bool hidden: Use hidden files when creating the lock.
        """
        if not self._root_only or self._is_root:
            self._path_ctx = os.path.join(
                path_tempdir,
                '{}{}'.format(('.' if hidden else ''), str(self._ctx)))

            if os.path.isfile(self._path_ctx):
                raise FileExistsError
            try:
                open(self._path_ctx, 'a').close()
            except OSError as err:
                raise self.ContextError('Cannot create lock ({}).'.format(err))
        else:
            # acquire a lock for the root context
            root = self._get_root_ctx()
            root.acquire(path_tempdir)
            # broadcast
            for c in root:
                c._path_ctx = root._path_ctx

    # acquire ()

    def release(self):
        """
        Remove a previously acquired temporary file.
        """
        if not self._root_only or self._is_root:
            if not self._path_ctx:
                raise self.ContextError('Not acquired.')
            try:
                os.remove(self._path_ctx)
            except OSError as err:
                raise self.ContextError(
                    'While removing context ({}).'.format(err))
            self._path_ctx = None
        else:
            root = self._get_root_ctx()
            root.release()
            # broadcast
            for c in root:
                c._path_ctx = None

    # release ()

    def teardown(self):
        """
        Securely remove the context.
        """
        if self._is_root:
            for c in self._child_ctxs:
                self.__sub__(c)
            try:
                self.release()
            except Error:
                pass
        else:
            self._get_root_ctx().teardown()

    # teardown ()

    def __add__(self, ctx):
        """
        Add a sub-context to the current context.

        :param ctx: Context to be added.
        :type ctx: :py:class:`Context`
        """
        for c in ctx:
            if c.locked and ctx._root_only:
                raise self.ContextError(
                    'Cannot add locked contexts. Please, release first.')

        uuids = set([c._ctx for c in self])
        other_uuids = set([c._ctx for c in ctx])
        if uuids & other_uuids:
            raise self.ContextError('Only unique UUIDs allowed.')

        for c in ctx:
            c._root_only = self._root_only

        ctx._parent_ctx = self
        self._child_ctxs.add(ctx)

    # __add__ ()

    def __sub__(self, ctx):
        """
        Remove a sub-context from the current context.

        :param ctx: Context to be removed.
        :type ctx: :py:class:`Context`
        """
        if ctx in self:
            if ctx._child_ctxs:
                ctx.__sub__(ctx._child_ctxs.pop())

            if ctx.locked:
                ctx.release()
            self._child_ctxs.discard(ctx)

    # __sub__ ()

    def __contains__(self, other):
        return other in self._child_ctxs

    def __eq__(self, other):
        # TODO(damb): To be implemented.
        return self == other

    def __hash__(self):
        return hash(str(self))

    def __iter__(self):
        yield self

        for c in self._child_ctxs:
            # XXX(damb): Python3 only: yield from iter(c)
            for _c in iter(c):
                yield _c

    # __iter__ ()

    def __str__(self):
        stack = [self._ctx]

        parent_ctx = self._parent_ctx
        while parent_ctx:
            parent_ctx = parent_ctx._parent_ctx
            if not parent_ctx:
                break
            stack.append(parent_ctx._ctx)

        return self.SEP.join(str(e) for e in reversed(stack))

    # __str__ ()

    def _get_root_ctx(self):
        parent_ctx = self._parent_ctx
        ctx = self
        while parent_ctx:
            parent_ctx = parent_ctx._parent_ctx
            if not parent_ctx:
                break
            ctx = parent_ctx

        return ctx

    # _get_root_ctx ()

    def _get_current_object(self):
        return self._ctx

# class Context


def get_temp_filepath():
    """Return path of temporary file."""

    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

# get_temp_filepath ()

def choices(seq, k=1):
    return ''.join(random.choice(seq) for i in range(k))

# choices ()

def elements_equal(e, e_other, exclude_tags=[], recursive=True):
    """
    Compare XML :py:class:`lxml.etree` elements.

    :param e: :py:class:`lxml.etree` to compare with :code:`e_other`.
    :type e: :py:class:`lxml.etree`
    :type e_other: :py:class:`lxml.etree`
    :param list exclude_tags: List of child element tags to be excluded
        while comparing. When excluding child elements the function
        makes use of :py:func:`copy.deepcopy`
    :param bool recursive: Recursively exclude matching child elements.

    .. note:: The function expects child elements to be ordered.
    """
    local_e = e
    local_e_other = e_other

    def remove_elements(t, exclude_tags, recursive):
        for tag in exclude_tags:
            xpath = tag
            if recursive:
                xpath = ".//{}".format(tag)
            for n in t.findall(xpath):
                n.getparent().remove(n)

    if exclude_tags:
        # XXX(damb): In order to make use of len(e) to increase
        # performance we create local copies of the elements with child
        # elements excluded
        from copy import deepcopy
        local_e = deepcopy(e)
        local_e_other = deepcopy(e_other)
        remove_elements(local_e, exclude_tags, recursive)
        remove_elements(local_e_other, exclude_tags, recursive)

    if local_e.tag != local_e_other.tag:
        return False
    if local_e.text != local_e_other.text:
        return False
    if local_e.tail != local_e_other.tail:
        return False
    if local_e.attrib != local_e_other.attrib:
        return False
    if len(local_e) != len(local_e_other):
        return False
    return all(elements_equal(c, c_other)
               for c, c_other in zip(local_e, local_e_other))

# elements_equal ()

# ---- END OF <misc.py> ----
