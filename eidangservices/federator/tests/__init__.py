import os
import unittest


def testsuite():
    """
    Load the federator testsuite.
    """
    loader = unittest.TestLoader()
    return loader.discover(__name__.replace('.', os.path.sep), '*.py')
