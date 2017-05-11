# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import copy
import os
import re
import tempfile
import uuid

from operator import itemgetter

import flask
from flask import make_response
from flask_restful import Resource

import obspy
import requests

from mediator import settings
from mediator.server import parameters


# IDs from SC3 that do not validate against QuakeML 1.2_
# - arrival publicIDs from ETHZ (replace all publicIDs)
# - filterID
# - pickID (OK from ETHZ but may be invalid elsewhere)
RE_EVENT_XML_PUBLIC_ID = (
    re.compile(r'publicID="(.+?)"'), re.compile(r'publicID=\'(.+?)\''),
    re.compile(r'<filterID>(.+?)<\/filterID>'), 
    re.compile(r'<pickID>(.+?)<\/pickID>'))

PUBLIC_ID_LOCAL_PREFIX = 'smi:local/'


def sanitize_catalog_public_ids(cat_xml):
    """
    Replace all public IDs in a QuakeML instance with well-behaved
    place holders. Return string with replacements, and dict of original
    and replaced matches.
    
    """
    
    replace_list = []
    replace_map = {}
    
    # find public IDs in QuakeML instance and get random replacement
    for pattern in RE_EVENT_XML_PUBLIC_ID:
        for m in re.finditer(pattern, cat_xml):
            public_id = m.group(1)
            replacement = "%s%s" % (PUBLIC_ID_LOCAL_PREFIX, str(uuid.uuid4()))
            
            #print "replace %s with %s" % (public_id, replacement)
            replace_list.append(
                dict(orig=public_id, repl=replacement, start=m.start(1), 
                    end=m.end(1)))
                
            replace_map[replacement] = public_id
    
    # sort replace list by start index, descending
    replace_list = sorted(replace_list, key=itemgetter('start'), reverse=True)
    
    # replace public IDs by position (start at end of text so that indices are
    # not compromised)
    for match in replace_list:
        cat_xml = \
            cat_xml[:match['start']] + match['repl'] + cat_xml[match['end']:]
       
    return cat_xml, replace_map


def restore_catalog_public_ids(stream, replace_map):
    """Replace items from replace map in io stream."""
    
    text = stream.getvalue()
    
    # replacement strings are unique, so simple replace method can be used
    for repl, orig in replace_map.iteritems():
        text = text.replace(repl, orig)
    
    return text
    
    
def get_federator_endpoint(fdsn_service='dataselect'):
    """
    Get URL of EIDA federator endpoint depending on requested FDSN service
    (dataselect or station).
    
    """
    
    if not fdsn_service in settings.EIDA_FEDERATOR_SERVICES:
        raise NotImplementedError, "service %s not implemented" % fdsn_service
        
    
    return "%s:%s/fdsnws/%s/1/" % (
        settings.EIDA_FEDERATOR_BASE_URL, settings.EIDA_FEDERATOR_PORT, 
        fdsn_service)


def get_federator_query_endpoint(fdsn_service='dataselect'):
    """
    Get URL of EIDA federator query endpoint depending on requested FDSN 
    service (dataselect or station).
    
    """
    
    endpoint = get_federator_endpoint(fdsn_service)
    return "%s%s" % (endpoint, settings.FDSN_QUERY_METHOD_TOKEN)


def get_event_query_endpoint(event_service):
    """
    Get URL of EIDA federator query endpoint depending on requested FDSN 
    service (dataselect or station).
    
    """
    
    endpoint = get_event_url(event_service)
    return "%s%s" % (endpoint, settings.FDSN_QUERY_METHOD_TOKEN)


def get_routing_url(routing_service):
    """Get routing URL for routing service abbreviation."""
    
    try:
        server = settings.EIDA_NODES[routing_service]['services']['eida']\
            ['routing']['server']
    except KeyError:
        server = settings.EIDA_NODES[settings.DEFAULT_ROUTING_SERVICE]\
            ['services']['eida']['routing']['server']
        
    return "%s%s" % (server, settings.EIDA_ROUTING_PATH)


def get_event_url(event_service):
    """Get event URL for event service abbreviation."""
    
    try:
        server = settings.FDSN_EVENT_SERVICES[event_service]['server']
    except KeyError:
        server = settings.FDSN_EVENT_SERVICES[settings.DEFAULT_EVENT_SERVICE]\
            ['server']
        
    return "%s%s" % (server, settings.FDSN_EVENT_PATH)


def map_service(service):
    """
    Map service parameter of mediator to service path of FDSN/EIDA web service.
    
    """
    
    return parameters.MEDIATOR_SERVICE_PARAMS[service]['map']


def get_temp_filepath():
    """Return path of temporary file."""
    
    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

