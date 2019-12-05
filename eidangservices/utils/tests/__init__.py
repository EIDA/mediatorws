# -*- coding: utf-8 -*-
"""
Provides testsuite loading methods.
"""

import unittest

from eidangservices.utils.tests import schema, sncl, fdsnws

federator_available = False
mediator_available = False
stationlite_available = False

try:
    import eidangservices.federator.tests
    federator_available = True
except ImportError:
    federator_available = False

try:
    import eidangservices.mediator.tests
    mediator_available = True
except ImportError:
    mediator_available = False

try:
    import eidangservices.stationlite.tests
    stationlite_available = True
except ImportError:
    stationlite_available = False


# -----------------------------------------------------------------------------
def general_testsuite():
    """
    Load the general testsuite.
    """
    # NOTE(damb): Loading tests with discover does not work since the
    # directory 'eidangservices/tests' is considered as a namespace package.
    # Also discover() seems to change PYTHONPATH
    # return loader.discover(__name__.replace('.', os.path.sep), '*.py')
    general_testsuite = unittest.TestSuite()
    loader = unittest.TestLoader()
    general_testsuite.addTests(loader.loadTestsFromModule(schema))
    general_testsuite.addTests(loader.loadTestsFromModule(sncl))
    general_testsuite.addTests(loader.loadTestsFromModule(fdsnws))
    return general_testsuite


def federator_testsuite():
    """
    Load the general testsuite + federator testsuite.
    """
    federator_testsuite = general_testsuite()
    if federator_available:
        federator_testsuite.addTests(
            eidangservices.federator.tests.testsuite())
    return federator_testsuite


def mediator_testsuite():
    """
    Load the general testsuite + mediator testsuite.
    """
    mediator_testsuite = general_testsuite()
    if mediator_available:
        mediator_testsuite.addTests(
            eidangservices.mediator.tests.testsuite())
    return mediator_testsuite


def stationlite_testsuite():
    """
    Load the general testsuite + stationlite testsuite.
    """
    stationlite_testsuite = general_testsuite()
    if stationlite_available:
        stationlite_testsuite.addTests(
            eidangservices.stationlite.tests.testsuite())
    return stationlite_testsuite


def testsuite():
    """
    Load a testsuite for all EIDA NG webservices i.e.

        + general testsuite
        + federator testsuite
        + mediator testsuite
        + stationlite testsuite
    """
    testsuite = general_testsuite()
    if federator_available:
        testsuite.addTests(eidangservices.federator.tests.testsuite())
    if mediator_available:
        testsuite.addTests(eidangservices.mediator.tests.testsuite())
    if stationlite_available:
        testsuite.addTests(eidangservices.stationlite.tests.testsuite())
    return testsuite
