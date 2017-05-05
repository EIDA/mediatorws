# -*- coding: utf-8 -*-
"""
Federator query parameter definitions.

This file is part of the EIDA mediator/federator webservices.

"""

import re

from obspy import UTCDateTime

PARAMETER_PREFIX_SEPARATOR = '.'

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

TIMESTAMP_PARAMS = ('starttime', 'start', 'endtime', 'end')
RE_TIMESTAMP_WITHOUT_TIME = re.compile(r'^\d{4}-\d{2}-\d{2}$')


MEDIATOR_GENERAL_PARAMS = {
    'service': {
        'aliases': ('service',),
        'type': str,
        'values': (
            'submit', 'station', 'waveform', 'routing', 'wfcatalog', 'event'),
        'default': 'waveform',
        'mandatory': True},
    'eventservice': {
        'aliases': ('eventservice',),
        'type': str,
        'default': 'usgs'},
    'event_sncl_filter': {
        'aliases': ('event_sncl_filter',),
        'type': str,
        'values': ('all', 'any'),
        'default': 'all'},
    'pre_event_length': {
        'aliases': ('pre_event_length',),
        'type': float,
        'default': 120},
    'post_event_length': {
        'aliases': ('post_event_length',),
        'type': float,
        'default': 1200},
    'pre_pick_length': {
        'aliases': ('pre_pick_length',),
        'type': float,
        'default': 120},
    'post_pick_length': {
        'aliases': ('post_pick_length',),
        'type': float,
        'default': 1200}
}


MEDIATOR_EVENT_PARAMS = {
    'e.starttime': {
        'aliases': ('e.starttime', 'e.start'),
        'type': str,
        'nonsnclepoch': True},
    'e.endtime': {
        'aliases': ('e.endtime', 'e.end'),
        'type': str,
        'nonsnclepoch': True},
    'e.minlatitude': {
        'aliases': ('e.minlatitude', 'e.minlat'),
        'type': float,
        'nonsnclepoch': True},
    'e.maxlatitude': {
        'aliases': ('e.maxlatitude', 'e.maxlat'),
        'type': float,
        'nonsnclepoch': True},
    'e.minlongitude': {
        'aliases': ('e.minlongitude', 'e.minlon'),
        'type': float,
        'nonsnclepoch': True},
    'e.maxlongitude': {
        'aliases': ('e.maxlongitude', 'e.maxlon'),
        'type': float,
        'nonsnclepoch': True},
    'e.latitude': {
        'aliases': ('e.latitude', 'e.lat'),
        'type': float,
        'nonsnclepoch': True},
    'e.longitude': {
        'aliases': ('e.longitude', 'e.lon'),
        'type': float,
        'nonsnclepoch': True},
    'e.minradius': {
        'aliases': ('e.minradius',),
        'type': float,
        'nonsnclepoch': True},
    'e.maxradius': {
        'aliases': ('e.maxradius',),
        'type': float,
        'nonsnclepoch': True},
    'e.mindepth': {
        'aliases': ('e.mindepth',),
        'type': float,
        'nonsnclepoch': True},
    'e.maxdepth': {
        'aliases': ('e.maxdepth',),
        'type': float,
        'nonsnclepoch': True},
    'e.minmagnitude': {
        'aliases': ('e.minmagnitude', 'e.minmag'),
        'type': float,
        'nonsnclepoch': True},
    'e.maxmagnitude': {
        'aliases': ('e.maxmagnitude', 'e.maxmag'),
        'type': float,
        'nonsnclepoch': True},
    'e.includeallorigins': {
        'aliases': ('e.includeallorigins',),
        'type': bool,
        'default': False,
        'nonsnclepoch': True},
    'e.includeallmagnitudes': {
        'aliases': ('e.includeallmagnitudes',),
        'type': bool,
        'default': False,
        'nonsnclepoch': True},
    'e.includearrivals': {
        'aliases': ('e.includearrivals',),
        'type': bool,
        'default': False,
        'nonsnclepoch': True},
    'e.format': {
        'aliases': ('e.format',),
        'type': str,
        'default': 'xml',
        'nonsnclepoch': True},
    'e.nodata': {
        'aliases': ('e.nodata',),
        'type': int,
        'default': 204,
        'nonsnclepoch': True}
}
  

