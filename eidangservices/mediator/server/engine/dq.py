# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import copy
import datetime
import os
import sys
import tempfile


import flask
from flask import make_response
from flask_restful import Resource, request

from intervaltree import Interval, IntervalTree

import requests

from mediator import settings
from mediator.server import httperrors, parameters, sncl
from mediator.utils import eventcatalog, misc


def process_dq(query_par, outfile):
    """
    Process direct query.
    
    query_par: DQRequestParser object
    
    """
    
    # event service: GET only
    # SC3 implementation: no catalogs parameter, contributors parameter are
    #  mapped to agencyIDs, they must be defined in
    #  @DATADIR@/share/fdsn/contributors.xml
    #  eventid (optional) is implemented, is a publicID

    # exclude a few service parameter combinations that make no sense
    if query_par.service_enabled('station') and \
        query_par.service_enabled('event'):
        
        if (query_par.channel_constraint_enabled('station') and \
            query_par.temporal_constraint_enabled('station')) or (
            
            query_par.channel_constraint_enabled('station') and \
            query_par.channel_constraint_enabled('event')):
            
            print "error: bad service parameter combination"
            raise httperrors.BadRequestError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())     

    service = query_par.getpar('service')
    snclepochs = sncl.SNCLEpochs()
    
    catalogs = []
    replace_maps = []
    
    cat = None
    replace_map = None
    
    if query_par.service_enabled('event'):
        
        event_query_par = query_par.event_params['fdsnws']
        
        print event_query_par
        
        # If target service is not 'event' (i.e., pick information is needed),
        # or if there are channel parameters for event,
        # add query parameter 'includearrivals'
        # TODO(fab): make includearrivals 'true' in issued query
        if service != 'event' or (
            service == 'event' and \
                query_par.channel_constraint_enabled('event')):
            event_query_par['includearrivals'] = 'true'
            
        print "event query: %s" % event_query_par
        
        event_service_endpoints = misc.get_event_service_endpoints(
            query_par, default=False)
        
        if not event_service_endpoints:
            print "error: no valid event service endpoint given"
            raise httperrors.NoDataError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())
        
        elif len(event_service_endpoints) > 1 and service == 'event':
            print "error: multiple eventservices not allowed for target "\
                "service event"
            raise httperrors.BadRequestError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())     
        
        print "%s valid event query endpoint(s)" % len(event_service_endpoints)
        
        for endpoint in event_service_endpoints:

            print "querying endpoint %s" % endpoint
            
            # consume event service
            # TODO(fab): 301 moved permanently (e.g., USGS moved to https)
            try:
                r = requests.get(endpoint, params=event_query_par)
                print "issued url %s" % r.url
                
            except Exception, e:
                print "event service query url failed with error: %s" % (e)
                raise httperrors.NoDataError(
                    settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                    datetime.datetime.utcnow())
    
            cat_xml = ''
            
            if r.text:
                cat_xml = unicode(r.text)
                #print cat_xml
                    
            # check for non-zero response, check for XML response
            if len(event_service_endpoints) == 1:
                
                if not cat_xml:
                    raise httperrors.NoDataError(
                        settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                        datetime.datetime.utcnow())
                
                elif service == 'event' and not \
                    query_par.channel_constraint_enabled('event'):
                        
                    # target service event w/o additional event sncl filtering 
                    # requested: we are done
                    # sncl constraints of S, W, and Q namespaces are ignored
                    # NOTE: don't catch output that is invalid QuakeML (e.g., 
                    # HTML error message returned by event service)
                    
                    if misc.write_response_string_to_file(outfile, cat_xml):
                        print "writing raw event catalog"
                        return outfile
                    else:
                        raise httperrors.NoDataError(
                            settings.FDSN_SERVICE_DOCUMENTATION_URI, 
                            request.url, datetime.datetime.utcnow())
            
            if not cat_xml:
                print "no valid response, skipping..."
                continue
            
            # NOTE: ObsPy fails on illegal ResourceIdentifiers.
            # Replace all publicIDs with safe random temp string,
            # save mapping from temp to original ID, in final serialized document,
            # replace all temp IDs.
            cat_success = False
            try:
                the_cat, the_replace_map = eventcatalog.get_obspy_catalog(
                    cat_xml)
                cat_success = True
                print "read event catalog, %s events" % (len(the_cat))
                
            except RuntimeError, e:
                print "catalog read failed: %s, skipping" % e 
            
            if cat_success and len(the_cat) > 0:
                catalogs.append(the_cat)
                replace_maps.append(the_replace_map)

        # merge overall catalogs
        if len(catalogs) > 0:
            print "merging {} catalogs".format(len(catalogs))
            cat, replace_map = eventcatalog.merge_catalogs(
                catalogs, replace_maps)
            print "overall {} events".format(len(cat))
        else:
            print "no event catalog data (all empty)"
            raise httperrors.NoDataError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())
    
    # get sncl epochs (event and non-event)
    # may require to consume service S in order to get station coords and
    # available channels
    snclepochs, cat, inventory = sncl.get_sncl_epochs(
        query_par, service, cat, replace_map)
        
    #print len(cat)
    print str(snclepochs)
    
    
    # TODO(fab): check for wild cards in SNCLs
    # based on that list: consume dataselect/station
    
    # re-serialize filtered catalog w/ ObsPy
    if service == 'event':
        if eventcatalog.restore_catalog_to_file(outfile, cat, replace_map):
            return outfile
        else:
            raise httperrors.NoDataError(
                settings.FDSN_SERVICE_DOCUMENTATION_URI, request.url,
                datetime.datetime.utcnow())
            
    #print str(snclepochs)
    #print len(snclepochs.sncle)
    #print snclepochs.empty
    
    if snclepochs.empty:
        print "snclepochs empty"
        raise httperrors.NoDataError()
    
    # TODO(fab): check if final query to target service is necessary
    # TODO(fab): if target service is 'station' and inventory is not None,
    # serialize inventory
    
    # POST to federator for target service
    print "final federator query"
    if misc.query_federator_for_target_service(
            outfile, service, query_par, snclepochs):
        return outfile
    else:
        raise httperrors.NoDataError()
