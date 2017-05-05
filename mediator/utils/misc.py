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

from intervaltree import Interval, IntervalTree

import obspy
import requests

from mediator import settings
from mediator.server import httperrors, parameters


# IDs from SC3 that do not validate against QuakeML 1.2_
# - arrival publicIDs from ETHZ (replace all publicIDs)
# - filterID
# - pickID (OK from ETHZ but may be invalid elsewhere)
RE_EVENT_XML_PUBLIC_ID = (
    re.compile(r'publicID="(.+?)"'), re.compile(r'publicID=\'(.+?)\''),
    re.compile(r'<filterID>(.+?)<\/filterID>'), 
    re.compile(r'<pickID>(.+?)<\/pickID>'))

PUBLIC_ID_LOCAL_PREFIX = 'smi:local/'


class SNCL(object):
    """
    This class represents a SNCL dict, defined by network, station, location,
    and channel code.
    
    sncl = {
        'network': CH,
        'station': ZUR,
        'location': '',
        'channel': 'HHZ'
    }
    
    """

    def __init__(self, network, station, location, channel):
        self.d = dict(
            network=network, station=station, location=location, 
            channel=channel)
        
    def __str__(self):
        return "%(network)s.%(station)s.%(location)s.%(channel)s" % (self.d)

          
class SNCLE(object):
    """
    This class represents a SNCL plus a tree of epochs (= time intervals).
    Uses IntervalTree, https://github.com/chaimleib/intervaltree
    
    Note: The intervals tree consists of merged intervals.
    
    sncle = {
        'sncl': SNCL, 
        'epochs': IntervalTree(Interval(t1, t2), ...))
    }
    
    """
    
    def __init__(self, sncl, epochs=[]):
        """
        epochs is a list of (t1, t2) tuples, with t1 and t2 of type
        datetime.datetime. It can contain overlaps.
        The intervals are merged in the constructor.
        
        """
        
        self.sncle = {}
        
        self.sncle['sncl'] = sncl
        self.sncle['epochs'] = IntervalTree.from_tuples(epochs)
        
        # empty tree is False
        if self.sncle['epochs']:
            self.sncle['epochs'] = merge_intervals_in_tree(
                self.sncle['epochs'])

    
    def merge(self, epochs):
        """
        Merge an epoch list into an existing SNCL.
        epochs is a list of (t1, t2) tuples.
        
        """
        
        for iv in epochs:
            self.sncle['epochs'].addi(iv[0], iv[1])
        
        if self.sncle['epochs']:
            self.sncle['epochs'] = merge_intervals_in_tree(
                self.sncle['epochs'])


    def __str__(self):
        return "%s: %s" % (str(self.sncle['sncl']), str(self.sncle['epochs']))


class SNCLEpochs(object):
    """
    This class represents a dict of SNCL objects with associated epochs
    (interval tree of start and end times). The intervals in the tree are 
    merged.
    
    sncl = {SNCL: IntervalTree(Interval(t1, t2), ...)), ...}
    
    """
    
    def __init__(self, sncle=[]):
        """
        Init w/ list of sncle
        
        """
        
        self.sncle = {}
        
        for s in sncle:
            self.add(s.sncle)
    
    
    def merge(self, other):
        """Merge other SNCLEpochs to object."""
        
        for k, v in other.sncle.iteritems():
            self.add({'sncl': k, 'epochs': v})


    def add(self, s):
        """Add SNCLE dict to object."""
        
        key = s['sncl']
        if key in self.sncle:
            
            # merge epoch interval trees (union)
            self.sncle[key] |= s['epochs']
        
        else:
            
            # add new SNCL
            self.sncle.update({key: s['epochs']})
            
        if self.sncle[key]:
            self.sncle[key] = merge_intervals_in_tree(self.sncle[key])


    def tofdsnpost(self):
        """
        Write SNCLEpochs to FDSN web service POST lines.
        Date/time info is UTC YYYY-MM-DDThh:mm:ss.s
        (leave out time zone indicator).
        
        """
        
        out_str = ''
        for sncl, ivtree in self.sncle.iteritems():

            (net, sta, loc, cha) = str(sncl).split('.')
            if not loc:
                loc = '--'
                
            for iv in ivtree:
                out_str += "%s %s %s %s %s %s\n" % (
                    net, sta, loc, cha, iv.begin.isoformat(), 
                    iv.end.isoformat())
                
        return out_str
    
    
    @property
    def empty(self):
        if len(self.sncle) == 0:
            return True
        else:
            return False
    
    
    def __str__(self):
        out_str = ''
        for k, v in self.sncle.iteritems():
            out_str += "%s: %s\n" % (str(k), str(v))
        
        return out_str


def in_interval(value, start, end):
    """Check if a value is within an interval (including boundaries)."""
    
    if value >= start and value <= end:
        return True
    else:
        return False


def merge_intervals_in_tree(tree):
    """
    Merge intervals given in a interval tree and return tree
    with merged intervals.
    
    """
    
    merged_intervals = merge_intervals(list(tree))
    return IntervalTree(merged_intervals)
    
 
def merge_intervals(interval_list):
    """Merge intervals given in an unordered list and return merged list."""
    
    # list of intervals, sorted with start time, ascending
    sorted_list = sorted(interval_list)
    merged_list = [sorted_list[0],]

    for iv in sorted_list[1:]:
        
        if iv.begin > merged_list[-1].end:
            merged_list.append(iv)
            
        elif iv.end > merged_list[-1].end:
            
            start = merged_list[-1].begin
            _ = merged_list.pop()
            
            new = Interval(start, iv.end)
            merged_list.append(new)

    return merged_list


