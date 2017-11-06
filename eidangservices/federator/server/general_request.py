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
from flask import current_app, request
from flask_restful import abort, reqparse, Resource

from federator import settings
from federator.server import httperrors, parameters, route
from federator.utils import fdsnws_fetch, misc

try:
    # Python 2.x
    import urlparse
except ImportError:
    # Python 3.x
    import urllib.parse as urlparse


# -----------------------------------------------------------------------------
# constants
FDSNWS_QUERY_VALUE_SEPARATOR_CHAR = '='
FDSNWS_QUERY_SERVICE_PARAM = 'service'


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

    def _preprocess_post_request(self, request_handler):
        """Preprocess POST parameters of a request.
       
        When parsing the POST request data param=value pairs are removed and
        considered as query parameters i.e. added to the args dict.
        """
        
        # make temp file for POST pars (-p)
        temp_postfile = misc.get_temp_filepath()
        
        #self.logger.debug('Request data (POST): %s' % request.data)
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
                self.logger.debug('Adding query parameter: %s' % check_param)
                request_handler.add(check_param[0].strip(), 
                        check_param[1].strip())

            elif len(check_param) == 1:
                
                # copy line (automatically append)
                cleaned_post = "%s%s\n" % (cleaned_post, line)
                self.logger.debug('Adding POST content: "%s"' % line)
            
            else:
                self.logger.warn("Ignoring illegal POST line: %s" % line)
                continue

        # check that POST request is not empty
        if len(cleaned_post) == 0:
            self.logger.warn("Empty POST request")
            raise httperrors.BadRequestError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())

        
        self.logger.debug(
            'Writing cleaned POST content to temporary post file ...')
        with open(temp_postfile, 'w') as fout:
            fout.write(cleaned_post)
            
        return temp_postfile, request_handler

    # def _preprocess_post_request

    def _process_request(self, args, mimetype, path_tempfile, 
            path_postfile=None):
        """Process a request and send resulting file to client."""
        
        self.logger.debug(("Processing request: args={0}, path_tempfile={1}, "
                + "path_postfile={2}, timout={3}, retries={4}, "
                + "retry_wait={5}, threads={6}").format(args, path_tempfile,
                    path_postfile, current_app.config['ROUTING_TIMEOUT'], 
                    current_app.config['ROUTING_RETRIES'],
                    current_app.config['ROUTING_RETRY_WAIT'], 
                    current_app.config['NUM_THREADS']))

        resource_path = process_request(args, 
                path_tempfile=path_tempfile,
                path_postfile=path_postfile,
                timeout=current_app.config['ROUTING_TIMEOUT'],
                retries=current_app.config['ROUTING_RETRIES'],
                retry_wait=current_app.config['ROUTING_RETRY_WAIT'],
                threads=current_app.config['NUM_THREADS'])

        # remove POST temp file
        if path_postfile and os.path.isfile(path_postfile):
            os.unlink(path_postfile)

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

# get_request_parser ()

def process_request(query_params, 
        path_tempfile=None,
        path_postfile=None,
        timeout=settings.DEFAULT_ROUTING_TIMEOUT,
        retries=settings.DEFAULT_ROUTING_RETRIES,
        retry_wait=settings.DEFAULT_ROUTING_RETRY_WAIT, 
        threads=settings.DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS,
        # TODO(damb): Either use a logger or pass the log_level.
        verbose=True):
    """Route a 'new' request."""

    if path_tempfile is None:
        return None

    # TODO(fab): capture log output

    try:
        cred = {}
        authdata = None
        postdata = None

        if path_postfile:
            with open(path_postfile) as fd:
                postdata = fd.read()

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

# process_request

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

            path_postfile=None):
        """Process a request and send resulting file to client."""
        
        self.logger.debug(("Processing request: args={0}, path_temfile={1}, "
                + "path_postfile={2}, timout={3}, retries={4}, "
                + "retry_wait={5}, threads={6}").format(args, path_tempfile,
                    path_postfile, current_app.config['ROUTING_TIMEOUT'], 
                    current_app.config['ROUTING_RETRIES'],
                    current_app.config['ROUTING_RETRY_WAIT'], 
                    current_app.config['NUM_THREADS']))

        resource_path = process_request(args, 
                path_tempfile=path_tempfile,
                path_postfile=path_postfile,
                timeout=current_app.config['ROUTING_TIMEOUT'],
                retries=current_app.config['ROUTING_RETRIES'],
                retry_wait=current_app.config['ROUTING_RETRY_WAIT'],
                threads=current_app.config['NUM_THREADS'])

        # remove POST temp file
        if path_postfile and os.path.isfile(path_postfile):
            os.unlink(path_postfile)

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

# get_request_parser ()

def process_request(query_params, 
        path_tempfile=None,
        path_postfile=None,
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

        if path_postfile:
            with open(path_postfile) as fd:
                postdata = fd.read()

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

# process_request

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

