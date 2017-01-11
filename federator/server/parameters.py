# -*- coding: utf-8 -*-
"""
Federator query parameter definitions.

This file is part of the EIDA mediator/federator webservices.

"""


GENERAL_PARAMS = {
    'starttime': {
        'aliases': ('starttime', 'start'),
        'type': str,
        'fdsn_fetch_par': '-s'},
    'endtime': {
        'aliases': ('endtime', 'end'),
        'type': str,
        'fdsn_fetch_par': '-e'},
    'network': {
        'aliases': ('network', 'net'),
        'type': str,
        'fdsn_fetch_par': '-N'},
    'station': {
        'aliases': ('station', 'sta'),
        'type': str,
        'fdsn_fetch_par': '-S'},
    'location': {
        'aliases': ('location', 'loc'),
        'type': str,
        'fdsn_fetch_par': '-L'},
    'channel': {
        'aliases': ('channel', 'cha'),
        'type': str,
        'fdsn_fetch_par': '-C'},
    'format': {
        'aliases': ('format',),
        'type': str,
        'fdsn_fetch_par': ''},
    'nodata': {
        'aliases': ('nodata',),
        'type': int,
        'fdsn_fetch_par': ''}
}


DATASELECT_PARAMS = {
    'quality': {
        'aliases': ('quality',),
        'type': str,
        'fdsn_fetch_par': ''},
    'minimumlength': {
        'aliases': ('minimumlength',),
        'type': float,
        'fdsn_fetch_par': ''},
    'longestonly': {
        'aliases': ('longestonly',),
        'type': bool,
        'fdsn_fetch_par': ''}
}


STATION_PARAMS = {
    'minlatitude': {
        'aliases': ('minlatitude', 'minlat'),
        'type': float,
        'fdsn_fetch_par': ''},
    'maxlatitude': {
        'aliases': ('maxlatitude', 'maxlat'),
        'type': float,
        'fdsn_fetch_par': ''},
    'minlongitude': {
        'aliases': ('minlongitude', 'minlon'),
        'type': float,
        'fdsn_fetch_par': ''},
    'maxlongitude': {
        'aliases': ('maxlongitude', 'maxlon'),
        'type': float,
        'fdsn_fetch_par': ''},
    'latitude': {
        'aliases': ('latitude', 'lat'),
        'type': float,
        'fdsn_fetch_par': ''},
    'longitude': {
        'aliases': ('longitude', 'lon'),
        'type': float,
        'fdsn_fetch_par': ''},
    'minradius': {
        'aliases': ('minradius',),
        'type': float,
        'fdsn_fetch_par': ''},
    'maxradius': {
        'aliases': ('maxradius',),
        'type': float,
        'fdsn_fetch_par': ''},
    'level': {
        'aliases': ('level',),
        'type': str,
        'fdsn_fetch_par': ''},
    'includerestricted': {
        'aliases': ('includerestricted',),
        'type': bool,
        'fdsn_fetch_par': ''},
    'includeavailability': {
        'aliases': ('includeavailability',),
        'type': bool,
        'fdsn_fetch_par': ''},
    'updatedafter': {
        'aliases': ('updatedafter',),
        'type': str,
        'fdsn_fetch_par': ''},
    'matchtimeseries': {
        'aliases': ('matchtimeseries',),
        'type': bool,
        'fdsn_fetch_par': ''}
}


ALL_QUERY_PARAMS = (GENERAL_PARAMS, DATASELECT_PARAMS, STATION_PARAMS)


def parameter_description(query_param):
    """Check if a given query parameter has a definition and return it. If not 
    found, return None."""
    
    for group_idx, parameter_group in enumerate(ALL_QUERY_PARAMS):
        for k, v in parameter_group.iteritems():
            
            # check aliases definition for parameter name
            if query_param in v['aliases']:
                return (group_idx, k)
    
    return (None, None)
