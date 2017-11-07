# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import logging

import flask
from flask import request
from webargs.flaskparser import use_args


class DataselectResource(general_request.GeneralResource):
    """
    Handler for dataselect service route.
    
    """
    LOGGER = 'federator.dataselect_resource'

    def __init__(self):
        super(DataselectResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.DataselectSchema())
    def get(self, sncl_args, args):
        # request.method == 'GET'
        _context = {'request': request}

        # serialize objects
        s = schema.SNCLSchema(context=_context)
        args.update(s.dump(sncl_args).data)
        self.logger.debug('SNCLSchema (serialized): %s' % 
                s.dump(sncl_args).data)

        # process request
        self.logger.debug('Request args: %s' % args)
        return self._process_request(args, settings.DATASELECT_MIMETYPE,
            path_tempfile=self.path_tempfile)

    # get ()

        
    @misc.use_fdsnws_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('form',)
    )
    @misc.use_fdsnws_args(schema.DataselectSchema())
    def post(self, sncl_args, args):
        # request.method == 'POST'
        # NOTE: must be sent as binary to preserve line breaks
        # curl: --data-binary @postfile --header "Content-Type:text/plain"

        # serialize objects
        s = schema.SNCLSchema()
        sncl_args = s.dump(sncl_args).data
        self.logger.debug('SNCLSchema (serialized): %s' % sncl_args)

        self.logger.debug('Request args: %s' % args)
        # merge SNCL parameters
        sncls = misc.convert_sncl_dict_to_lines(sncl_args)
        self.logger.debug('SNCLs: %s' % sncls)

        self.logger.debug('Writing SNCLs to temporary post file ...')
        temp_postfile = misc.get_temp_filepath()
        with open(temp_postfile, 'w') as ofd:
            ofd.write('\n'.join(sncls))

        return self._process_request(args, settings.DATASELECT_MIMETYPE, 
            path_tempfile=self.path_tempfile, path_postfile=temp_postfile)

    # post ()

# class DataselectResource
