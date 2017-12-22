# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

from flask import current_app, g, make_response

from eidangservices.stationlite.engine import db


def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    
    """
    
    if not hasattr(g, 'db_connection'):
        
        g.db_engine, g.db_connection = db.get_engine_and_connection(
            current_app.config['SQLALCHEMY_DATABASE_URI'])
        
        g.db_tables = db.get_db_tables(g.db_engine)
        
    return g.db_engine, g.db_connection, g.db_tables


def get_response(output, mimetype):
    """Return Response object for output and mimetype."""
    
    response = make_response(output)
    response.headers['Content-Type'] = mimetype
    return response
