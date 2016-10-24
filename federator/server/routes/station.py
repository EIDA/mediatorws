# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import os

import flask
from flask_restful import abort, reqparse, request, Resource

from federator import settings
from federator.server import general_request, httperrors
from federator.utils import misc                                      

station_reqparser = general_request.general_reqparser.copy()
station_reqparser.add_argument('minlatitude', type=float)
station_reqparser.add_argument('maxlatitude', type=float)
station_reqparser.add_argument('minlongitude', type=float)
station_reqparser.add_argument('maxlongitude', type=float)
station_reqparser.add_argument('latitude', type=float)
station_reqparser.add_argument('longitude', type=float)
station_reqparser.add_argument('minradius', type=float)
station_reqparser.add_argument('maxradius', type=float)

station_reqparser.add_argument('level', type=str)
station_reqparser.add_argument('includerestricted', type=bool)
station_reqparser.add_argument('includeavailability', type=bool)
station_reqparser.add_argument('updatedafter', type=str)
station_reqparser.add_argument('matchtimeseries', type=bool)


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
            raise httperrors.BadRequestError()
            
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
        
        
    
