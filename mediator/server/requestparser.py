# -*- coding: utf-8 -*-
"""
Mediator request parser.

This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import os

import flask
from flask_restful import reqparse, request

from mediator import settings
from mediator.server import httperrors, parameters
from mediator.server.engine import dq
from mediator.utils import misc


QUERY_VALUE_SEPARATOR_CHAR = '='


class GeneralRequestParser(object):
    """Parse and sanity check request parameters."""

    def __init__(self, query_args):
        """
        query_args are the flask request parameters, as returned from 
        the parse_args() method of reqparse.RequestParser. The ones that are 
        not set in the request are None. Note that long form and aliases are
        all present.
        
        Params that are not None are sanity-checked and copied to out_params.
        
        """
        
        self.out_params = {}
        
        # parse flask request parameters
        for param, value in query_args.iteritems():
            if value is not None:
                
                # NOTE: param is the FDSN service parameter name from the HTTP 
                # web service query (could be long or short version)
                par_group_idx, par_name = parameters.parameter_description(
                    param)
                
                # check if valid web service parameter
                if par_group_idx is not None:
                    
                    # fix, e.g., timestamp values
                    value = parameters.fix_param_value(par_name, value)
                    descr = parameters.get_parameter_description(
                        par_group_idx, par_name)
                    
                    self.add(par_name, descr, value)
                
                else:
                    
                    raise httperrors.BadRequestError(
                        settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                        datetime.datetime.utcnow())
                
        # walk through missing mandatory parameters and add default values
        for section_idx, section in enumerate(
            parameters.ALL_MEDIATOR_QUERY_PARAMS):
            
            for name, par in section.iteritems():
                if self.getpar(name) is None and 'mandatory' in par and \
                    par['mandatory']:
                        
                    descr = parameters.get_parameter_description(
                        section_idx, name)
                    
                    self.add(name, descr, par['default'])
        
    
    def add(self, param, descr, value):
        self.out_params[param] = dict(descr=descr, value=value)
            
 
    def getpar(self, param):
        """Get value of a query parameter."""
        
        match = self.out_params.get(param, None)
        if match is None:
            return None
        else:
            return match['value']


    def getlist(self):
        """This returns a list with par1, val1, par2, val2, ..."""
        
        out = []
        for name, par in self.out_params.iteritems():
            out.extend([name, par['value']])
            
        return out
    
    
    def serialize(self):
        """Return a  string serialization of the parameters object."""
        
        out_str = ''
        for name, par in self.out_params.iteritems():
            out_str += "%s=%s " % (name, par['value'])
            
        return out_str
    
    
    def __str__(self):
        return self.serialize()
    

def get_request_parser(request_params, request_parser=None):
    """
    Create request parser and add possible/allowed query parameters
    and their types to the request parser.
    
    """
    
    if request_parser is None:
        the_parser = reqparse.RequestParser()
    else:
        the_parser = request_parser.copy()
    
    if not isinstance(request_params, (list, tuple)):
        request_params = (request_params,)
    
    for param_section in request_params:
        for _, req_par_data in param_section.iteritems():
            for param_alias in req_par_data['aliases']:
                the_parser.add_argument(param_alias, type=req_par_data['type'])
            
    return the_parser


# general query string parameters
general_reqparser = get_request_parser(parameters.ALL_MEDIATOR_QUERY_PARAMS)
