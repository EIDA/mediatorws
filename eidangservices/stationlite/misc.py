# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.
"""

import argparse
from flask import make_response

from sqlalchemy import create_engine

from eidangservices import settings


def get_response(output, mimetype):
    """Return Response object for output and mimetype."""

    response = make_response(output)
    response.headers['Content-Type'] = mimetype
    return response


def db_engine(url):
    """
    Check if `url` is a valid URL by means of creating a `SQLAlchemy
    <https://www.sqlalchemy.org/>`_.
    """
    try:
        return create_engine(url)
    except Exception as err:
        raise argparse.ArgumentTypeError(
            'Error while creating engine ({}).'.format(err))


def node_generator(exclude=[]):

    nodes = list(settings.EIDA_NODES)

    for node in nodes:
        if node not in exclude:
            yield node, settings.EIDA_NODES[node]