MEDIATOR_STATION_PARAMS = {
    's.starttime': {
        'aliases': ('s.starttime', 's.start'),
        'type': str},
    's.endtime': {
        'aliases': ('s.endtime', 's.end'),
        'type': str},
    's.network': {
        'aliases': ('s.network', 's.net'),
        'type': str},
    's.station': {
        'aliases': ('s.station', 's.sta'),
        'type': str},
    's.location': {
        'aliases': ('s.location', 's.loc'),
        'type': str},
    's.channel': {
        'aliases': ('s.channel', 's.cha'),
        'type': str},
    's.minlatitude': {
        'aliases': ('s.minlatitude', 's.minlat'),
        'type': float,
        'nonsnclepoch': True},
    's.maxlatitude': {
        'aliases': ('s.maxlatitude', 's.maxlat'),
        'type': float,
        'nonsnclepoch': True},
    's.minlongitude': {
        'aliases': ('s.minlongitude', 's.minlon'),
        'type': float,
        'nonsnclepoch': True},
    's.maxlongitude': {
        'aliases': ('s.maxlongitude', 's.maxlon'),
        'type': float,
        'nonsnclepoch': True},
    's.latitude': {
        'aliases': ('s.latitude', 's.lat'),
        'type': float,
        'nonsnclepoch': True},
    's.longitude': {
        'aliases': ('s.longitude', 's.lon'),
        'type': float,
        'nonsnclepoch': True},
    's.minradius': {
        'aliases': ('s.minradius',),
        'type': float,
        'nonsnclepoch': True},
    's.maxradius': {
        'aliases': ('s.maxradius',),
        'type': float,
        'nonsnclepoch': True},
    's.level': {
        'aliases': ('s.level',),
        'type': str,
        'nonsnclepoch': True},
    's.includerestricted': {
        'aliases': ('s.includerestricted',),
        'type': bool,
        'default': True,
        'nonsnclepoch': True},
    's.includeavailability': {
        'aliases': ('s.includeavailability',),
        'type': bool,
        'default': False,
        'nonsnclepoch': True},
    's.updatedafter': {
        'aliases': ('s.updatedafter',),
        'type': str,
        'nonsnclepoch': True},
    's.matchtimeseries': {
        'aliases': ('s.matchtimeseries',),
        'type': bool,
        'default': False,
        'nonsnclepoch': True},
    's.format': {
        'aliases': ('s.format',),
        'type': str,
        'default': 'xml',
        'nonsnclepoch': True},
    's.nodata': {
        'aliases': ('s.nodata',),
        'type': int,
        'default': 204,
        'nonsnclepoch': True}
}

MEDIATOR_DATASELECT_PARAMS = {
    'w.starttime': {
        'aliases': ('w.starttime', 'w.start'),
        'type': str},
    'w.endtime': {
        'aliases': ('w.endtime', 'w.end'),
        'type': str},
    'w.network': {
        'aliases': ('w.network', 'w.net'),
        'type': str},
    'w.station': {
        'aliases': ('w.station', 'w.sta'),
        'type': str},
    'w.location': {
        'aliases': ('w.location', 'w.loc'),
        'type': str},
    'w.channel': {
        'aliases': ('w.channel', 'w.cha'),
        'type': str},
    'w.quality': {
        'aliases': ('w.quality',),
        'type': str,
        'default': 'B',
        'nonsnclepoch': True},
    'w.minimumlength': {
        'aliases': ('w.minimumlength',),
        'type': float,
        'default': 0.0,
        'nonsnclepoch': True},
    'w.longestonly': {
        'aliases': ('w.longestonly',),
        'type': bool,
        'default': False,
        'nonsnclepoch': True},
    'w.format': {
        'aliases': ('w.format',),
        'type': str,
        'default': 'miniseed',
        'nonsnclepoch': True},
    'w.nodata': {
        'aliases': ('w.nodata',),
        'type': int,
        'default': 204,
        'nonsnclepoch': True}
}
    
# TODO(fab)
MEDIATOR_WFCATALOG_PARAMS = {}
    
