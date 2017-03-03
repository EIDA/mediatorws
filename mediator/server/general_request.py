# -*- coding: utf-8 -*-
"""
Mediator request handlers.

This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import os

import flask
from flask import current_app
from flask_restful import abort, reqparse, request, Resource

from mediator import settings
from mediator.server import httperrors, parameters
from mediator.utils import misc


QUERY_VALUE_SEPARATOR_CHAR = '='


class GeneralResource(Resource):
    """Handler for general resource."""

    def _process_request(self, fetch_args, mimetype, postfile=''):
        """Process request and send resulting file to client."""
        
        resource_out = process_request(fetch_args)
        
        # remove POST temp file
        #if postfile and os.path.isfile(postfile):
            #os.unlink(postfile)

        #if resource_path is None or os.path.getsize(resource_path) == 0:
            
            ## TODO(fab): get user-supplied error code
            #raise httperrors.NoDataError()
            
        #else:
            
            ## return contents of temp file
            #try:
                #return flask.send_file(resource_path, mimetype=mimetype)
            #except Exception:
                ## cannot send error code since response is already started
                ## TODO(fab): how to let user know of error?
                #pass
                
        return resource_out


class GeneralRequestParser(object):
    """Parse and sanity check request parameters."""

    def __init__(self, query_args):
        
        self.out_params = {}
        
    
    def add(self, param, value):
        
        # is it a list?
        if param in self.out_params and isinstance(self.out_params[param], list):
            self.out_params[param].append(value)
        else:
            
            # Note: overwrites existing params
            self.out_params[param] = value
            
 
    def getpar(self, param):
        """Get value of a given fdsnws_fetch command line parameter."""
        return self.out_params.get(param, None)
    
    
    def getquerypar(self, param):
        """Get value of a given param within list of fdsnws_fetch -q params."""
        
        for pairs in self.getpar(FDSNWSFETCH_QUERY_PARAM):
            check_param = pairs.split(QUERY_VALUE_SEPARATOR_CHAR)
            if check_param[0] == param:
                return check_param[1]
            
        return None

    
    def getlist(self):
        out = []
        for name, value in self.out_params.iteritems():
            
            if isinstance(value, list):
                
                # params that can be repeated (list)
                for list_value in value:
                    out.extend([name, list_value])
            else:    
                out.extend([name, value])
            
        return out
    
    
    def serialize(self):
        return ' '.join(self.getlist())
    

def get_request_parser(request_params, request_parser=None):
    """Create request parser and add query parameters."""
    
    if request_parser is None:
        the_parser = reqparse.RequestParser()
    else:
        the_parser = request_parser.copy()
        
    for _, req_par_data in request_params.iteritems():
        for param_alias in req_par_data['aliases']:
            the_parser.add_argument(param_alias, type=req_par_data['type'])
            
    return the_parser


def process_request(args):
    """Write result of mediated query to file."""
    
    #tempfile_path = args.getpar(FDSNWSFETCH_OUTFILE_PARAM)
    #if tempfile_path is None:
        #return None
    
    #tempfile_path = 'foo.tmp'
    # TODO(fab): capture log output

    #print args.serialize()
    
    try:
        #fdsnws_fetch.main(args.getlist())
        out = misc.process_dq(args.getlist())
    except Exception:
        return None
    
    return out
    # get contents of temp file
    #if os.path.isfile(tempfile_path):
        #return tempfile_path
    #else:
        #return None


def get_routing_url(routing_service):
    """Get routing URL for routing service abbreviation."""
    
    try:
        server = settings.EIDA_NODES[routing_service]['services']['eida']\
            ['routing']['server']
    except KeyError:
        server = settings.EIDA_NODES[settings.DEFAULT_ROUTING_SERVICE]\
            ['services']['eida']['routing']['server']
        
    return "%s%s" % (server, settings.EIDA_ROUTING_PATH)


# general query string parameters
general_reqparser = get_request_parser(parameters.GENERAL_PARAMS)
