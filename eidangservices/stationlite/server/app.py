#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
stationlite server.

This file is part of the EIDA mediator/federator webservices.

"""

from flask import Flask
from flask_restful import Api


from mediator import settings

from eidangservices.stationlite.server.routes.stationlite import \
    StationLiteResource
from eidangservices.stationlite.server.routes.wildcards import \
    WildcardsResource


    
def main(debug=False, port=5002):
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
 
    api.init_app(app)
    
    app.config.update(PORT=port)
    app.run(threaded=True, debug=debug, port=port)


if __name__ == '__main__':
    main()
