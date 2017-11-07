# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging
# FIXME(damb): Check if 'import os' needed!
import os

from flask import request
from webargs.flaskparser import use_args

from federator import settings
from federator.server import general_request, schema, httperrors
from federator.utils import misc                                      


class StationResource(general_request.GeneralResource):

    LOGGER = 'federator.station_resource'

    def __init__(self):
        super(StationResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.TemporalSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.StationSchema(), locations=('query',))
    def get(self, temporal_args, sncl_args, station_args):
        # request.method == 'GET'
        _context = {'request': request}

        args = {}
        # serialize objects
        s = schema.TemporalSchema(context=_context)
        args.update(s.dump(temporal_args).data)
        self.logger.debug('TemporalSchema (serialized): %s' %
                s.dump(temporal_args).data)

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

    @misc.use_fdsnws_args(schema.TemporalSchema(), locations=('form',))
    @misc.use_fdsnws_args(schema.SNCLSchema(), locations=('form',)) 
    @misc.use_fdsnws_args(schema.StationSchema(), locations=('form',))
    def post(self, temporal_args, sncl_args, station_args):
        # request.method == 'POST'

        # TODO(damb): At least one SNCL must be defined -> Delegated to context
        # dependent SNCLSchema validator

        # serialize objects
        s = schema.WFCatalogSchema()
        station_args = s.dump(station_args).data
        self.logger.debug('WFCatalogSchema (serialized): %s' % station_args)
        
        self.logger.debug('Request args: %s' % station_args)
        # serialize objects
        s = schema.TemporalSchema()
        self.logger.debug('TemporalSchema (serialized): %s' %
                s.dump(temporal_args).data)
        sncl_args.update(s.dump(temporal_args).data)

        self.logger.debug('SNCL args: %s' % sncl_args)
        # merge SNCL parameters
        sncls = misc.convert_sncl_dict_to_lines(sncl_args)
        self.logger.debug('SNCLs: %s' % sncls)

        self.logger.debug('Writing SNCLs to temporary post file ...')
        temp_postfile = misc.get_temp_filepath()
        with open(temp_postfile, 'w') as ofd:
            ofd.write('\n'.join(sncls))

        return self._process_request(station_args,
                self._get_result_mimetype(args), 
                path_tempfile=self.path_tempfile,
                path_postfile=temp_postfile)

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