ALL_MEDIATOR_QUERY_PARAMS = (
    MEDIATOR_GENERAL_PARAMS, MEDIATOR_EVENT_PARAMS, MEDIATOR_STATION_PARAMS,
    MEDIATOR_DATASELECT_PARAMS)


MEDIATOR_SERVICES = ('event', 'station', 'waveform', 'wfcatalog')

# mediator service parameters that need a mapping to other names for 
# FDSN/EIDA services

MEDIATOR_SERVICE_PARAMS = {
    'event': {
        'map': 'event',
        'prefix': 'e',
        'parameters': MEDIATOR_EVENT_PARAMS},
    
    'station': {
        'map': 'station',
        'prefix': 's',
        'parameters': MEDIATOR_STATION_PARAMS},
    
    'waveform': {
        'map': 'dataselect',
        'prefix': 'w',
        'parameters': MEDIATOR_DATASELECT_PARAMS},
    
    'wfcatalog': {
        'map': 'wfcatalog',
        'prefix': 'q',
        'parameters': MEDIATOR_WFCATALOG_PARAMS}
}



class MediatorServiceMap(object):
    """
    Structure that indicates which of the services (FDSNWS/EIDAWS) are 
    involved.
    
    """
    
    map = dict(event=False, station=False, waveform=False, wfcatalog=False)
    params = dict(
        event=dict(), station=dict(), waveform=dict(), wfcatalog=dict())
    ws_params = dict(
        event=dict(), station=dict(), waveform=dict(), wfcatalog=dict())
    
    def __init__(self, map=None):
        if map is not None:
            for k, v in map.iteritems():
                if v:
                    self.enable(k)
                    
    
    def is_enabled(self, service):
        return self.map.get(service, None)
    
    
    def enable(self, service):
        if service in self.map:
            self.map[service] = True 
    
    
    def disable(self, service):
        if service in self.map:
            self.map[service] = False
            
            
    def addpar(self, service, k, v):
        if service in self.params and v is not None:
            self.params[service][k] = v
            self.ws_params[service][strip_param_prefix(k, service)] = v
            self.enable(service)
            
            
    def set_services(self, params):
        for k, v in params.iteritems():
            if v is not None:
                for service in MEDIATOR_SERVICE_PARAMS:
                    if k in MEDIATOR_SERVICE_PARAMS[service]['parameters']:
                        self.addpar(service, k, v)
    
    @property
    def event_params(self):
        return (self.params['event'], self.ws_params['event'])
    
    @property
    def station_params(self):
        return (self.params['station'], self.ws_params['station'])
    
    @property
    def waveform_params(self):
        return (self.params['waveform'], self.ws_params['waveform'])
    
    @property
    def wfcatalog_params(self):
        return (self.params['wfcatalog'], self.ws_params['wfcatalog'])


class SNCLConstraint(object):
    """
    Structure for SNCL constraints given by query parameters.
    
    """
    
    def __init__(self, net='', sta='', loc='', cha=''):
        self.net = net
        self.sta = sta
        self.loc = loc
        self.cha = cha
        
    
    def match(self, pick_dict):
        """
        Check if SNCL constraints match. Very simple. No wildcards. No lists.
        
        """
        
        # don't compare unset parametes (they are None)
        if self.net is not None and self.net != pick_dict['net']:
            return False
        
        if self.sta is not None and self.sta != pick_dict['sta']:
            return False
        
        if self.cha is not None and self.cha != pick_dict['cha']:
            return False
        
        check_loc = pick_dict['loc']
        
        if check_loc == '--':
            check_loc = ''
            
        if self.loc is not None and self.loc != check_loc:
            return False
        
        return True
    
    
    def __str__(self):
        out_str = "net=%s sta=%s loc=%s cha=%s" % (
            self.net, self.sta, self.loc, self.cha)
        
        return out_str
    

