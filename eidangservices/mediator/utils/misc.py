# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import io
import os
import tempfile

from flask import current_app

import requests
import obspy

from mediator import settings
from mediator.server import httperrors, parameters


DATETIME_TIMESTAMP_FORMAT_FOR_FILENAME_DATE = '%Y%m%d'
DATETIME_TIMESTAMP_FORMAT_FOR_FILENAME_SECOND = '%Y%m%d-%H%M%S'
DATETIME_TIMESTAMP_FORMAT_FOR_FILENAME_MICROSECOND = '%Y%m%d-%H%M%S-%f'


def write_response_string_to_file(outfile, data_str):
    """Write response data to file."""
    
    if not data_str:
        return False
    
    else:
        with open(outfile, 'wb') as fh:
            fh.write(data_str)
            
        return True


def query_federator_for_target_service(
    outfile, service, query_par, snclepochs):
    """
    Query federator service for target service and write response to
    outfile.
    
    """
    
    print "final POST to target service"
    # get endpoint and assemble POST data for federator service
    federator_url, postdata = get_federator_endpoint_and_postdata(
        service, query_par, snclepochs)
    
    with open(outfile, 'wb') as fh:
        response = requests.post(federator_url, data=postdata, stream=True)

        if not response.ok:
            error_msg = "federator POST failed with code %s" % (
                response.status_code)
            raise RuntimeError, error_msg

        for block in response.iter_content(1024):
            fh.write(block)
            
    return True


def get_federator_response_for_post_service(
    service, query_par, snclepochs, addpar={}):
    """
    Query federator service for target service and return response.
    Disallow waveform service.
    
    """
    
    if service == 'waveform':
        error_msg = "federator response is not allowed for waveform service"
        raise NotImplementedError, error_msg
    
    # get endpoint and assemble POST data for federator service
    federator_url, postdata = get_federator_endpoint_and_postdata(
        service, query_par, snclepochs, addpar)

    response = requests.post(federator_url, data=postdata, stream=True)

    if not response.ok:
        error_msg = "federator POST failed with code %s" % (
            response.status_code)
        raise RuntimeError, error_msg
    
    else:
        return response.text


def get_federator_endpoint_and_postdata(
    service, query_par, snclepochs, addpar={}):
    """Get service endpoint and POST payload for federator query."""

    federator_url = get_federator_query_endpoint(map_service(service))
    postdata = get_post_payload(query_par, snclepochs, addpar, service)
    
    print "Federator URL for POST and postdata: %s\n%s" % (
        federator_url, postdata)
    
    return federator_url, postdata
    

def get_inventory_from_federated_station_service(
    query_par, snclepochs, addpar):
    """Return ObsPy inventory from station federator service."""
    
    staxml = get_federator_response_for_post_service(
        'station', query_par, snclepochs, addpar)
    
    # ObsPy inventory from station xml
    inv = obspy.read_inventory(io.StringIO(staxml), format="STATIONXML")
    
    return inv


def get_network_station_code_pairs(inventory):
    """
    Return a list of (network.code, station.code) pairs from an ObsPy 
    inventory.
    
    """ 
    
    net_sta_pairs = []
    
    for net in inventory:
        for sta in net:
            net_sta_pairs.append((net.code, sta.code))
            
    return net_sta_pairs

  
def get_post_payload(query_par, snclepochs, addpar={}, service=''):
    """Assemble and return POST payload for a service query."""
    
    postdata = parameters.get_non_sncl_postlines(query_par, addpar, service)
    postdata += snclepochs.tofdsnpost()
    
    if not postdata:
        # TODO(fab): do not raise from here
        raise httperrors.NoDataError()
    
    return postdata

    
def get_federator_endpoint(fdsn_service='dataselect'):
    """
    Get URL of EIDA federator endpoint depending on requested FDSN service
    (dataselect or station).
    
    """
    
    # service: station or dataselect
    if not fdsn_service in settings.EIDA_FEDERATOR_SERVICES:
        raise NotImplementedError, "service %s not implemented" % fdsn_service
    
    if current_app.config['FEDERATOR']:
        if current_app.config['FEDERATOR'].startswith('http://'):
            federator_server = current_app.config['FEDERATOR']
        else:
            federator_server = "http://{}".format(
                current_app.config['FEDERATOR'])
    else:
        federator_server = "{}:{}".format(
            settings.EIDA_FEDERATOR_BASE_URL, settings.EIDA_FEDERATOR_PORT)
        
    return "{}/fdsnws/{}/1/".format(federator_server, fdsn_service)


def get_federator_query_endpoint(fdsn_service='dataselect'):
    """
    Get URL of EIDA federator query endpoint depending on requested FDSN 
    service (dataselect or station).
    
    """
    
    endpoint = get_federator_endpoint(fdsn_service)
    return "%s%s" % (endpoint, settings.FDSN_QUERY_METHOD_TOKEN)


def get_event_service_endpoints(query_par, default=True):
    """
    Get URLs for event service endopints given as comma-separated lists of
    acronyms.
    
    """
    
    service_acronyms = [x.strip() for x in query_par.getpar(
        'eventservice').split(parameters.PARAMETER_LIST_SEPARATOR)]
    
    url_list = []
    for acr in service_acronyms:
        
        url = get_event_query_endpoint(acr, default=default)
        
        if url is not None:
            url_list.append(url)
      
    return url_list


def get_event_query_endpoint(event_service, default=True):
    """
    Get URL of EIDA federator query endpoint depending on requested FDSN 
    service (dataselect or station).
    
    """
    
    url = None
    
    endpoint = get_event_url(event_service, default=default)
    
    if endpoint is not None:
        url = "%s%s" % (endpoint, settings.FDSN_QUERY_METHOD_TOKEN)
    
    return url


def get_routing_url(routing_service):
    """Get routing URL for routing service abbreviation."""
    
    try:
        server = settings.EIDA_NODES[routing_service]['services']['eida']\
            ['routing']['server']
    except KeyError:
        server = settings.EIDA_NODES[settings.DEFAULT_ROUTING_SERVICE]\
            ['services']['eida']['routing']['server']
        
    return "%s%s" % (server, settings.EIDA_ROUTING_PATH)


def get_event_url(event_service, default=True):
    """Get event URL for event service abbreviation."""
    
    url = None
    
    try:
        server = settings.FDSN_EVENT_SERVICES[event_service]['server']
    except KeyError:
        if default:
            server = settings.FDSN_EVENT_SERVICES\
                [settings.DEFAULT_EVENT_SERVICE]['server']
        else:
            server = None
        
    if server is not None:
        url = "%s%s" % (server, settings.FDSN_EVENT_PATH)
        
    return url
    

def map_service(service):
    """
    Map service parameter of mediator to service path of FDSN/EIDA web service.
    
    """
    
    return parameters.MEDIATOR_SERVICE_PARAMS[service]['map']


def get_temp_filepath():
    """Return path of temporary file."""
    
    return os.path.join(
        tempfile.gettempdir(), next(tempfile._get_candidate_names()))

