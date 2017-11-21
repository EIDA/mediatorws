# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging

from flask import request
from webargs.flaskparser import use_args

from eidangservices import settings
from eidangservices.federator.server import general_request, schema, httperrors
from eidangservices.federator.utils import misc


class StationResource(general_request.GeneralResource):

    LOGGER = 'federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.StationSchema(), locations=('query',))
    def get(self, sncl_args, station_args):
        # request.method == 'GET'
        _context = {'request': request}

        args = {}
        # serialize objects
        s = schema.SNCLSchema(context=_context)
        args.update(s.dump(sncl_args).data)
        self.logger.debug('SNCLSchema (serialized): %s' % 
                s.dump(sncl_args).data)

        s = schema.StationSchema(context=_context)
        args.update(s.dump(station_args).data)
        self.logger.debug('StationSchema (serialized): %s' % 
                s.dump(station_args).data)

        # process request
        self.logger.debug('Request args: %s' % args)
        return self._process_request(args, self._get_result_mimetype(args), 
            path_tempfile=self.path_tempfile)

    # get ()

    @misc.use_fdsnws_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('form',)
    )
    @misc.use_fdsnws_args(schema.StationSchema(), locations=('form',))
    def post(self, sncl_args, station_args):
        # request.method == 'POST'

        # serialize objects
        s = schema.SNCLSchema()
        sncl_args = s.dump(sncl_args).data
        self.logger.debug('SNCLSchema (serialized): %s' % sncl_args)
        
        s = schema.StationSchema()
        station_args = s.dump(station_args).data
        self.logger.debug('StationSchema (serialized): %s' % station_args)
        self.logger.debug('Request args: %s' % station_args)

        # merge SNCL parameters
        sncls = misc.convert_sncl_dict_to_lines(sncl_args)
        self.logger.debug('SNCLs: %s' % sncls)
        sncls = '\n'.join(sncls) 

        return self._process_request(station_args,
                self._get_result_mimetype(station_args), 
                path_tempfile=self.path_tempfile,
                postdata=sncls)

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
