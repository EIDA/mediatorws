# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging
import os

import flask
from flask import request
from flask_restful import abort, reqparse, Resource

from eidangservices import settings

from eidangservices.federator.server import general_request, httperrors, parameters
from eidangservices.federator.utils import misc


class DataselectRequestHandler(general_request.RequestParameterHandler):
    """Translate query params to commandline params."""

    def __init__(self, query_args):
        super(DataselectRequestHandler, self).__init__(query_args)
        
        # add service commandline switch
        self.add(general_request.FDSNWS_QUERY_SERVICE_PARAM, 'dataselect')
        
        # TODO(damb): Reimplement sanity check!
        # sanity check - for GET, need at least one of SNCL and network can't be
        # just wildcards
        # this is to prevent people from typing the blank query URL into the
        # browser and thus making a huge request
        """
        if request.method == 'GET' and self.getpar('-S') is None and \
            self.getpar('-C') is None and self.getpar('-L') is None and (
                self.getpar('-N') is None or self.getpar('-N') in ('*', '?', '??')):
                
                raise httperrors.BadRequestError(
                    settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                    datetime.datetime.utcnow())
        """

class DataselectResource(general_request.GeneralResource):
    """
    Handler for dataselect service route.
    
    """
    LOGGER = 'federator.dataselect_resource'

    def __init__(self):
        super(DataselectResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

     
    def get(self):
        
        # request.method == 'GET'

        args = dataselect_reqparser.parse_args()
        self.logger.debug('DataselectResource (GET) args: %s' % args)

        args = DataselectRequestHandler(args).params

        return self._process_request(
            args, settings.DATASELECT_MIMETYPE, 
            path_tempfile=self.path_tempfile)

    # get ()

        
    def post(self):
        
        # request.method == 'POST'
        # Note: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"
        args = dataselect_reqparser.parse_args()
        self.logger.debug('DataselectResource (POST) args: %s' % args)

        request_handler = DataselectRequestHandler(args)
        temp_postfile, request_handler = self._preprocess_post_request(
                request_handler)
        args = request_handler.params
        
        self.logger.debug("Request query parameters: %s." % args)

        # TODO(damb): Migrate function identifier to self._process_request
        return self._process_request(
            args, settings.DATASELECT_MIMETYPE, 
            path_tempfile=self.path_tempfile, path_postfile=temp_postfile)

    # post ()

dataselect_reqparser = general_request.get_request_parser(
    parameters.DATASELECT_PARAMS, general_request.general_reqparser)


    
