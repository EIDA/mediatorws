# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

#from flask import current_app

from flask_restful import Resource

from eidangservices import settings

from eidangservices.stationlite.engine import dbquery
from eidangservices.stationlite.utils import misc


class StationLiteResource(Resource):
    """Service query for routing."""
    
    def get(self):
        
        db_engine, db_connection, db_tables = misc.get_db()
        
        # TODO(fab): put in "real" query for SNCL at al.
        # this is an simple example query that lists all networks
        net = dbquery.find_networks(db_connection, db_tables)
        
        return misc.get_response(str(net), settings.MIMETYPE_TEXT)
    

    def post(self): 
        return misc.get_response('post', settings.MIMETYPE_TEXT)

