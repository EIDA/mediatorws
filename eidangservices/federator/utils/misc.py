# -*- coding: utf-8 -*-
"""
Miscellaneous utils.

This file is part of the EIDA mediator/federator webservices.

"""

import os
import tempfile


def get_temp_filepath():
    """Return path of temporary file."""
    
    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

   