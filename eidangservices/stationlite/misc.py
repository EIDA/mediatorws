# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <misc.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
#
# eida-stationlite is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# eida-stationlite is distributed in the hope that it will be useful,
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
#
# REVISION AND CHANGES
# 2017/12/21        V0.1    Daniel Armbruster; Based on fab's code.
# =============================================================================
"""
This file is part of the EIDA mediator/federator webservices.

"""

from flask import current_app, g, make_response

from eidangservices.stationlite.engine import db


# -----------------------------------------------------------------------------
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

# get_db ()


def get_response(output, mimetype):
    """Return Response object for output and mimetype."""
    
    response = make_response(output)
    response.headers['Content-Type'] = mimetype
    return response

# get_response ()

# ---- END OF <misc.py> ----
