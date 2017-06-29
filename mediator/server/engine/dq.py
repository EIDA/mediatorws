# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import copy
import os
import sys
import tempfile


import flask
from flask import make_response
from flask_restful import Resource

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
            raise httperrors.BadRequestError()     

    service = query_par.getpar('service')
    snclepochs = sncl.SNCLEpochs()
    
    cat = None
    replace_map = None
    
    if query_par.service_enabled('event'):
        
        event_query_par = query_par.event_params['fdsnws']
        
        # If target service is not 'event' (i.e., pick information is needed),
        # or if there are channel parameters for event,
        # add query parameter 'includearrivals'
        if service != 'event' or (
            service == 'event' and \
                query_par.channel_constraint_enabled('event')):
            event_query_par['includearrivals'] = 'true'
            
        print "event query: %s" % event_query_par
        
        event_service = query_par.getpar('eventservice')
        event_query_url = misc.get_event_query_endpoint(event_service)
        print "querying %s" % event_query_url

        # consume event service
        # TODO(fab): 301 moved permanently (e.g., USGS moved to https)
        try:
            r = requests.get(event_query_url, params=event_query_par)
        except Exception, e:
            print "event service query failed with error: %s" % e
            raise httperrors.NoDataError()
    
        # check for non-zero response, check for XML response
        if r.text:
            cat_xml = str(r.text)
            #print cat_xml
        else:
            raise httperrors.NoDataError()

        # target service event w/o additional event sncl filtering requested: 
        # we are done
        # sncl constraints of S, W, and Q namespaces are ignored
        # NOTE: don't catch output that is invalid QuakeML (e.g., HTML
        # error message returned by event service)
        if service == 'event' and not query_par.channel_constraint_enabled(
            'event'):
            
            print "writing raw event catalog"
            if misc.write_response_string_to_file(outfile, cat_xml):
                return outfile
            else:
                raise httperrors.NoDataError()
            
        # NOTE: ObsPy fails on illegal ResourceIdentifiers.
        # Replace all publicIDs with safe random temp string,
        # save mapping from temp to original ID, in final serialized document,
        # replace all temp IDs.
        cat, replace_map = eventcatalog.get_obspy_catalog(cat_xml)
        print "read event catalog, %s events" % (len(cat))

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
            raise httperrors.NoDataError()
            
    #print str(snclepochs)
    #print len(snclepochs.sncle)
    #print snclepochs.empty
    
    if snclepochs.empty:
        print "snclepochs empty"
        raise httperrors.NoDataError()
    
    # TODO(fab): check if final query to target service is necessary
    # TODO(fab): if target service in station and inventory is not None,
    # serialize inventory
    
    # POST to federator for target service
    if misc.query_federator_for_target_service(
            outfile, service, query_par, snclepochs):
        return outfile
    else:
        raise httperrors.NoDataError()
