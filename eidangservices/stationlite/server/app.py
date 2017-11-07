#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
stationlite server.

This file is part of the EIDA mediator/federator webservices.

"""

from flask import Flask

from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from eidangservices import settings

#from eidangservices.stationlite.engine import dbquery

from eidangservices.stationlite.server.routes.stationlite import \
    StationLiteResource
from eidangservices.stationlite.server.routes.wildcards import \
    WildcardsResource


db = SQLAlchemy()

    
def main(debug=False, port=5002, dbfile=''):
    """Run Flask app."""

    errors = {
        'NODATA': {
            'message': "Empty dataset.",
            'status': 204,
        },
    }

    app = Flask(__name__)
    api = Api(errors=errors)

    ## routing service endpoint
    
    # query method
    api.add_resource(
        StationLiteResource, "%s%s" % (settings.EIDA_STATIONLITE_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))

    ## wildcardresolver service endpoint
    
    # query method
    api.add_resource(
        WildcardsResource, "%s%s" % (settings.EIDA_WILDCARDS_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))
 
    sqlalchemy_uri = "sqlite:///{}".format(dbfile)
    
    app.config.update(
        PORT=port, DB=dbfile, SQLALCHEMY_DATABASE_URI=sqlalchemy_uri)
    
    api.init_app(app)
    db.init_app(app)
    
    app.run(threaded=True, debug=debug, port=port)


if __name__ == '__main__':
    main()
