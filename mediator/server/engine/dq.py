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
    
    # 15 events, NO PICKS
    # http://arclink.ethz.ch/fdsnws/event/1/query?
    # starttime=2016-01-01&endtime=2017-01-01&minlatitude=46&maxlatitude=49&minlongitude=8&maxlongitude=11&minmagnitude=3.5&format=xml&includearrivals=true&formatted=true
    
    # mediator query:
    # e.starttime=2016-01-01&e.endtime=2017-01-01&e.minlatitude=46&e.maxlatitude=49&e.minlongitude=8&e.maxlongitude=11&e.minmagnitude=3.5&e.format=xml&e.includearrivals=true&formatted=true
    
    # with SNCL constraint
    # s.network=CH&s.channel=HHZ
    
    # TODO(fab): with SNCL/geometry constraint (no E geometry constraint)
    
    service = query_par.getpar('service')
    snclepochs = sncl.SNCLEpochs()
    
    cat = None
    replace_map = None
    
    if query_par.service_enabled('event'):
        
        print "event query: %s" % query_par.event_params['fdsnws']
        
        # event query
        event_service = query_par.getpar('eventservice')
        event_query_url = misc.get_event_query_endpoint(event_service)
        print "querying %s" % event_query_url

        # consume event service
        try:
            r = requests.get(
                event_query_url, params=query_par.event_params['fdsnws'])
        except Exception, e:
            raise RuntimeError, e
    
        cat_xml = str(r.text)
        #print cat_xml

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
    snclepochs, cat = sncl.get_sncl_epochs(
        query_par, service, cat, replace_map)
        
    #print len(cat)
    print str(snclepochs)
        
    # TODO(fab): apply S geometry constraints (remove whole events)
    # requires to consume service S in order to get station coords

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
    
    # TODO: check for wild cards in SNCLs
    # based on that list: consume dataselect/station

    # POST to federator for target service
    if misc.query_federator_for_target_service(
            outfile, service, query_par, snclepochs):
        return outfile
    else:
        raise httperrors.NoDataError()
