# -*- coding: utf-8 -*-
"""
Miscellaneous utils.
"""

import enum
import os
import importlib
import logging
import random
import tempfile
import uuid

from redis.exceptions import RedisError

from eidangservices.federator.server import redis_client
from eidangservices.utils.error import Error, ErrorWithTraceback


class ContextLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter expecting the passed in dict-like object to have a 'ctx' key, whose
    value in brackets is prepended to the log message.
    """
    def process(self, msg, kwargs):
        return '[%s] %s' % (self.extra['ctx'], msg), kwargs


class KeepTempfiles(enum.Enum):
    ALL = 0
    ON_ERRORS = 1
    NONE = 2


class Context:
    """
    Utility implementation of a simple hierarchical request context. Request
    contexts are pickable.

    :param ctx: Hashable to be used for context initialization.
    :t
    :param payload: Payload to be associated with the context.
    """
    SEP = '::'

    class ContextError(ErrorWithTraceback):
        """Base context error ({})."""

    def __init__(self, ctx=None, payload=None):
        """
        :param ctx: Context identifier
        :type ctx: None or hashable
        """

        self._ctx = ctx or uuid.uuid4()
        try:
            hash(self._ctx)
        except TypeError as err:
            raise self.ContextError('Context unhashable ({}).'.format(err))

        self._payload = payload or {}
        self._parent_ctx = None

        self._key = 'request:' + str(self._ctx)
        self._child_ctxs = []

    @property
    def locked(self):
        if self._is_root:
            try:
                return bool(redis_client.exists(self._key))
            except RedisError as err:
                raise self.ContextError(err)
        # check if the root context is still locked
        return self._get_root_ctx().locked

    @property
    def payload(self):
        return self._payload

    @property
    def _is_root(self):
        return self._parent_ctx is None

    def acquire(self):
        """
        Acquire a context lock.
        """

        if self._is_root:

            assert not redis_client.exists(self._key), \
                'Context lock already acquired.'

            # acquire by means of creating a redis hash
            resp = None
            try:
                resp = redis_client.set(self._key, 'locked')
            except RedisError as err:
                raise self.ContextError(
                    'Error while creating lock: {}'.format(err))
            else:
                if not resp:
                    raise self.ContextError(
                        'Error while creating lock '
                        '(already existing): {}'.format(self._key))

        else:
            # acquire a lock for the root context
            root = self._get_root_ctx()
            root.acquire()

    def release(self):
        """
        Release a context lock.
        """

        if self._is_root:
            try:
                resp = redis_client.delete(self._key)
            except RedisError as err:
                raise self.ContextError(
                    'Error while removing context lock: {}'.format(err))
            else:
                if not resp:
                    raise self.ContextError(
                        'Error while removing context lock: '
                        '{}'.format(self._key))

        else:
            root = self._get_root_ctx()
            root.release()

    def teardown(self):
        """
        Securely remove the context.

        When a context is removed, all subcontexts are dropped, too.
        """

        if self._is_root:
            for c in self._child_ctxs:
                self.__sub__(c)
            try:
                self.release()
            except Error:
                pass
        else:
            root = self._get_root_ctx()
            root.teardown()

    def associate(self, payload, root_only=True):
        """
        Associate payload with a context.

        :param dict payload: Payload to be associated
        :param bool root_only: Associate payload with *root* context instead of
            the context itself
        """

        if root_only:
            root = self._get_root_ctx()
            root._payload.update(payload)
        else:
            self._payload.update(payload)

    def append(self, ctx):
        self.__add__(ctx)

    def remove(self, ctx):
        self.__sub__(ctx)

    def __getstate__(self):
        d = dict(self.__dict__)
        if '_ctx' in d.keys():
            d['_ctx_type'] = qualname(d['_ctx'])
            d['_ctx'] = str(d['_ctx'])

        return d

    def __setstate__(self, state):
        if '_ctx' in state.keys() and '_ctx_type' in state.keys():
            m = importlib.import_module(
                '.'.join(p for p in state['_ctx_type'].split('.')[:-1]))
            c = state['_ctx_type'].split('.')[-1]

            state['_ctx'] = getattr(m, c)(state['_ctx'])
            del state['_ctx_type']

        if '_child_ctxs' in state.keys():
            for c in state['_child_ctxs']:
                c._parent_ctx = self

        self.__dict__.update(state)

    def __add__(self, ctx):
        """
        Add a sub-context to the current context.

        :param ctx: Context to be added.
        :type ctx: :py:class:`Context`

        :returns: The context the sub-context was associated with
        :rtype: :py:class:`Context`
        """

        ctxs = set([c._ctx for c in self])
        other_ctxs = set([c._ctx for c in ctx])
        if ctxs & other_ctxs:
            raise self.ContextError('Only unique contexts allowed.')

        ctx._parent_ctx = self
        self._child_ctxs.append(ctx)

        return self

    def __sub__(self, ctx):
        """
        Remove a sub-context from the current context.

        :param ctx: Context to be removed.
        :type ctx: :py:class:`Context`

        :returns: Sub-context removed
        :rtype: :py:class:`Context` or None
        """

        if ctx in self:
            self._child_ctxs.remove(ctx)
            return ctx

        return None

    def __contains__(self, other):
        return other in self._child_ctxs

    def __eq__(self, other):
        # TODO(damb): To be implemented. Currently, comparison is based on
        # __hash__(), exclusively.
        return self._ctx == other._ctx

    def __hash__(self):
        return hash(self._ctx)

    def __iter__(self):
        """
        Generator providing a recursive iterator implementation.
        """

        yield self

        for c in self._child_ctxs:
            yield from iter(c)

    def __str__(self):
        stack = [self._ctx]

        parent_ctx = self._parent_ctx
        while parent_ctx:
            stack.append(parent_ctx._ctx)
            if not parent_ctx:
                break
            parent_ctx = parent_ctx._parent_ctx

        return self.SEP.join(str(e) for e in reversed(stack))

    def _get_root_ctx(self):
        if self._parent_ctx is None:
            return self

        parent_ctx = self._parent_ctx
        ctx = self
        while parent_ctx:
            ctx = parent_ctx
            if not parent_ctx:
                break
            parent_ctx = parent_ctx._parent_ctx

        return ctx


# -----------------------------------------------------------------------------
def qualname(obj):
    m = type(obj).__module__
    # avoid reporting __builtin__
    return (type(obj).__name
            if m is None or m == type(str).__module__ else
            m + '.' + type(obj).__name__)


def get_temp_filepath():
    """Return path of temporary file."""

    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))


def choices(seq, k=1):
    return ''.join(random.choice(seq) for i in range(k))


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
