# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging
# FIXME(damb): Check if 'import os' needed!
import os

import flask
from flask import request
from flask_restful import abort, reqparse, Resource

from federator import settings
from federator.server import general_request, httperrors, parameters
from federator.utils import misc                                      


class StationRequestHandler(general_request.RequestParameterHandler):
    """Handle request parameters for service=station"""
        
    def __init__(self, query_args):
        super(StationRequestHandler, self).__init__(query_args)

        self.add(general_request.FDSNWS_QUERY_SERVICE_PARAM, 'station')

# class StationRequestHandler


class StationResource(general_request.GeneralResource):

    LOGGER = 'federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    def get(self):
        
        # request.method == 'GET'

        args = station_reqparser.parse_args()
        self.logger.debug('StationResource (GET) args: %s' % args)

        # sanity check against query with no params
        arg_count = 0
        for n, v in args.iteritems():
            if v:
                arg_count += 1 
        
        if arg_count == 0:
            raise httperrors.BadRequestError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())
            
        args = StationRequestHandler(args).params
        self.logger.debug("Request query parameters: %s." % args)

        return self._process_request(
            args, self._get_result_mimetype(args), 
            path_tempfile=self.path_tempfile)

    # get ()

    def post(self):

        # request.method == 'POST'
        # Note: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        args = station_reqparser.parse_args()
        self.logger.debug('StationResource (POST) args: %s' % args)

        request_handler = StationRequestHandler(args)

        self.logger.debug('Preprocessing POST request data ...')
        temp_postfile, request_handler = self._preprocess_post_request(
                request_handler)
        args = request_handler.params
        self.logger.debug("Request query parameters: %s." % args)

        return self._process_request(
            args, self._get_result_mimetype(args), 
            path_tempfile=self.path_tempfile, path_postfile=temp_postfile)

    # post ()
    
    def _get_result_mimetype(self, args):
        """Return result mimetype (either XML or plain text."""
        try:
            args['format'] == 'text'
            return settings.STATION_MIMETYPE_TEXT
        except KeyError:
            return settings.STATION_MIMETYPE_XML

    # _get_result_mimetype () 
            
# class StationResource
        

station_reqparser = general_request.get_request_parser(
    parameters.STATION_PARAMS, general_request.general_reqparser)
