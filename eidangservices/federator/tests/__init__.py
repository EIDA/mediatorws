import os
import unittest

def federator_testsuite():
    """
    load the federator testsuite
    """
    loader = unittest.TestLoader()
    return loader.discover(__name__.replace('.', os.path.sep), '*.py')
