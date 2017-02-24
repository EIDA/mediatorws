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
        epochs is a list of (t1, t2) tuples. It can contain overlaps.
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
    
    def __init__(self, sncle=None):
        
        self.sncle = {}
        
        if sncle:
            self.sncle = self.add(sncle)
    
    
    def merge(self, other):
        """Merge other SNCLEpochs to object."""
        
        for k, v in other.iteritems():
            self.add({'sncl': k, 'epochs': v})


    def add(self, s):
        """Add SNCLE to object."""
        
        key = s['sncl']
        if key in self.sncle.keys():
            
            # merge epoch interval trees (union)
            self.sncle[key] |= s['epochs']
            if self.sncle['epochs']:
                self.sncle['epochs'] = merge_intervals_in_tree(
                    self.sncle['epochs'])
        
        else:
            
            # add new SNCL
            self.sncle.update({key: s['epochs']})


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
    pass

