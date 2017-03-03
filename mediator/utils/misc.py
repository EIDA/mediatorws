# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import copy
import os

import flask
from flask import make_response
from flask_restful import Resource

from intervaltree import Interval, IntervalTree

import obspy
import requests

from mediator import settings                                


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
        if key in self.sncle.keys():
            
            # merge epoch interval trees (union)
            self.sncle[key] |= s['epochs']
        
        else:
            
            # add new SNCL
            self.sncle.update({key: s['epochs']})
            
        if self.sncle[key]:
            self.sncle[key] = merge_intervals_in_tree(self.sncle[key])


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


def process_dq(args):
    """Process direct query."""
    
    # event service: GET only
    # SC3 implementation: no catalogs parameter, contributors parameter are
    #  mapped to agencyIDs, they must be defined in
    #  @DATADIR@/share/fdsn/contributors.xml
    #  eventid (optional) is implemented, is a publicID
    
    # event query
    payload = {
        'start': '2009-01-01', 'end': '2010-01-01', 'minlat': '46', 
        'maxlat': '49', 'minlon': '8', 'maxlon':'11', 'minmag': '3.5', 
        'format': 'xml', 'includearrivals': 'true', 'formatted': 'true'}
    
    event_query_url = 'http://arclink.ethz.ch/fdsnws/event/1/query'
    
    # consume event service
    r = requests.get(event_query_url, params=payload)
    
    # print r.text
    
    cat = obspy.read_events(str(r.text))

    # browse through all waveform stream IDs in catalog
    snclepochs = get_sncl_epochs_from_catalog(cat)

    
    # TODO: check for wild cards in SNCLs
    # based on that list: consume dataselect/station
    
    return str(snclepochs)


def get_sncl_epochs_from_catalog(catalog):
    """Get SNCL epochs from an ObsPy catalog."""
    
    origin_pick_ids = []
    pick_ids = []
    
    #print "%s events" % len(catalog.events)
    
    for ev in catalog.events:
        
        #print "%s origins" % len(ev.origins)
        
        for ori in ev.origins:
            
            ori_time = ori.time
            
            for arr in ori.arrivals:
                origin_pick_ids.append((arr.pick_id, ori.time))
        
        #print "%s picks" % len(ev.picks)
        
        # (pick, stationmagnitude, amplitude, ...)
        for pick in ev.picks:
            
            # get reference to origin, origin time (through arrival)
            if pick.waveform_id.location_code:
                loc = pick.waveform_id.location_code
            else:
                loc = ''
            
            #  pick.time not needed
            pick_tuple = (pick.resource_id.id, pick.waveform_id.network_code, 
                pick.waveform_id.station_code, pick.waveform_id.channel_code, 
                loc)
            
            pick_ids.append(pick_tuple)
    
    # add SNCLE for all picks that are in origins
    sn = []
    for o_pick in origin_pick_ids:
        for pick in pick_ids:
            
            if o_pick[0] == pick[0]:
                
                # create SNCLEs w/ standard start/endtime
                # seconds
                starttime = o_pick[1] - 60 * 10
                endtime = o_pick[1] + 60 * 20
                
                s = SNCL(pick[1], pick[2], pick[4], pick[3])
                iv = [(starttime.datetime, endtime.datetime),]
                sncle = SNCLE(s, iv)
                sn.append(sncle)
                
    return SNCLEpochs(sn)
    
    