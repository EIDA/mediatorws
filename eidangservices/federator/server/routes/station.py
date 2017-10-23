# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging
import os

import flask
from flask_restful import abort, reqparse, request, Resource

from federator import settings
from federator.server import general_request, httperrors, parameters
from federator.utils import misc                                      



class StationRequestHandler(general_request.RequestParameterHandler):
    """Handle request parameters for service=station"""
        
    def __init__(self, query_args):
        
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
        
        args = station_reqparser.parse_args()
        self.logger.debug('StationResource args: %s' % args)

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

        # TODO(damb): Migrate function identifier to self._process_request
        return self._process_new_request(
            args, self._get_result_mimetype(args), 
            path_tempfile=self.path_tempfile)


    def post(self):

        # request.method == 'POST'
        # Note: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        args = station_reqparser.parse_args()
        # TODO(damb): Use the StationRequestHandler!
        fetch_args = StationRequestTranslator(args)
        
        temp_postfile, fetch_args = self._process_post_args(fetch_args)

        return self._process_request(
            fetch_args, self._get_result_mimetype(fetch_args), 
            postfile=temp_postfile)
    
    def _get_result_mimetype(self, args):
        """Return result mimetype (either XML or plain text."""
        try:
            args['format'] == 'text'
            return settings.STATION_MIMETYPE_TEXT
        except KeyError:
            return settings.STATION_MIMETYPE_XML

    # _get_result_mimetype () 
            

    
    def _get_result_mimetype_post(self, fetch_args):
        """Return result mimetype (either XML or plain text."""
        
        if fetch_args.getquerypar('format') == 'text':
            return settings.STATION_MIMETYPE_TEXT
        else:
            return settings.STATION_MIMETYPE_XML
        

station_reqparser = general_request.get_request_parser(
    parameters.STATION_PARAMS, general_request.general_reqparser)
