# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""


import datetime
import os

#import flask
#from flask_restful import abort, reqparse, request, Resource

from mediator import settings
from mediator.server import general_request, httperrors, parameters
from mediator.utils import misc


class DQRequestParser(general_request.GeneralRequestParser):
    """Translate query params to commandline params."""

    def __init__(self, query_args):
        super(DQRequestParser, self).__init__(query_args)


class DQResource(general_request.GeneralResource):
    """Direct query resource."""
     
    def get(self):
        
        args = dq_reqparser.parse_args()
        new_args = DQRequestParser(args)

        return self._process_request(
            new_args, mimetype=settings.STATION_MIMETYPE_TEXT)

        
    def post(self):
        
        # request.method == 'POST'
        # Note: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        args = dq_reqparser.parse_args()
        new_args = DQRequestParser(args)
        
        temp_postfile, new_args = self._process_post_args(new_args)
        
        return self._process_request(new_args, postfile=temp_postfile)
        

dq_reqparser = general_request.get_request_parser(
    parameters.DATASELECT_PARAMS, general_request.general_reqparser)


    
