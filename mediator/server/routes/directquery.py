# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

from flask import current_app

from mediator import settings
from mediator.server import general_request, parameters, requestparser
  
    
class DQRequestParser(requestparser.GeneralRequestParser):
    """Collect and merge all query parameters."""

    service_map = parameters.MediatorServiceMap()
    
    def __init__(self, query_args):
        super(DQRequestParser, self).__init__(query_args)
        
        if current_app.debug:
            print "all query params: %s" % query_args
        
        self.service_map.set_services(query_args)
        
        if current_app.debug:
            print "service map: %s" % self.service_map.map
            print "prefixed params: %s" % self.service_map.params
            print "fdsnws params: %s" % self.service_map.ws_params
    
        
    def service_enabled(self, service):
        return self.service_map.is_enabled(service)
    
   
    def channel_constraint_enabled(self, service):
        return self.service_map.constraint_enabled(
            service, parameters.CHANNEL_PARAMETER_CONSTRAINT_TOKEN)
    
    
    def temporal_constraint_enabled(self, service):
        return self.service_map.constraint_enabled(
            service, parameters.TEMPORAL_PARAMETER_CONSTRAINT_TOKEN)
    
    
    def geographic_constraint_enabled(self, service):
        return self.service_map.constraint_enabled(
            service, parameters.GEOGRAPHIC_PARAMETER_CONSTRAINT_TOKEN)
    
    
    def get_time_interval(self, service, todatetime=False):
        return self.service_map.get_time_interval(service, todatetime)
    
    
    def get_sncl_params(self, service):
        return self.service_map.get_sncl_params(service)
    
    
    def get_geographic_params(self, service):
        return self.service_map.get_geographic_params(service)
    
    
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


    