def get_start_end_time_par(query_par, service='', todatetime=False):
    """Get start/end times from query parameters, depending on service."""
    
    starttime = None
    endtime = None
    
    if not service:
        service = query_par.getpar('service')
    
    if service == 'station':
        starttime = query_par.getpar('s.starttime')
        endtime = query_par.getpar('s.endtime')
    
    
    elif service == 'waveform':
        starttime = query_par.getpar('w.starttime')
        endtime = query_par.getpar('w.endtime')
    
    
    elif service == 'wfcatalog':
        starttime = query_par.getpar('q.starttime')
        endtime = query_par.getpar('q.endtime')
        
    elif service == 'event':
        starttime = query_par.getpar('e.starttime')
        endtime = query_par.getpar('e.endtime')
        
    if starttime is not None and todatetime:
        starttime = UTCDateTime(starttime).datetime
        
    if endtime is not None and todatetime:
        endtime = UTCDateTime(endtime).datetime

    return starttime, endtime
    

def get_sncl_par(query_par, service='', wildcards=False):
    """Get SNCL parameters from query parameters, depending on service."""
    
    net = None
    sta = None
    loc = None
    cha = None
    
    if not service:
        service = query_par.getpar('service')
    
    if service == 'station':
        net = query_par.getpar('s.network')
        sta = query_par.getpar('s.station')
        loc = query_par.getpar('s.location')
        cha = query_par.getpar('s.channel')
    
    elif service == 'waveform':
        net = query_par.getpar('w.network')
        sta = query_par.getpar('w.station')
        loc = query_par.getpar('w.location')
        cha = query_par.getpar('w.channel')
    
    
    elif service == 'wfcatalog':
        net = query_par.getpar('q.network')
        sta = query_par.getpar('q.station')
        loc = query_par.getpar('q.location')
        cha = query_par.getpar('q.channel')
        
    elif service == 'event':
        
        # use SNCL params of station for event
        net = query_par.getpar('s.network')
        sta = query_par.getpar('s.station')
        loc = query_par.getpar('s.location')
        cha = query_par.getpar('s.channel')

    if wildcards:
        if net is None:
            net = '*'
        if sta is None:
            sta = '*'
        if loc is None:
            loc = '*'
        if cha is None:
            cha = '*'
            
    return net, sta, loc, cha


def get_non_sncl_postlines(query_par):
    """Get parameter=value lines for federator POST query."""
    
    out_lines = ''
    
    service = query_par.getpar('service')
    
    for group_idx, parameter_group in enumerate(ALL_MEDIATOR_QUERY_PARAMS):
        for k, v in parameter_group.iteritems():
            
            par_value = query_par.getpar(k)
            if par_value is not None and 'nonsnclepoch' in v and \
                v['nonsnclepoch']:
                
                fdsn_par = strip_param_prefix(k, service)
                out_lines += "%s=%s\n" % (fdsn_par, par_value) 
  
    return out_lines

    
def parameter_description(query_param):
    """
    Check if a given query parameter from current request has a proper 
    definition. If true, return parameter name and section index of occurrence.
    If not found, return (None, None).
    
    """
    
    for group_idx, parameter_group in enumerate(ALL_MEDIATOR_QUERY_PARAMS):
        for k, v in parameter_group.iteritems():
            
            # check aliases definition for parameter name
            if query_param in v['aliases']:
                return (group_idx, k)
    
    return (None, None)


def get_parameter_description(group_idx, param_key):
    """Return parameter description with type, aliases, default value."""
    return ALL_MEDIATOR_QUERY_PARAMS[group_idx][param_key]

  
def fix_param_value(param, value):
    """Check format of parameter values and fix, if necessary."""
    
    # add zero time part to date-only timestamp (required for routing service)
    if param.lower() in TIMESTAMP_PARAMS and is_timestamp_without_time(value):
        value += "T00:00:00"
        
    return value


def is_timestamp_without_time(value):
    """Return True if value is of YYYY-MM-DD format."""
    
    return bool(RE_TIMESTAMP_WITHOUT_TIME.search(value))


def strip_param_prefix(param, service=''):
    """Strip service prefix from parameter name."""
    
    if not service:
        return param
    
    prefix = MEDIATOR_SERVICE_PARAMS[service]['prefix']
    full_prefix = "%s%s" % (prefix, PARAMETER_PREFIX_SEPARATOR)
    
    if param.startswith(full_prefix):
        param = param[len(full_prefix):]
    
    return param
    
    