def get_sncl_epochs_from_catalog(cat, replace_map, query_par=None, copy=False):
    """
    Get SNCL epochs from an ObsPy catalog. If requested, apply SNCL 
    constraints (in station namespace) to catalog (filter catalog).
    
    When a catalog is filtered, only whole events are removed (all origins are
    kept, even if their associated picks do not match the SNCL constraint).
    
    Station geometry constraints are not supported (requires station
    service call).
    
    replace_map is the mapping of original to sanitized catalog object IDs.
    
    If copy is True, return a copy of the catalog (may be useful if the catalog
    is modified).
    
    Return SNCLs and filtered catalog.
    
    """
    
    if copy is True:
        catalog = copy.deepcopy(cat)
    else:
        catalog = cat
        
    if query_par is not None:
        pre_length, post_length, mode = get_pre_post_length(query_par)
        sncl_constraint = get_sncl_constraint(query_par, service='station')
    else:
        pre_length = \
            parameters.MEDIATOR_GENERAL_PARAMS['pre_event_length']['default']
        post_length = \
            parameters.MEDIATOR_GENERAL_PARAMS['post_event_length']['default']
        mode = 'event'
        sncl_constraint = get_sncl_constraint()
        
    origin_pick_ids = []
    pick_ids = []
    
    event_match_count = [0] * len(catalog.events)
    
    #print "%s events" % len(catalog.events)
    for ev_idx, ev in enumerate(catalog.events):
        
        ori_count = 0
        
        #print "%s origins" % len(ev.origins)
        for ori in ev.origins:
            for arr in ori.arrivals:
                
                # original pick ID for matching
                pick_id = replace_map[arr.pick_id.id]
                
                origin_pick_ids.append(
                    dict(pick_id=pick_id, ori_time=ori.time, 
                        ev_idx=ev_idx))
        
        #print "%s picks" % len(ev.picks)
        
        # (pick, stationmagnitude, amplitude, ...)
        for pick in ev.picks:
            
            # get reference to origin, origin time (through arrival)
            if pick.waveform_id.location_code:
                loc = pick.waveform_id.location_code
            else:
                loc = ''
            
            # original pick publicID for matching
            pick_publicid = replace_map[pick.resource_id.id]
                
            pick_dict = dict(
                id=pick_publicid, net=pick.waveform_id.network_code, 
                sta=pick.waveform_id.station_code, 
                cha=pick.waveform_id.channel_code, loc=loc, time=pick.time)
            
            # check SNCL constraints
            if sncl_constraint.match(pick_dict):
                #print "matched %s and %s" % (pick_dict, sncl_constraint)
                pick_ids.append(pick_dict)
                
    
    # add SNCLE for all picks that are in origins
    sn = []
    for o_pick in origin_pick_ids:
        for pick in pick_ids:
            
            # compare pick IDs
            if o_pick['pick_id'] == pick['id']:
                
                # add to matching pick count for event
                event_match_count[o_pick['ev_idx']] += 1
                #print "add pick to event idx %s, now: %s" % (
                    #o_pick['ev_idx'], event_match_count[o_pick['ev_idx']])
                
                # create SNCLEs w/ standard start/endtime
                # seconds
                if mode == 'pick':
                    starttime = pick['time'] - pre_length
                    endtime = pick['time'] + post_length
                else:
                    starttime = o_pick['ori_time'] - pre_length
                    endtime = o_pick['ori_time'] + post_length
                    
                s = SNCL(pick['net'], pick['sta'], pick['loc'], pick['cha'])
                iv = [(starttime.datetime, endtime.datetime),]
                sncle = SNCLE(s, iv)
                sn.append(sncle)
    
    # remove events that have no origins that match SNCL constraint
    for ev_idx in reversed(xrange(len(catalog.events))):
        if event_match_count[ev_idx] == 0:
            del catalog.events[ev_idx]
    
    return SNCLEpochs(sn), catalog


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


def get_pre_post_length(query_par):
    """Return pre/post event/pick lengths (in seconds)."""
    
    pre_ev_length = query_par.getpar('pre_event_length')
    post_ev_length = query_par.getpar('post_event_length')
    pre_pick_length = query_par.getpar('pre_pick_length')
    post_pick_length = query_par.getpar('post_pick_length')
    
    # pre/post times, check pick (default is event)
    if pre_pick_length is None and post_pick_length is None:
        
        # event
        mode = 'event'
        if pre_ev_length is not None:
            pre_length = pre_ev_length
        else:
            pre_length = parameters.MEDIATOR_GENERAL_PARAMS\
                ['pre_event_length']['default']
            
        if post_ev_length is not None:
            post_length = post_ev_length
        else:
            post_length = parameters.MEDIATOR_GENERAL_PARAMS\
                ['post_event_length']['default']
            
    else:
        # pick
        mode = 'pick'
        if pre_pick_length is not None:
            pre_length = pre_pick_length
        else:
            pre_length = parameters.MEDIATOR_GENERAL_PARAMS['pre_pick_length']\
                ['default']
                
        if post_pick_length is not None:
            post_length = post_pick_length
        else:
            post_length = parameters.MEDIATOR_GENERAL_PARAMS\
                ['post_pick_length']['default']
            
    return pre_length, post_length, mode
                

def get_sncl_constraint(query_par=None, service=''):
    """Return SNCL constraint object."""
    
    # get SNCL params
    if query_par is not None:
        
        if not service:
            service = query_par.getpar('service')
            
        net, sta, loc, cha = parameters.get_sncl_par(
            query_par, service=service)
        
    else:
        net, sta, loc, cha = [''] * 4
    
    sncl_constraint = parameters.SNCLConstraint(net, sta, loc, cha)
    return sncl_constraint


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

