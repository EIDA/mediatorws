# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import copy
import datetime
import fnmatch
import os
import re
import tempfile
import uuid

import flask
from flask import make_response
from flask_restful import Resource

from intervaltree import Interval, IntervalTree

import obspy
import requests

from mediator import settings
from mediator.server import httperrors, parameters
from mediator.utils import misc


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


def get_sncl_epochs(query_par, service, cat=None, replace_map=None):
    """
    Get SNCL epochs.
    
    For target service 'event':
        from catalog, with possible additional temporal and SNCL
        constraints.
        
    For other target service;
        from temporal and SNCL constraints.
    
    """
    
    time_interval = None
    sncl_params = None
    
    # TODO(fab): 
    # time constraint: either per pick, or fixed (relative to origin time, or
    # explicit interval)
    # ?? sncl constraint: either from event, or explicit (station query)
    
    
    if service == 'event':

        # apply E SNCL constraint (others do not make sense):    
        #  snclepochs: remove SNCLEs 
        #  catalog: remove whole events
        snclepochs, cat = get_sncl_epochs_from_catalog(
            cat, replace_map, query_par)

    else:
        
        # target service is not event: 
        # evaluate sncl and time constraints of
        # station, waveform, and quality namespaces
        time_interval = query_par.get_time_interval(service, todatetime=True)
        sncl_params = query_par.get_sncl_params(service)
        
        if cat is not None:
        
            # target service is not event, but catalog is used for 
            # SNCL selection
            snclepochs, cat = get_sncl_epochs_from_catalog(
                cat, replace_map, query_par, time_interval, sncl_params)
    
        else:
        
            # get sncl epochs w/o catalog
            # epoch time intervals must be finite, set to default limits
            start_time_fix, end_time_fix = \
                parameters.set_limit_on_undefined_time_interval(
                    time_interval['start'], time_interval['end'])
            
            # get SNCL constraints w/o catalog
            net, sta, loc, cha = get_sncl_par(
                query_par, service, wildcards=True)
            
            # TODO(fab): check SNCL epochs
            iv = [(start_time_fix, end_time_fix),]
            sn = get_sncl_epoch_list(net, sta, loc, cha, iv)
            snclepochs = SNCLEpochs(sn)
    
    return snclepochs, cat


def get_sncl_epochs_from_catalog(cat, replace_map, query_par=None, 
    time_interval=None, copy=False):
    """
    Get SNCL epochs from an ObsPy catalog. If requested, apply SNCL 
    constraints (in event namespace) to catalog (filter catalog).
    
    When a catalog is filtered, only whole events are removed (all origins are
    kept, even if their associated picks do not match the SNCL constraint).
    
    Station geometry and channel constraints are not supported 
    (requires station service call).
    
    replace_map is the mapping of original to sanitized catalog object IDs.
    
    time_interval is a pair of datetime objects (starttime, endtime). If this 
    is not None, it is used for all SNCL epochs. Still one of the componnets
    can be None. In this case, use the default pre/post-length relative to
    the origin time.
    
    If copy is True, return a copy of the catalog (may be useful if the catalog
    is modified).
    
    Return SNCLs and filtered catalog.
    
    """
    
    if copy is True:
        catalog = copy.deepcopy(cat)
    else:
        catalog = cat
    
    if query_par is not None:
        match_all = parameters.get_event_sncl_filter(query_par)[1]
        sncl_constraint = get_sncl_constraint(
            query_par, service='event', match_all=match_all)
        
        pre_length, post_length, mode = parameters.get_pre_post_length(
            query_par)  
    
    else:
        mode = 'event'
        match_all = False
        sncl_constraint = get_sncl_constraint(match_all=match_all)
        
        pre_length = \
            parameters.MEDIATOR_GENERAL_PARAMS['pre_event_length']['default']
        post_length = \
            parameters.MEDIATOR_GENERAL_PARAMS['post_event_length']['default']
       
        
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
            
            #print "check picks: %s" % str(pick_dict)
            
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
                
                # if request contains starttime, endtime: use fixed time
                # interval for all SNCLs
                # otherwise use pre/post length relative to pick or origin time
                if time_interval is not None and not(
                    time_interval['start'] is None or \
                        time_interval['end'] is None) and (
                    time_interval['end'] > time_interval['start']):
                        
                    starttime = time_interval['start']
                    endtime = time_interval['end']
                
                elif time_interval is None and mode == 'pick':
                    starttime = pick['time'].datetime - datetime.timedelta(
                        seconds=pre_length)
                    endtime = pick['time'].datetime + datetime.timedelta(
                        seconds=post_length)
                
                else:
                    
                    # init with pre/post length relative to origin time
                    starttime = o_pick['ori_time'].datetime - \
                        datetime.timedelta(seconds=pre_length)
                    endtime = o_pick['ori_time'].datetime + datetime.timedelta(
                        seconds=post_length)
                   
                    # if one time interval component is finite and the other is
                    # None, apply it if the resulting time interval is finite
                    if time_interval is not None and \
                        time_interval['start'] is not None and \
                        time_interval['start'] < endtime:
                        
                        starttime = time_interval['start']
                        
                    elif time_interval is not None and \
                        time_interval['end'] is not None and \
                        time_interval['end'] > starttime:
                                
                        endtime = time_interval['end']
                    
                s = SNCL(pick['net'], pick['sta'], pick['loc'], pick['cha'])
                iv = [(starttime, endtime),]
                sncle = SNCLE(s, iv)
                sn.append(sncle)
    
    # remove events that have no origins that match SNCL constraint
    for ev_idx in reversed(xrange(len(catalog.events))):
        if event_match_count[ev_idx] == 0:
            del catalog.events[ev_idx]
    
    return SNCLEpochs(sn), catalog


