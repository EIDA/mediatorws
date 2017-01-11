# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import os

import flask
from flask_restful import abort, reqparse, request, Resource

from federator import settings
from federator.server import general_request, httperrors, parameters
from federator.utils import misc                                      




class StationRequestTranslator(general_request.GeneralRequestTranslator):
    """Translate query params to commandline params."""

    def __init__(self, query_args):
        super(StationRequestTranslator, self).__init__(query_args)
        
        # add service commandline switch
        self.add(general_request.FDSNWSFETCH_SERVICE_PARAM, 'station')
        
        
class StationResource(general_request.GeneralResource):
    def get(self):
        
        args = station_reqparser.parse_args()
        
        # sanity check against query with no params
        arg_count = 0
        for n, v in args.iteritems():
            if v:
                arg_count += 1 
        
        if arg_count == 0:
            raise httperrors.BadRequestError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())
            
        fetch_args = StationRequestTranslator(args)
        
        # print fetch_args.serialize()
        
        return self._process_request(
            fetch_args, general_request.STATION_MIMETYPE)


    def post(self):

        # request.method == 'POST'
        # Note: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        args = station_reqparser.parse_args()
        fetch_args = StationRequestTranslator(args)
        
        temp_postfile, fetch_args = self._process_post_args(fetch_args)

        return self._process_request(
            fetch_args, general_request.STATION_MIMETYPE, 
            postfile=temp_postfile)
        

station_reqparser = general_request.get_request_parser(
    parameters.STATION_PARAMS, general_request.general_reqparser)


    
