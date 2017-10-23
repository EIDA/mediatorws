#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Federator server.

This file is part of the EIDA mediator/federator webservices.

"""

import tempfile

from flask import Flask
from flask_restful import Api

from eidangservices import settings

from eidangservices.federator.server.routes.dataselect import \
    DataselectResource

from eidangservices.federator.server.routes.misc import \
    DataselectVersionResource, StationVersionResource, DataselectWadlResource,\
    StationWadlResource

from eidangservices.federator.server.routes.station import StationResource


    
def main(args):
    #debug=False, port=5000, routing=settings.DEFAULT_ROUTING_SERVICE,
    #tmpdir=''):
    #    debug=args.debug, port=args.port, routing=args.routing, 
    #    tmpdir=args.tmpdir)
    """Run Flask app."""

    errors = {
        'NODATA': {
            'message': "Empty dataset.",
            'status': 204,
        },
    }
    
    if args.tmpdir:
        tempfile.tempdir = args.tmpdir
    
    app = Flask(__name__)
    
    api = Api(errors=errors)

    ## station service endpoint
    
    # query method
    api.add_resource(
        StationResource, "%s%s" % (settings.FDSN_STATION_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))
        
    # version method
    api.add_resource(
        StationVersionResource, "%s%s" % (settings.FDSN_STATION_PATH, 
            settings.FDSN_VERSION_METHOD_TOKEN))
        
    # application.wadl method
    api.add_resource(
        StationWadlResource, "%s%s" % (settings.FDSN_STATION_PATH, 
            settings.FDSN_WADL_METHOD_TOKEN))

    ## dataselect service endpoint
    
    # query method
    api.add_resource(
        DataselectResource, "%s%s" % (settings.FDSN_DATASELECT_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))
        
    # queryauth method
    
    # version method
    api.add_resource(
        DataselectVersionResource, "%s%s" % (settings.FDSN_DATASELECT_PATH, 
            settings.FDSN_VERSION_METHOD_TOKEN))
    
    # application.wadl method
    api.add_resource(
        DataselectWadlResource, "%s%s" % (settings.FDSN_DATASELECT_PATH, 
            settings.FDSN_WADL_METHOD_TOKEN))
        
    api.init_app(app)
    
    app.config.update(
        # TODO(damb): Pass log_level to app.config!
        NUM_THREADS=args.threads,
        PORT=args.port,
        ROUTING_SERVICE=args.routing,
        ROUTING_TIMEOUT=args.timeout,
        ROUTING_RETRIES=args.retries,
        ROUTING_RETRY_WAIT=args.retry_wait,
        TMPDIR=args.tmpdir
    )
    
    app.run(threaded=True, debug=args.debug, port=args.port)


if __name__ == '__main__':
    main()