class SNCLConstraint(object):
    """
    Structure for SNCL constraints given by query parameters.
    
    """
    
    def __init__(self, net=[], sta=[], loc=[], cha=[], match_all=False):
        """
        net, sta, loc, cha are lists.
        
        """
        
        self.net = net
        self.sta = sta
        self.loc = loc
        self.cha = cha
        self.match_all = match_all
        
    
    def match(self, pick_dict):
        """
        Check if SNCL constraints match. Very simple. 
        
        """
        
        #print "matching against: %s" % str(self)
        
        if self.net and (None not in self.net) and not(
            sncl_constraint_matches(
                self.net, pick_dict['net'], self.match_all)):
            
            return False
        
        if self.sta and (None not in self.sta) and not(
            sncl_constraint_matches(
                self.sta, pick_dict['sta'], self.match_all)):
            
            return False
        
        if self.cha and (None not in self.cha) and not(
            sncl_constraint_matches(
                self.cha, pick_dict['cha'], self.match_all)):
            
            return False
        
        check_loc = pick_dict['loc']
        
        if check_loc == '--':
            check_loc = ''
            
        if self.loc and (None not in self.loc) and not(
            sncl_constraint_matches(
                self.loc, check_loc, self.match_all)):
            
            return False
        
        return True
    
    
    def __str__(self):
        out_str = "net=%s sta=%s loc=%s cha=%s" % (
            str(self.net), str(self.sta), str(self.loc), str(self.cha))
        
        return out_str


def get_sncl_par(query_par, service='', wildcards=False):
    """Get SNCL parameters from query parameters, depending on service."""

    if not service:
        service = query_par.getpar('service')
        
    prefix = parameters.MEDIATOR_SERVICE_PARAMS[service]['prefix']
    
    net = listify_sncl_par(query_par.getpar("%s.network" % prefix), wildcards)
    sta = listify_sncl_par(query_par.getpar("%s.station" % prefix), wildcards)
    loc = listify_sncl_par(query_par.getpar("%s.location" % prefix), wildcards)
    cha = listify_sncl_par(query_par.getpar("%s.channel" % prefix), wildcards)
  
    return net, sta, loc, cha


def listify_sncl_par(par, wildcards=False):
    """Turn sncl par string into list."""
    
    if par is None and wildcards:
        par = ['*',]
        
    elif par is None and not wildcards:
        par = [None,]
        
    else:
        par = [x.strip() for x in par.split(
            parameters.PARAMETER_LIST_SEPARATOR)]

    return par


def get_sncl_epoch_list(net, sta, loc, cha, iv):
    """
    net, sta, loc, cha are lists.
    iv is a list of (starttime, endtime) pairs.
    
    NOTE: This function can return SNCL combinations that do no exist.
    Example: two stations, N1.S1 and N2.S2. Query for net=N1,N2 sta=S1,S2
    yields all combinations N1.S1, N1.S2, N2.S1, N2.S2.
    
    """
        
    sncle_list = []
        
    for n in net:
        for s in sta:
            for l in loc:
                for c in cha:
                    for i in iv:
                        
                        # TODO(fab): what about None values?
                        sn = SNCL(n, s, l, c)
                        sncle = SNCLE(sn, i)
                        sncle_list.append(sncle)
    
    return sncle_list


def get_sncl_constraint(query_par=None, service='', match_all=False):
    """Return SNCL constraint object."""
    
    # get SNCL params
    if query_par is not None:
        
        if not service:
            service = query_par.getpar('service')
            
        net, sta, loc, cha = get_sncl_par(query_par, service=service)
        
    else:
        net, sta, loc, cha = [[]] * 4
    
    return SNCLConstraint(net, sta, loc, cha, match_all)


def sncl_constraint_matches(patterns, test, match_all=False):
    """
    Validate test against a list of fnmatch patttern (* and ? wildcards).
    
    match_all=True: return True if all patterns are matched
    match_all=False: return True if one of the patterns is matched
    
    TODO(fab): does match_all=True make sense in any case?
    """

    miss_count = 0
    for pattern in patterns:
        if not fnmatch.fnmatch(test, pattern):
            if match_all:
                return False
            else:
                miss_count += 1
    
    # fail if we have only misses
    if miss_count == len(patterns):
        return False
    else:
        return True
