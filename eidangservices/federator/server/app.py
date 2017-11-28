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
from eidangservices.federator.server.routes.misc import \
    DataselectVersionResource, StationVersionResource, \
    WFCatalogVersionResource, DataselectWadlResource,\
    StationWadlResource, WFCatalogWadlResource 
from eidangservices.federator.server.routes.dataselect import DataselectResource
from eidangservices.federator.server.routes.station import StationResource
from eidangservices.federator.server.routes.wfcatalog import WFCatalogResource 


def setup_app(args):
    """
    Build the Flask app.

    :param dict args: app configuration arguments
    :rtype :py:class:`flask.Flask`:
    """

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
        
    ## wfcatalog service endpoint

    api.add_resource(
        WFCatalogResource, "%s%s" % (settings.FDSN_WFCATALOG_PATH, 
            settings.FDSN_QUERY_METHOD_TOKEN))

    # version method
    api.add_resource(
        WFCatalogVersionResource, "%s%s" % (settings.FDSN_WFCATALOG_PATH, 
            settings.FDSN_VERSION_METHOD_TOKEN))
        
    # application.wadl method
    api.add_resource(
        WFCatalogWadlResource, "%s%s" % (settings.FDSN_WFCATALOG_PATH, 
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
        ROUTING_RETRY_LOCK=args.retry_lock,
        TMPDIR=tempfile.gettempdir()
    )

    return app

# setup_app()
