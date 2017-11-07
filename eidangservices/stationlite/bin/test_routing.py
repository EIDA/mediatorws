#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Checks output of routing services at EIDA nodes for all test SNCLs of the
nodes. Expected result is that each node is the authoritative source for
its own reference SNCLs, all services provide the correct routes, and that 
there are no ambiguities.

"""

import requests

from eidangservices import settings


TEST_TIME_INTERVALS = {
    'small': {
        'start': '2016-10-01T06:00:00', 'end': '2016-10-01T06:10:00'
        },
    'medium': {
        'start': '2016-10-01T06:00:00', 'end': '2016-10-01T09:00:00'
        },
    'large': {
        'start': '2016-10-01T06:00:00', 'end': '2016-10-01T18:00:00'
        },
    'verylarge': {
        'start': '2016-10-01T06:00:00', 'end': '2016-10-03T06:00:00'
        },
    'huge': {
        'start': '2016-10-01T06:00:00', 'end': '2016-10-20T06:00:00'
        }
    }
    
USE_TIME_INTERVAL = 'large'


def main():
    
    for node, node_par in settings.EIDA_NODES.items():
        
        print "===== using service at node {}".format(node)
        
        if node_par['services']['eida']['routing']['service'] is False:
            print "does not provide routing service, skipping\n"
            continue
        
        server = node_par['services']['eida']['routing']['server']
        endpoint = "{}/eidaws/routing/1/query".format(server)
        
        for check_node, check_node_par in settings.EIDA_NODES.items():
            
            print "-- trying SNCLs for node {}".format(check_node)
            
            payload = {
                'network': check_node_par['testquerysncls']['network'],
                'station': check_node_par['testquerysncls']['station'],
                'location': check_node_par['testquerysncls']['location'],
                'channel': check_node_par['testquerysncls']['channel'],
                'starttime': TEST_TIME_INTERVALS\
                        [USE_TIME_INTERVAL]['start'],
                'endtime': TEST_TIME_INTERVALS[USE_TIME_INTERVAL]\
                    ['end'],
                'service': 'dataselect',
                'format': 'post'
            }
            
            payload_wild = {
                'network': '*',
                'station': check_node_par['testquerysncls']['station'],
                'location': check_node_par['testquerysncls']['location'],
                'channel': check_node_par['testquerysncls']['channel'],
                'starttime': TEST_TIME_INTERVALS\
                        [USE_TIME_INTERVAL]['start'],
                'endtime': TEST_TIME_INTERVALS[USE_TIME_INTERVAL]\
                    ['end'],
                'service': 'dataselect',
                'format': 'post'
            }
            
            # fire GET request
            
            for pl in (payload, payload_wild):
                
                print "+++"
                
                try:
                    response = requests.get(endpoint, params=pl)
                        
                except requests.exceptions.ConnectionError:
                        
                    error_msg = "error: no connection"
                    print error_msg
                    continue
                
                if not response.ok:
                    print "error: code {}".format(response.status_code)
                
                print response.text


if __name__ == '__main__':
    main()
