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
from mediator.server import (general_request, httperrors, parameters, 
                             requestparser)

       
    
class DQRequestParser(requestparser.GeneralRequestParser):
    """Collect and merge all query parameters."""

    service_map = parameters.MediatorServiceMap()
    
    def __init__(self, query_args):
        super(DQRequestParser, self).__init__(query_args)
        
        print query_args
        
        self.service_map.set_services(query_args)
        
        print self.service_map.map
        print self.service_map.params
        print self.service_map.ws_params
    
        
    def service_enabled(self, service):
        return self.service_map.is_enabled(service)
    
    
    @property
    def event_params(self):
        return self.service_map.event_params
    
    @property
    def station_params(self):
        return self.service_map.station_params
    
    @property
    def waveform_params(self):
        return self.service_map.waveform_params
    
    @property
    def wfcatalog_params(self):
        return self.service_map.wfcatalog_params
 
 
class DQResource(general_request.GeneralResource):
    """Direct query resource."""
     
    def get(self):
        
        args = requestparser.general_reqparser.parse_args()
        
        # args['foo'], ...
        # print args
        
        new_args = DQRequestParser(args)
        #print new_args
        
        return self._process_request(
            new_args, mimetype=settings.STATION_MIMETYPE_TEXT)

        
    def post(self):
        
        # request.method == 'POST'
        # Note: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        args = requestparser.general_reqparser.parse_args()
        
        new_args = DQRequestParser(args)
        temp_postfile, new_args = self._process_post_args(new_args)
        
        return self._process_request(new_args, postfile=temp_postfile)


    
