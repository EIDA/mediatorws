# -*- coding: utf-8 -*-
"""
Federator request handlers.

This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import os

import flask
from flask import current_app
from flask_restful import abort, reqparse, request, Resource

from federator import settings
from federator.server import httperrors, parameters
from federator.utils import fdsnws_fetch, misc


DATASELECT_MIMETYPE = 'application/vnd.fdsn.mseed'
STATION_MIMETYPE_XML = 'application/xml'
STATION_MIMETYPE_TEXT = 'text/plain'

FDSNWS_QUERY_VALUE_SEPARATOR_CHAR = '='

FDSNWSFETCH_OUTFILE_PARAM = '-o'
FDSNWSFETCH_SERVICE_PARAM = '-y'
FDSNWSFETCH_ROUTING_PARAM = '-u'
FDSNWSFETCH_QUERY_PARAM = '-q'
FDSNWSFETCH_POSTFILE_PARAM = '-p'


class GeneralResource(Resource):
    """Handler for general resource."""
    
    def _process_post_args(self, fetch_args):
        """Process POST parameters of a request."""
        
        # make temp file for POST pars (-p)
        temp_postfile = misc.get_temp_filepath()
        
        # fill in POST file parameter for fetch
        fetch_args.add(FDSNWSFETCH_POSTFILE_PARAM, temp_postfile)
        
        # print request.data

        # remove name=value pars from original POST request and make
        # them fetch parameters
        cleaned_post = ''
        req_lines = request.data.split('\n')
            
        for line in req_lines:
            
            # skip empty lines
            if not line:
                continue
            
            # check for name=value params
            check_param = line.split(FDSNWS_QUERY_VALUE_SEPARATOR_CHAR)
            
            if len(check_param) == 2:
                
                # add query params
                query_par = "%s=%s" % (
                    check_param[0].strip(), check_param[1].strip())
                fetch_args.add(FDSNWSFETCH_QUERY_PARAM, query_par)
            
            elif len(check_param) == 1:
                
                # copy line
                cleaned_post = "%s%s\n" % (cleaned_post, line)
            
            else:
                print "ignore illegal POST line: %s" % line
                continue

        # check that POST request is not empty
        if len(cleaned_post) == 0:
            print "empty POST request"
            raise httperrors.BadRequestError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())

        with open(temp_postfile, 'w') as fout:
            fout.write(cleaned_post)
            
        return temp_postfile, fetch_args


    def _process_request(self, fetch_args, mimetype, postfile=''):
        """Process request and send resulting file to client."""
        
        resource_path = process_request(fetch_args)
        
        # remove POST temp file
        if postfile and os.path.isfile(postfile):
            os.unlink(postfile)

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


class GeneralRequestTranslator(object):
    """Translate query params to commandline params."""

    def __init__(self, query_args):
        
        self.out_params = {}
        self.out_params[FDSNWSFETCH_QUERY_PARAM] = []
        
        # temp. output file
        self.out_params[FDSNWSFETCH_OUTFILE_PARAM] = misc.get_temp_filepath()
        
        # routing URL
        self.out_params[FDSNWSFETCH_ROUTING_PARAM] = get_routing_url(
            current_app.config['ROUTING'])
        
        # find params that have a direct mapping to fdsnws_fetch params
        for param, value in query_args.iteritems():
            if value is not None:
                
                # NOTE: param is the FDSN service parameter name from the HTTP 
                # web service query (could be long or short version)
                par_group_idx, par_name = parameters.parameter_description(
                    param)
                
                # check if valid web service parameter
                if par_group_idx is not None:
                    
                    fdsnfetch_par = parameters.ALL_QUERY_PARAMS[par_group_idx]\
                        [par_name]['fdsn_fetch_par']
                    
                    if fdsnfetch_par:
                        self.add(fdsnfetch_par, value)
                    
                    else:
                        # add as a query param
                        self.add(
                            FDSNWSFETCH_QUERY_PARAM, "%s=%s" % (param, value))
                
                else:
                    
                    raise httperrors.BadRequestError(
                        settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                        datetime.datetime.utcnow())
    
    
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
            check_param = pairs.split(FDSNWS_QUERY_VALUE_SEPARATOR_CHAR)
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
    """Call fdsnws_fetch with args, return path of result file."""
    
    tempfile_path = args.getpar(FDSNWSFETCH_OUTFILE_PARAM)
    if tempfile_path is None:
        return None
    
    # TODO(fab): capture log output

    print args.serialize()
    
    try:
        fdsnws_fetch.main(args.getlist())
    except Exception:
        return None
    
    # get contents of temp file
    if os.path.isfile(tempfile_path):
        return tempfile_path
    else:
        return None


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
