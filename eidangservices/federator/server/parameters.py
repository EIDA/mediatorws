# -*- coding: utf-8 -*-
"""
Federator query parameter definitions.

This file is part of the EIDA mediator/federator webservices.

"""

import re

GENERAL_PARAMS = {
    'starttime': {
        'aliases': ('starttime', 'start'),
        'type': str},
    'endtime': {
        'aliases': ('endtime', 'end'),
        'type': str},
    'network': {
        'aliases': ('network', 'net'),
        'type': str},
    'station': {
        'aliases': ('station', 'sta'),
        'type': str},
    'location': {
        'aliases': ('location', 'loc'),
        'type': str},
    'channel': {
        'aliases': ('channel', 'cha'),
        'type': str},
    'format': {
        'aliases': ('format',),
        'type': str},
    'nodata': {
        'aliases': ('nodata',),
        'type': int}
}


DATASELECT_PARAMS = {
    'quality': {
        'aliases': ('quality',),
        'type': str},
    'minimumlength': {
        'aliases': ('minimumlength',),
        'type': float},
    'longestonly': {
        'aliases': ('longestonly',),
        'type': bool},
}


STATION_PARAMS = {
    'minlatitude': {
        'aliases': ('minlatitude', 'minlat'),
        'type': float},
    'maxlatitude': {
        'aliases': ('maxlatitude', 'maxlat'),
        'type': float},
    'minlongitude': {
        'aliases': ('minlongitude', 'minlon'),
        'type': float},
    'maxlongitude': {
        'aliases': ('maxlongitude', 'maxlon'),
        'type': float},
    'latitude': {
        'aliases': ('latitude', 'lat'),
        'type': float},
    'longitude': {
        'aliases': ('longitude', 'lon'),
        'type': float},
    'minradius': {
        'aliases': ('minradius',),
        'type': float},
    'maxradius': {
        'aliases': ('maxradius',),
        'type': float},
    'level': {
        'aliases': ('level',),
        'type': str},
    'includerestricted': {
        'aliases': ('includerestricted',),
        'type': bool},
    'includeavailability': {
        'aliases': ('includeavailability',),
        'type': bool},
    'updatedafter': {
        'aliases': ('updatedafter',),
        'type': str},
    'matchtimeseries': {
        'aliases': ('matchtimeseries',),
        'type': bool},
}

ALL_QUERY_PARAMS = (GENERAL_PARAMS, DATASELECT_PARAMS, STATION_PARAMS)

TIMESTAMP_PARAMS = ('starttime', 'start', 'endtime', 'end')
RE_TIMESTAMP_WITHOUT_TIME = re.compile(r'^\d{4}-\d{2}-\d{2}$')

def parameter_description(query_param):
    """Check if a given query parameter has a definition and return it. If not 
    found, return None."""
    
    for group_idx, parameter_group in enumerate(ALL_QUERY_PARAMS):
        for k, v in parameter_group.iteritems():
            
            # check aliases definition for parameter name
            if query_param in v['aliases']:
                return (group_idx, k)
    
    return (None, None)
  
  
def fix_param_value(param, value):
    """Check format of parameter values and fix, if necessary."""
    
    # add zero time part to date-only timestamp (required for routing service)
    if param.lower() in TIMESTAMP_PARAMS and is_timestamp_without_time(value):
        value += "T00:00:00"
        
    return value


def is_timestamp_without_time(value):
    """Return True if value is of YYYY-MM-DD format."""
    
    return bool(RE_TIMESTAMP_WITHOUT_TIME.search(value))
