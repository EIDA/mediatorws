#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Harvest EIDA routing service in order to update local routing DB.
This is done to resolve SNCL wildcards.

Uses:
    singletony          https://github.com/andrew-azarov/singletony

"""

import datetime
import gzip
import io
import json
import logging
import os
import requests
import sys

from operator import itemgetter

from gflags import DEFINE_boolean
from gflags import DEFINE_string
from gflags import FLAGS

from lxml import etree
from sqlalchemy import create_engine


from eidanodetest.thirdparty.singletony import Singlet

from eidangservices import settings

from eidangservices.mediator.utils import misc as mediator_misc
from eidangservices.stationlite.engine import db


# logging
LOG_FILE_NAME = 'harvest_eida_routing.log'
DEFAULT_LOG_FORMAT = "%(asctime)s %(message)s"
LOG = logging.getLogger()

STATIONXML_NS = '{http://www.fdsn.org/xml/station/1}'

STATIONXML_NETWORK_ELEMENT = '{}Network'.format(STATIONXML_NS)
STATIONXML_STATION_ELEMENT = '{}Station'.format(STATIONXML_NS)
STATIONXML_CHANNEL_ELEMENT = '{}Channel'.format(STATIONXML_NS)

STATIONXML_LATITUDE_ELEMENT = '{}Latitude'.format(STATIONXML_NS)
STATIONXML_LONGITUDE_ELEMENT = '{}Longitude'.format(STATIONXML_NS)
STATIONXML_DESCRIPTION_ELEMENT = '{}Description'.format(STATIONXML_NS)

STATIONMXL_STATIONSITENAME_ELEMENT = '{0}Site/{0}Name'.format(STATIONXML_NS)

STATIONXML_CODE_ATTRIBUTE = 'code'
STATIONXML_LOCATIONCODE_ATTRIBUTE = 'locationCode'
STATIONXML_STARTDATE_ATTRIBUTE = 'startDate'
STATIONXML_ENDDATE_ATTRIBUTE = 'endDate'

ROUTING_NODE = 'gfz'

HARVEST_SERVICES = ('station', 'dataselect', 'wfcatalog')


DB_FILE = 'eida_stationlite.db'

STATION_NETWORK_FILE = "allstations_network.txt"
MISSING_ROUTES_TXT_FILE = "missing_routes.txt"
MISSING_ROUTES_GZIJPSON_FILE = "missing_routes.json.gz"


DEFINE_string('nodes', '', 'Comma-separated list of nodes')
DEFINE_string(
    'excludenodes', '', 
    'Comma-separated list of nodes to be excluded')

DEFINE_string('networks', '', 'Comma-separated list of networks')
DEFINE_string(
    'excludenetworks', '', 
    'Comma-separated list of networks to be excluded')

DEFINE_string('stations', '', 'Comma-separated list of networks')

DEFINE_string('db', DB_FILE, 'SQLite database file')
DEFINE_string('ld', '', 'Logging directory')
DEFINE_string('lf', LOG_FILE_NAME, 'Log file name')

DEFINE_string('label', '', 'Result label')
DEFINE_boolean('truncate', False, 'Truncate DB (delete outdated information)')



# allow only one instance to run at the same time
me = Singlet()

def main():
    
    _ = FLAGS(sys.argv)
    
    if FLAGS.nodes and FLAGS.excludenodes:
        error_msg = "--nodes and --excludenodes are mutually exclusive"
        raise RuntimeError, error_msg
    
    if FLAGS.networks and FLAGS.excludenetworks:
        error_msg = "--networks and --excludenetworks are mutually exclusive"
        raise RuntimeError, error_msg
    
    if not FLAGS.label:
        error_msg = "--label must be set"
        raise RuntimeError, error_msg
    
    global COMMANDLINE_PAR
    set_commandline_parameters()
    
    # logging - always overwrite last logfile
    logpath = get_outpath(FLAGS.lf, FLAGS.ld)
    logging.basicConfig(
        level=logging.INFO, format=DEFAULT_LOG_FORMAT, filename=logpath, 
        filemode='w')
    
    # check if DB file exists, if not, create and init
    if not os.path.isfile(FLAGS.db):
        db.create_and_init_tables(FLAGS.db)
    
    now_utc = datetime.datetime.utcnow()
    
    # connect to db
    engine = create_engine('sqlite:///{}'.format(FLAGS.db))
    connection = engine.connect()
    
    # get routing endpoint
    routing_server = mediator_misc.get_routing_url(ROUTING_NODE)
    routing_service_endpoint = "{}{}query".format(
        routing_server, settings.EIDA_ROUTING_PATH)
    
    all_stations = []
    missing_routes = {}
    
    db_tables = db.get_db_tables(engine)
    
    nodes_used = [x for x in node_generator()]
    node_count = len(nodes_used)
    
    # loop over nodes
    for node_idx, (node, node_par) in enumerate(node_generator()):
        
        missing_routes[node] = []
   
        # get node id from node table
        node_id = db.get_db_object_id(
            connection, db_tables['node'], 'name', node)
        
        LOG.info("===== getting data from node {}, id {} ({} of {})".format(
            node, node_id, node_idx+1, node_count))

        # get networks from node's station ws
        server = node_par['services']['fdsn']['server']
        endpoint = "{}/fdsnws/station/1/query".format(server)
        
        node_stream = io.BytesIO()
        
        # TODO(fab): set suitable timeout, save status if node does not respond
        LOG.info("querying networks")
        networks = get_networks_for_node(endpoint)
        
        if networks is None:
            LOG.error("cannot read networks from endpoint, skipping node")
            continue
        
        net_codes = map(itemgetter('name'), networks)
            
        # remove duplicates, order ascending
        net_codes_unique = sorted(list(set(net_codes)))
        networks_used = [x for x in network_code_generator(net_codes_unique)]
        network_count = len(networks_used)
            
        #LOG.info("unique network codes: {}".format(net_codes_unique))
        LOG.info("unique network codes: {}".format(networks_used))
        
        # populate tables network, networkepoch, network_node_relation
        for net in network_generator(sorted(networks, key=itemgetter('name'))):
            _ = db.db_insert_network(connection, db_tables, net, node_id)
        
        for netcode_idx, net_code in enumerate(
            network_code_generator(net_codes_unique)):
        
            LOG.info(
                "=== querying stations for network code {}".format(net_code))
            
            stations = get_stations_for_network(endpoint, net_code)
            
            if stations is None:
                LOG.error("cannot read stations from endpoint, skipping "\
                    "network")
                continue
            
            # populate tables station, stationepoch, station_network_relation
            for station in station_generator(
                    sorted(stations, key=itemgetter('name'))):
                _ = db.db_insert_station(
                    connection, db_tables, station, net_code)
            
            sta_codes = map(itemgetter('name'), stations)
            
            # remove duplicates, order ascending
            sta_codes_unique = sorted(list(set(sta_codes)))
            stations_used = [
                x for x in station_code_generator(sta_codes_unique)]
            station_count = len(stations_used)

            LOG.info("network {} with {} unique stations {}".format(
                net_code, station_count, stations_used))
            
            for stacode_idx, sta_code in enumerate(
                station_code_generator(sta_codes_unique)):
                
                LOG.info("querying channels")
                
                all_stations.append((sta_code, net_code))
                
                channels = get_channels_for_network_station(
                    endpoint, net_code, sta_code)
                
                if channels is None:
                    LOG.error("cannot read channels from endpoint, skipping "\
                        "station")
                    continue
                
                LOG.info("node {} ({} of {}): network {} ({} of {}), station "\
                    "{} ({} of {}) with channels:".format(
                        node, node_idx+1, node_count, net_code, netcode_idx+1, 
                        network_count, sta_code, stacode_idx+1, station_count))
                
                for cha in channels:
                    network_id = db.find_db_network_id(
                        connection, db_tables, net_code)
                    
                    if network_id is None:
                        LOG.error(
                            "ERROR_NO_NETWORK: no network found for channel")
                        continue
                    
                    station_id = db.find_db_station_id(
                        connection, db_tables, sta_code)
                    
                    if station_id is None:
                        LOG.error(
                            "ERROR_NO_STATION: no station found for channel")
                        continue
                    
                    # populate channel (check if already existing, from other
                    # node)
                    channel_id = db.db_insert_channel(
                        connection, db_tables, cha, station_id, network_id)
                    
                    resource_endpoints = []
                    
                    # this is True if a channel has at least one missing
                    # endpoint
                    channel_missing_endpoint = False
                    
                    # a combination of '+' and '=' symbols, e.g., route was
                    # inserted into table for station, dataselect, but not for
                    # wfcatalog: ++=
                    inserted_marker = ''
                    
                    for sv in HARVEST_SERVICES:
                        
                        missing_endpoint = True
                        routing_inserted = False
                        resource_endpoint = None
                        
                        try:
                            resource_endpoint = \
                                get_service_endpoint_per_channel(
                                    routing_service_endpoint, net_code, 
                                    sta_code, cha, sv)
                            
                            if resource_endpoint is not None:
                                missing_endpoint = False
                            else:
                                channel_missing_endpoint = True
                            
                        except RuntimeError, e:
                            missing_endpoint = True
                            channel_missing_endpoint = True
                            LOG.error(
                                "error: cannot get endpoint, {}".format(e))
                        
                        resource_endpoints.append(resource_endpoint)
                        
                        if not missing_endpoint:
                            
                            # populate/update routing
                            routing_inserted = db.db_insert_routing(
                                connection, db_tables, channel_id, 
                                resource_endpoint, sv, cha['starttime'], 
                                cha['endtime'])
                            
                        if routing_inserted:
                            inserted_marker += '+'
                        else:
                            inserted_marker += '='
                    
                    if channel_missing_endpoint:
                    
                        missing_routes[node].append({
                            'net': net_code,
                            'sta': sta_code,
                            'loc': cha['locationcode'],
                            'cha': cha['code'],
                            'st': cha['starttime'],
                            'et': cha['endtime'],
                            'route_station': resource_endpoints[0],
                            'route_dataselect': resource_endpoints[1],
                            'route_wfcatalog': resource_endpoints[2]
                        })
                    
                    out_str = "{0} {1}.{2}.{d[locationcode]}.{d[code]} "\
                        "{d[longitude]} {d[latitude]} {d[starttime]} "\
                        "{d[endtime]} {a[0]} {a[1]} {a[2]}".format(
                            inserted_marker, net_code, sta_code, d=cha, 
                            a=resource_endpoints)
                    
                    LOG.info(out_str)
                    node_stream.write("{}\n".format(out_str))
        
        outfile = "{}_{}_channels.txt".format(FLAGS.label, node)
        
        with open(outfile, 'w') as fh:
            fh.write(node_stream.getvalue())
            
        node_stream.close()
    
    # remove outdated entries from DB (that have not been seen in last run)
    # TODO(fab): this is not good if only a subset of nodes/networks/stations
    # is selected. Make optional. Add flag --truncate, not allowed with
    # restrictions. Careful if a node is down (does not respond).
    if FLAGS.truncate:
        LOG.info("remove outdated table rows")
        _ = db.db_remove_outdated_rows(connection, db_tables, now_utc)
    
    # write stations with network (including duplicates)
    # (duplicate: same station name with different network)
    # TODO(fab): improve reporting, read from DB
    with open("{}_{}".format(FLAGS.label, STATION_NETWORK_FILE), 'w') as fh:
        for sta in all_stations:
            fh.write("{d[0]}\t{d[1]}\n".format(d=sta))
    
    # check for duplicate station names (network aliases)
    sta_codes_unique = list(set(map(itemgetter(0), all_stations)))
    
    if len(sta_codes_unique) != len(all_stations):
        LOG.warning("WARNING_DUPLICATE_STATION: overall duplicate station "\
            "names, {} vs {} stations".format(
                len(sta_codes_unique), len(all_stations)))
    
    # write channels that have no routes (per node)
    # NOTE: this does not check if another node provides routes for the channel
    # TODO(fab): check routes from other nodes in DB
    with open("{}_{}".format(FLAGS.label, MISSING_ROUTES_TXT_FILE), 'w') as fh:
        
        for node, routes in missing_routes.items():
            
            fh.write("\n-{}\n\n".format(node))
            
            for route in routes:
                
                has_station_route = (route['route_station'] is not None)
                has_dataselect_route = (route['route_dataselect'] is not None)
                has_wfcatalog_route = (route['route_wfcatalog'] is not None)
                
                fh.write(
                    "{d[net]}.{d[sta]}.{d[loc]}.{d[cha]} {d[st]} {d[et]} {0} "\
                    "{1} {2}\n".format(
                        has_station_route, has_dataselect_route, 
                        has_wfcatalog_route, d=route))
                
    with gzip.open(
        "{}_{}".format(FLAGS.label, MISSING_ROUTES_GZIJPSON_FILE), 'wb') as fp:
            
        json.dump(missing_routes, fp, sort_keys=True, indent=4)
      

def get_networks_for_node(endpoint):
    
    # use all wildcards (default)
    payload = {'level': 'network', 'format': 'xml'}
    
    try:
        xml_root = get_root_from_fdsn_stationws(endpoint, payload)
    except ValueError:
        return None
    
    return get_networks_from_root(xml_root)


def get_stations_for_network(endpoint, net):
    
    # use all wildcards (default)
    payload = {'network': net, 'level': 'station', 'format': 'xml'}
    
    try:
        xml_root = get_root_from_fdsn_stationws(endpoint, payload)
    except ValueError:
        return None
    
    return get_stations_from_single_network(xml_root)


def get_channels_for_network_station(endpoint, net, sta):
    
    # use all wildcards (default)
    payload = {
        'network': net, 'station': sta, 'level': 'channel', 'format': 'xml'}
    
    try:
        xml_root = get_root_from_fdsn_stationws(endpoint, payload)
    except ValueError:
        return None
    
    return get_channels_from_single_station(xml_root)


def get_root_from_fdsn_stationws(endpoint, payload, printurl=True):
    
    response = get_from_http_endpoint(endpoint, payload)
    
    if response is None:
        error_msg = "no valid data received from endpoint {}".format(endpoint)
        raise ValueError, error_msg
    
    return etree.fromstring(response.content)


def get_from_http_endpoint(endpoint, payload, printurl=False):
    
    try:
        response = requests.get(endpoint, params=payload)
            
    except requests.exceptions.ConnectionError:
        LOG.error("error: no connection")
        return None
    
    if not response.ok:
        LOG.error("error: code {}".format(response.status_code))
        return None
    
    if printurl:
        LOG.info(response.url)
     
    return response


def get_service_endpoint_per_channel(
    routing_service_endpoint, net, sta, cha, service='dataselect'):
    
    routing_payload = get_routing_payload(net, sta, cha, service)
    
    routing_response = get_from_http_endpoint(
        routing_service_endpoint, routing_payload, printurl=False)
    
    if routing_response is None:
        error_msg = "HTTP connection error"
        raise RuntimeError, error_msg
    
    # this uses first resource endpoint in response
    # since there are no SNCL wildcards in request, there can only be
    # one endpoint
    resource_arr = routing_response.text.split()
    
    if not resource_arr:
        resource_endpoint = None
    else:
        resource_endpoint = resource_arr[0].strip()
        
    return resource_endpoint


def get_routing_payload(net, sta, cha, service='dataselect'):
    
    # translate empty location code to the SEED '--' placeholder
    if not cha['locationcode']:
        loc_code = '--'
    else:
        loc_code = cha['locationcode']
    
    routing_payload = {
        'network': net,
        'station': sta,
        'location': loc_code,
        'channel': cha['code'],
        'starttime': cha['starttime'],
        'endtime': cha['endtime'],
        'service': service,
        'format': 'post',
        'alternative': 'false'
    }
    
    return routing_payload


def get_networks_from_root(root):
    
    networks = root.findall(STATIONXML_NETWORK_ELEMENT)
    
    output_networks = []
    
    for net in networks:
        
        network_data = {
            'network': net,
            'name': net.get(STATIONXML_CODE_ATTRIBUTE),
            'starttime': net.get(STATIONXML_STARTDATE_ATTRIBUTE),
            'endtime': net.get(STATIONXML_ENDDATE_ATTRIBUTE),
            'description': net.findtext(
                STATIONXML_DESCRIPTION_ELEMENT, default='')
        }
        
        output_networks.append(network_data)
    
    return output_networks


def get_stations_from_single_network(root):
    
    networks = root.findall(STATIONXML_NETWORK_ELEMENT)
    if len(networks) > 1:
        LOG.warning(
            "WARNING_NETWORK: more than one Network elements in StationXML")
    
    output_stations = []
    
    # there can be more than a single Network element, one for each epoch
    # of stations
    for network in networks:
    
        LOG.info("network {}, start {}, end {}".format(
            network.get(STATIONXML_CODE_ATTRIBUTE), 
            network.get(STATIONXML_STARTDATE_ATTRIBUTE), 
            network.get(STATIONXML_ENDDATE_ATTRIBUTE)))
        
        stations = network.findall(STATIONXML_STATION_ELEMENT)
        
        for station in stations:
            
            station_data = {
                'station': station,
                'name': station.get(STATIONXML_CODE_ATTRIBUTE),
                'description': station.findtext(
                    STATIONMXL_STATIONSITENAME_ELEMENT),
                'longitude': float(
                    station.findtext(STATIONXML_LONGITUDE_ELEMENT)),
                'latitude': float(
                    station.findtext(STATIONXML_LATITUDE_ELEMENT)),
                'starttime': station.get(STATIONXML_STARTDATE_ATTRIBUTE),
                'endtime': station.get(STATIONXML_ENDDATE_ATTRIBUTE)
            }
            
            output_stations.append(station_data)
        
    return output_stations


def get_channels_from_single_station(root):
    
    networks = root.findall(STATIONXML_NETWORK_ELEMENT)
    if len(networks) > 1:
        LOG.warning(
            "WARNING_NETWORK: more than one Network elements in StationXML")
    
    output_channels = []
    
    # maybe there can be more than a single Network element (to find out)
    for network in networks:
    
        # NOTE: there can be more than a single Station element for the same
        # single station
        stations = network.findall(STATIONXML_STATION_ELEMENT)
        
        if len(stations) > 1:
            LOG.warning(
                "WARNING_STATION: more than one Station elements in StationXML")
        
        for station in stations:
            sta_name = station.get(STATIONXML_CODE_ATTRIBUTE)
            sta_description = station.findtext(
                STATIONMXL_STATIONSITENAME_ELEMENT)
            sta_lon = float(station.findtext(STATIONXML_LONGITUDE_ELEMENT))
            sta_lat = float(station.findtext(STATIONXML_LATITUDE_ELEMENT))
            sta_st = station.get(STATIONXML_STARTDATE_ATTRIBUTE)
            sta_et = station.get(STATIONXML_ENDDATE_ATTRIBUTE)
                    
            channels = station.findall(STATIONXML_CHANNEL_ELEMENT)
            
            for cha in channels:
                
                channel_data = {
                    'sta_name': sta_name,
                    'sta_description': sta_description,
                    'sta_longitude': sta_lon,
                    'sta_latitude': sta_lat,
                    'sta_starttime': sta_st,
                    'sta_endtime': sta_et,
                    'longitude': float(cha.findtext(STATIONXML_LONGITUDE_ELEMENT)),
                    'latitude': float(cha.findtext(STATIONXML_LATITUDE_ELEMENT)),
                    'channel': cha,
                    'locationcode': cha.get(STATIONXML_LOCATIONCODE_ATTRIBUTE),
                    'code': cha.get(STATIONXML_CODE_ATTRIBUTE),
                    'starttime': cha.get(STATIONXML_STARTDATE_ATTRIBUTE),
                    'endtime': cha.get(STATIONXML_ENDDATE_ATTRIBUTE)
                }
                
                output_channels.append(channel_data)
     
    return output_channels


def node_generator():
    
    global COMMANDLINE_PAR
    nodes = list(COMMANDLINE_PAR['the_node_list'])
    
    for node in nodes:
        node_par = settings.EIDA_NODES[node] 
        
        if node not in COMMANDLINE_PAR['the_excludenode_list']:
            yield node, node_par


def network_generator(networks):
    
    global COMMANDLINE_PAR
    
    if FLAGS.networks:
        for net in networks:
            if net['name'] in COMMANDLINE_PAR['the_network_list']:
                yield net
                
    elif FLAGS.excludenetworks:
        for net in networks:
           if net['name'] not in COMMANDLINE_PAR['the_excludenetwork_list']:
                yield net
                
    else:
        for net in networks:
            yield net


def network_code_generator(network_codes):
    
    global COMMANDLINE_PAR
    
    if FLAGS.networks:
        for code in network_codes:
            if code in COMMANDLINE_PAR['the_network_list']:
                yield code
                
    elif FLAGS.excludenetworks:
        for code in network_codes:
           if code not in COMMANDLINE_PAR['the_excludenetwork_list']:
                yield code
                
    else:
        for code in network_codes:
            yield code
            
            
def station_generator(stations):
    
    global COMMANDLINE_PAR
    
    if FLAGS.stations:
        for sta in stations:
            if sta['name'] in COMMANDLINE_PAR['the_station_list']:
                yield sta
           
    else:
        for sta in stations:
            yield sta


def station_code_generator(station_codes):
    
    global COMMANDLINE_PAR
    
    if FLAGS.stations:
        for code in station_codes:
            if code in COMMANDLINE_PAR['the_station_list']:
                yield code
           
    else:
        for code in station_codes:
            yield code
            

def get_outpath(outfile, dir=''):
    
    if dir:
        outpath = os.path.join(dir, outfile)
    else:
        outpath = outfile
    
    if os.path.dirname(outpath) and not(
        os.path.isdir(os.path.dirname(outpath))):
        
        os.makedirs(os.path.dirname(outpath))
        
    return outpath


def set_commandline_parameters():

    # nodes
    if FLAGS.nodes:
        COMMANDLINE_PAR['the_node_list'] = [
            x.strip() for x in FLAGS.nodes.split(',')]
    else:
        COMMANDLINE_PAR['the_node_list'] = sorted(settings.EIDA_NODES.keys())
    
    if FLAGS.excludenodes:
        COMMANDLINE_PAR['the_excludenode_list'] = [
            x.strip() for x in FLAGS.excludenodes.split(',')]
    else:
        COMMANDLINE_PAR['the_excludenode_list'] = []

    # networks
    if FLAGS.networks:
        COMMANDLINE_PAR['the_network_list'] = [
            x.strip() for x in FLAGS.networks.split(',')]
    else:
        COMMANDLINE_PAR['the_network_list'] = []
        
    if FLAGS.excludenetworks:
        COMMANDLINE_PAR['the_excludenetwork_list'] = [
            x.strip() for x in FLAGS.excludenetworks.split(',')]
    else:
        COMMANDLINE_PAR['the_excludenetwork_list'] = []
        
    # stations
    if FLAGS.stations:
        COMMANDLINE_PAR['the_station_list'] = [
            x.strip() for x in FLAGS.stations.split(',')]
    else:
        COMMANDLINE_PAR['the_station_list'] = []


if __name__ == '__main__':
    COMMANDLINE_PAR = {}
    main()
