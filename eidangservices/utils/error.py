# -*- coding: utf-8 -*-
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


class ErrorWithTraceback(Error):
    """Error with traceback."""
    traceback = True
