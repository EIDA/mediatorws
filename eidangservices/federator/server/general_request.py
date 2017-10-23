# -*- coding: utf-8 -*-
"""
Federator request handlers.

This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging
import os

from future.utils import iteritems

import flask
from flask import current_app
from flask_restful import abort, reqparse, request, Resource

from federator import settings
from federator.server import httperrors, parameters, route
from federator.utils import fdsnws_fetch, misc

try:
    # Python 2.x
    import urlparse
except ImportError:
    # Python 3.x
    import urllib.parse as urlparse


FDSNWS_QUERY_VALUE_SEPARATOR_CHAR = '='
FDSNWS_QUERY_SERVICE_PARAM = 'service'

FDSNWSFETCH_OUTFILE_PARAM = '-o'
FDSNWSFETCH_SERVICE_PARAM = '-y'
FDSNWSFETCH_ROUTING_PARAM = '-u'
FDSNWSFETCH_QUERY_PARAM = '-q'
FDSNWSFETCH_POSTFILE_PARAM = '-p'


class GeneralResource(Resource):
    """Handler for general resource."""

    LOGGER = "federator.general_resource"

    def __init__(self):
        self.logger = logging.getLogger(self.LOGGER)
        self.__path_tempfile = misc.get_temp_filepath() 
   
    # __init__ ()

    @property
    def path_tempfile(self):
        return self.__path_tempfile

    def _process_post_args(self, fetch_args):
        """Process POST parameters of a request."""
        
        # make temp file for POST pars (-p)
        temp_postfile = misc.get_temp_filepath()
        
        # fill in POST file parameter for fetch
        fetch_args.add(FDSNWSFETCH_POSTFILE_PARAM, temp_postfile)
        
        # print request.data

        # remove name=value pairs from original POST request and convert them
        # to fdsnws_fetch parameters
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
        
        self.logger.debug("fetch_args: %s" % fetch_args)

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

    def _process_new_request(self, args, mimetype, path_tempfile, 
            postfile=''):
        """Process a new request and send resulting file to client."""
        
        resource_path = process_new_request(args, 
                path_tempfile=path_tempfile,
                timeout=current_app.config['ROUTING_TIMEOUT'],
                retries=current_app.config['ROUTING_RETRIES'],
                retry_wait=current_app.config['ROUTING_RETRY_WAIT'],
                threads=current_app.config['NUM_THREADS'])

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

    # _process_new_request ()

# class GeneralResource


class RequestParameterHandler(object):
    """
    Implementation of a parameter handler performing fixes and corrections at
    query parameters.
    """

    LOGGER = 'federator.request_parameter_handler'

    def __init__(self, query_args):
        self.logger = logging.getLogger(self.LOGGER)
        
        self.__params = {}

        for param, value in iteritems(query_args):
            if value is not None:
                self.logger.debug(
                    'Processing query argument: param=%s, value=%s' % 
                    (param, value))
                # NOTE(fab): param is the FDSN service parameter name from the
                # HTTP web service query (could be long or short version)
                par_group_idx, par_name = self._is_defined_parameter(param)
                
                # check if valid web service parameter
                if par_group_idx is not None:
                    
                    # TODO(damb): Add a valid service parameter
                    value = self._fix_param_value(param, value)

                    self.__params[param] = value 
                
                else:
                    raise httperrors.BadRequestError(
                        settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                        datetime.datetime.utcnow())
    
    # __init__ ()

    @property 
    def params(self):
        return self.__params


    def add(self, param, value):
        # NOTE(damb): overwrites existing params
        self.__params[param] = value

    # add ()

    def _fix_param_value(self, param, value):
        """Check format of parameter values and fix, if necessary."""
        return parameters.fix_param_value(param, value)

    # _fix_param_value ()

    def _is_defined_parameter(self, param):
        """Check if a given query parameter has a definition and return it. If
        not found, return None."""
        return parameters.parameter_description(param)

    # _is_defined_parameter ()

# class RequestParameterHandler

# -----------------------------------------------------------------------------
# NOTE(damb): fdnsws_fetch modularization makes request translation probably
# obsolete.
class GeneralRequestTranslator(object):
    """Translate query params to commandline params."""

    LOGGER = 'federator.general_request_translator'

    def __init__(self, query_args):
        self.logger = logging.getLogger(self.LOGGER)
        
        self.out_params = {}
        self.out_params[FDSNWSFETCH_QUERY_PARAM] = []
        
        # temp. output file
        self.out_params[FDSNWSFETCH_OUTFILE_PARAM] = misc.get_temp_filepath()
        
        # routing URL
        self.out_params[FDSNWSFETCH_ROUTING_PARAM] = get_routing_url(
            current_app.config['ROUTING_SERVICE'])
        
        self.logger.debug('Translating request parameters ...')

        # find params that have a direct mapping to fdsnws_fetch params
        for param, value in query_args.iteritems():
            if value is not None:
                
                print('p=%s, v=%s' % (param, value))    
                # NOTE: param is the FDSN service parameter name from the HTTP 
                # web service query (could be long or short version)
                par_group_idx, par_name = parameters.parameter_description(
                    param)
                
                # check if valid web service parameter
                if par_group_idx is not None:
                    
                    value = parameters.fix_param_value(param, value)
                    
                    fdsnfetch_par = parameters.ALL_QUERY_PARAMS[par_group_idx]\
                        [par_name]['fdsn_fetch_par']
                    
                    # NOTE(damb): Parameters either are added as a
                    # fdsnfetch param or as a query param
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

    try:
        fdsnws_fetch.main(args.getlist())
    except Exception:
        return None
    
    # get contents of temp file
    if os.path.isfile(tempfile_path):
        return tempfile_path
    else:
        return None


def process_new_request(query_params, path_tempfile=None,
        timeout=settings.DEFAULT_ROUTING_TIMEOUT,
        retries=settings.DEFAULT_ROUTING_RETRIES,
        retry_wait=settings.DEFAULT_ROUTING_RETRY_WAIT, 
        threads=settings.DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS,
        # TODO(damb): Either use a logger or pass the log_level.
        verbose=False):
    """Route a 'new' request."""

    if path_tempfile is None:
        return None

    # TODO(fab): capture log output

    try:
        cred = {}
        authdata = None
        postdata = None

        url = route.RoutingURL(urlparse.urlparse(get_routing_url(
                    current_app.config['ROUTING_SERVICE'])),
                query_params)
        dest = open(path_tempfile, 'wb')

        route.route(url, query_params, cred, authdata, postdata, dest, timeout,
              retries, retry_wait, threads, verbose)
    except Exception:
        return None
    
    # get contents of temp file
    if os.path.isfile(path_tempfile):
        return path_tempfile
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
