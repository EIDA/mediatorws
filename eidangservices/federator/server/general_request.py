# -*- coding: utf-8 -*-
"""
Federator request handlers.

This file is part of the EIDA mediator/federator webservices.

"""

import logging
import os

import flask
from flask import current_app, request
from flask_restful import Resource

from federator import settings
from federator.server import httperrors, route
from federator.utils import misc

try:
    # Python 2.x
    import urlparse
except ImportError:
    # Python 3.x
    import urllib.parse as urlparse


# -----------------------------------------------------------------------------
class GeneralResource(Resource):
    """Handler for general resource."""

    LOGGER = "federator.general_resource"

    def __init__(self):
        self.logger = logging.getLogger(self.LOGGER)
   
    # __init__ ()

    @property
    def path_tempfile(self):
        return misc.get_temp_filepath() 

    def _process_request(self, args, mimetype, path_tempfile, postdata=None):
        """Process a request and send resulting file to client."""
        
        self.logger.debug(("Processing request: args={0}, path_tempfile={1}, "
                + "postdata={2}, timout={3}, retries={4}, "
                + "retry_wait={5}, threads={6}").format(args, path_tempfile,
                    bool(postdata), current_app.config['ROUTING_TIMEOUT'], 
                    current_app.config['ROUTING_RETRIES'],
                    current_app.config['ROUTING_RETRY_WAIT'], 
                    current_app.config['NUM_THREADS']))

        resource_path = process_request(args, 
                path_tempfile=path_tempfile,
                postdata=postdata,
                timeout=current_app.config['ROUTING_TIMEOUT'],
                retries=current_app.config['ROUTING_RETRIES'],
                retry_wait=current_app.config['ROUTING_RETRY_WAIT'],
                threads=current_app.config['NUM_THREADS'])

        if resource_path is None or os.path.getsize(resource_path) == 0:
            # TODO(fab): get user-supplied error code
            raise httperrors.NoDataError()
            
        else:
            # return contents of temp file
            try:
                return flask.send_file(resource_path, mimetype=mimetype)
            except Exception:
                # cannot send error code since response is already started
                # TODO(fab): how to let user know of error?
                pass

    # _process_request ()

# class GeneralResource

# -----------------------------------------------------------------------------
def process_request(query_params, 
        path_tempfile=None,
        postdata=None,
        timeout=settings.DEFAULT_ROUTING_TIMEOUT,
        retries=settings.DEFAULT_ROUTING_RETRIES,
        retry_wait=settings.DEFAULT_ROUTING_RETRY_WAIT, 
        threads=settings.DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS):
    """Route a 'new' request."""

    if path_tempfile is None:
        return None

    # TODO(fab): capture log output
    # TODO(damb): ... and handla different type of exceptions

#    try:
    cred = {}
    authdata = None

    url = route.RoutingURL(urlparse.urlparse(get_routing_url(
                current_app.config['ROUTING_SERVICE'])),
            query_params)
    dest = open(path_tempfile, 'wb')

    router = route.WebserviceRouter(url, query_params, postdata,
            dest, timeout, retries, retry_wait, threads)
    router()
#    except Exception:
#        return None
    
    # get contents of temp file
    if os.path.isfile(path_tempfile):
        return path_tempfile
    else:
        return None

# process_request ()

def get_routing_url(routing_service):
    """Get routing URL for routing service abbreviation."""
    
    try:
        server = settings.EIDA_NODES[routing_service]['services']['eida']\
            ['routing']['server']
    except KeyError:
        server = settings.EIDA_NODES[settings.DEFAULT_ROUTING_SERVICE]\
            ['services']['eida']['routing']['server']
        
    return "%s%s" % (server, settings.EIDA_ROUTING_PATH)

# get_routing_url ()
