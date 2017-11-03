# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <wfcatalog.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/10/26        V0.1    Daniel Armbruster
# =============================================================================
"""
This file is part of the EIDA mediator/federator webservices.
"""
import datetime 
import logging

from future.utils import iteritems

from flask import request
from webargs.flaskparser import use_args

from federator import settings
from federator.server import general_request, schema, httperrors 
from federator.utils import misc


class WFCatalogResource(general_request.GeneralResource):

    LOGGER = 'federator.wfcatalog_resource'

    def __init__(self):
        super(WFCatalogResource, self).__init__()
        self.logger = logging.getLogger(self.LOGGER)

    @use_args(schema.TemporalSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.SNCLSchema(
        context={'request': request}), 
        locations=('query',)
    )
    @use_args(schema.WFCatalogSchema(), locations=('query',))
    def get(self, temporal_args, sncl_args, wfcatalog_args):
        # request.method == 'GET'
        _context = {'request': request}
        # sanity check - starttime and endtime must be specified
        print(temporal_args)
        if not temporal_args or not all(len(temporal_args[t]) == 1 for t in
            ('starttime', 'endtime')):
            raise httperrors.BadRequestError(
                    settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                    datetime.datetime.utcnow()
            )

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

        s = schema.WFCatalogSchema(context=_context)
        args.update(s.dump(wfcatalog_args).data)
        self.logger.debug('WFCatalogSchema (serialized): %s' % 
                s.dump(wfcatalog_args).data)

        # process request
        self.logger.debug('Request args: %s' % args)
        return self._process_request(args, settings.WFCATALOG_MIMETYPE,
            path_tempfile=self.path_tempfile)

    # get ()

    @misc.use_fdsnws_args(schema.TemporalSchema(), locations=('form',))
    @misc.use_fdsnws_args(schema.SNCLSchema(), locations=('form',)) 
    @misc.use_fdsnws_args(schema.WFCatalogSchema(), locations=('form',))
    def post(self, temporal_args, sncl_args, wfcatalog_args):
        # request.method == 'POST'
        sncl_args.update(temporal_args)
        # TODO(damb): check if at least one SNCL is defined
#        if (not sncl_args or 
#            len(set(len(v) for k,v in sncl_args.iteritems())) <= 1):
#            raise httperrors.BadRequestError(
#                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
#                datetime.datetime.utcnow())

        # serialize objects
        s = schema.WFCatalogSchema()
        wfcatalog_args = s.dump(wfcatalog_args).data
        self.logger.debug('WFCatalogSchema (serialized): %s' % wfcatalog_args)
        
        self.logger.debug('Request args: %s' % wfcatalog_args)
        # serialize objects
        s = schema.TemporalSchema()
        self.logger.debug('TemporalSchema (serialized): %s' %
                s.dump(temporal_args).data)
        sncl_args.update(s.dump(temporal_args).data)

        self.logger.debug('SNCL args: %s' % sncl_args)
        # merge SNCL parameters
        sncls = zip(*sncl_args.values())
        sncls = [' '.join(sncl) for sncl in sncls]
        self.logger.debug('SNCLs: %s' % sncls)

        self.logger.debug('Writing SNCLs to temporary post file ...')
        temp_postfile = misc.get_temp_filepath()
        with open(temp_postfile, 'w') as ofd:
            ofd.write('\n'.join(sncls))

        return self._process_request(wfcatalog_args, 
                settings.WFCATALOG_MIMETYPE, path_tempfile=self.path_tempfile,
                path_postfile=temp_postfile)

    # post ()

# class WFCatalogResource
