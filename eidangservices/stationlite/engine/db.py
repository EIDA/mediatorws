#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Station "light" (stationlite) DB tools.

"""

import datetime
import dateutil
import os

from operator import itemgetter

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import (
    MetaData, Table, Column, Integer, Float, String, Unicode, DateTime, 
    ForeignKey, create_engine, insert, select, update, and_, func)


from eidangservices import settings


STD_CODE_LENGTH = 32
CHANNEL_CODE_LENGTH = 3
LOC_CODE_LENGTH = 2

DESCRIPTION_LENGTH = 512
URL_LENGTH = 256

SQL_TABLE_NAMES = (
    'station', 'stationepoch', 'network', 'networkepoch', 
    'station_network_relation', 'network_node_relation', 
    'channel', 'routing', 'node', 'endpoint', 'service')

CACHED_SERVICES = ('station', 'dataselect', 'wfcatalog')


def get_engine_and_connection(connection_uri):
    
    engine = create_engine(connection_uri)
    connection = engine.connect()
    
    return engine, connection
    
    
def create_and_init_tables(db_path):
    
    metadata = MetaData()
    
    tables = setup_tables(metadata)
    
    if os.path.isfile(db_path):
        error_msg = "error: db file {} already exists".format(db_path)
        raise RuntimeError, error_msg
    
    engine, connection = get_engine_and_connection(
        'sqlite:///{}'.format(db_path))
    
    metadata.create_all(engine)
    init_tables(connection, tables)

    
def setup_tables(metadata):
    
    # station
    station = Table('station', metadata,
        Column('oid', Integer(), primary_key=True),
        Column(
            'name', String(STD_CODE_LENGTH), nullable=False, index=True)
    )
    
    # stationepoch
    stationepoch = Table('stationepoch', metadata,
        Column('oid', Integer(), primary_key=True),
        Column(
            'station_ref', ForeignKey('station.oid')),
        Column('description', Unicode(DESCRIPTION_LENGTH)),
        Column('longitude', Float(), nullable=False, index=True),
        Column('latitude', Float(), nullable=False, index=True),
        Column('starttime', DateTime(), index=True),
        Column('endtime', DateTime(), index=True),
        Column(
            'lastseen', DateTime(), default=datetime.datetime.utcnow, 
            onupdate=datetime.datetime.utcnow)
    )
        
    # network
    network = Table('network', metadata,
        Column('oid', Integer(), primary_key=True),
        Column(
            'name', String(STD_CODE_LENGTH), nullable=False, index=True)
    )
    
    # networkepoch
    networkepoch = Table('networkepoch', metadata,
        Column('oid', Integer(), primary_key=True),
        Column(
            'network_ref', ForeignKey('network.oid')),
        Column('description', Unicode(DESCRIPTION_LENGTH)),
        Column('starttime', DateTime(), index=True),
        Column('endtime', DateTime(), index=True),
        Column('lastseen', DateTime(), default=datetime.datetime.utcnow, 
            onupdate=datetime.datetime.utcnow)
    )
        
    # station_network_relation
    station_network_relation = Table('station_network_relation', metadata,
        Column('oid', Integer(), primary_key=True),
        Column('station_ref', ForeignKey('station.oid')),
        Column('network_ref', ForeignKey('network.oid')),
        Column('starttime', DateTime()),
        Column('endtime', DateTime())
    )
    
    # network_node_relation
    network_node_relation = Table('network_node_relation', metadata,
        Column('oid', Integer(), primary_key=True),
        Column('network_ref', ForeignKey('network.oid')),
        Column('node_ref', ForeignKey('node.oid')),
        Column('lastseen', DateTime(), default=datetime.datetime.utcnow, 
            onupdate=datetime.datetime.utcnow)
    )
    
    # channel
    # TODO(fab): network_ref should reference networkepoch,
    # station_ref should reference stationepoch
    channel = Table('channel', metadata,
        Column('oid', Integer(), primary_key=True),
        Column(
            'code', String(CHANNEL_CODE_LENGTH), nullable=False, index=True),
        Column(
            'locationcode', String(LOC_CODE_LENGTH), nullable=False, 
            index=True),
        Column('longitude', Float(), nullable=False, index=True),
        Column('latitude', Float(), nullable=False, index=True),
        Column('station_ref', ForeignKey('station.oid')),
        Column('network_ref', ForeignKey('network.oid')),
        Column('starttime', DateTime(), index=True),
        Column('endtime', DateTime(), index=True),
        Column('lastseen', DateTime(), default=datetime.datetime.utcnow, 
            onupdate=datetime.datetime.utcnow)
    )
    
    # routing
    routing = Table('routing', metadata,
        Column('oid', Integer(), primary_key=True),
        Column('channel_ref', ForeignKey('channel.oid')),
        Column('endpoint_ref', ForeignKey('endpoint.oid')),
        Column('starttime', DateTime()),
        Column('endtime', DateTime()),
        Column('lastseen', DateTime(), default=datetime.datetime.utcnow, 
            onupdate=datetime.datetime.utcnow)
    )
    
    # node
    node = Table('node', metadata,
        Column('oid', Integer(), primary_key=True),
        Column('name', String(STD_CODE_LENGTH), nullable=False, unique=True),
        Column('description', Unicode(DESCRIPTION_LENGTH))
    )
    
    # endpoint
    endpoint = Table('endpoint', metadata,
        Column('oid', Integer(), primary_key=True),
        Column('url', String(URL_LENGTH), nullable=False),
        Column('service_ref', ForeignKey('service.oid')),
        Column('node_id', Integer())
    )
    
    # service
    service = Table('service', metadata,
        Column('oid', Integer(), primary_key=True),
        Column('name', String(STD_CODE_LENGTH), nullable=False, unique=True)
    )
    
    return dict(
        station=station, stationepoch=stationepoch, network=network, 
        networkepoch=networkepoch, 
        station_network_relation=station_network_relation, 
        network_node_relation=network_node_relation, channel=channel,
        routing=routing, node=node, endpoint=endpoint, service=service)


def init_tables(connection, tables):
    
    # populate service, node, endpoint
    ins_service = []
    ins_node = []
    ins_endpoint = []
    
    for node, node_par in settings.EIDA_NODES.items():
        ins_node.append(dict(name=node, description=unicode(node_par['name'])))

    ins = tables['node'].insert()
    r = connection.execute(ins, ins_node)
    
    for sv in CACHED_SERVICES:
        ins_service.append(dict(name=sv))
    
    ins = tables['service'].insert()
    r = connection.execute(ins, ins_service)
    
    for node, node_par in settings.EIDA_NODES.items():
        
        # get node id
        s = select([tables['node'].c.oid]).where(tables['node'].c.name == node)
        rp = connection.execute(s)
        r = rp.first()
        node_id = r[0]
        
        for sv in CACHED_SERVICES:
            
            # get service id
            s = select(
                [tables['service'].c.oid]).where(tables['service'].c.name == sv)
            rp = connection.execute(s)
            r = rp.first()
            
            service_id = r[0]
        
            url = "{}/fdsnws/{}/1/query".format(
                node_par['services']['fdsn']['server'], sv)
            
            ins_endpoint.append(
                dict(url=url, service_ref=service_id, node_id=node_id))

    ins = tables['endpoint'].insert()
    r = connection.execute(ins, ins_endpoint)


def get_db_tables(engine):
    
    tables = {}
    
    metadata = MetaData(engine, reflect=True)
    
    for tb in SQL_TABLE_NAMES:
        tables[tb] = metadata.tables[tb]
        
    return tables


def get_db_object_id(connection, table, column, value):
        
    s = select(
        [table.c.oid]).where(table.c[column] == value)
    
    rp = connection.execute(s)
    return rp.first()[0]


def get_db_endpoint_id_from_url(connection, db_tables, endpoint_url, service):
    """
    Return endpoint ID (and, if applicable, node ID) for given endpoint URL
    and service.
    
    """

    te = db_tables['endpoint']
    ts = db_tables['service']
    tn = db_tables['node']
    
    node_id = None
    
    # find endpoint ID of endpoint/service combination
    s = select([te.c.oid]).where(
        and_(
            te.c.url == endpoint_url,
            ts.c.name == service,
            te.c.service_ref == ts.c.oid
        )  
    )
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        
        # find service ID
        s = select([ts.c.oid]).where(ts.c.name == service)
        rp = connection.execute(s)
        service_id = rp.first()[0]
        
        # add endpoint - no node ID
        endpoint_id = db_insert_endpoint(
            connection, db_tables, endpoint_url, service_id)
    
    else:
        
        if len(r) > 1:
            print "ERROR_UNIQUE_ENDPOINT: more that one entries for same "\
                "url/service combination"
            
        endpoint_id = r[0][0]
        
        # find node ID
        s = select([tn.c.oid]).where(
            and_(
                te.c.oid == endpoint_id,
                te.c.node_id == tn.c.oid
            )
        )
    
        rp = connection.execute(s)
        r = rp.first()
        
        if r:
            node_id = r[0]
        
    return endpoint_id, node_id


def find_db_network_id(connection, tables, net_code):
    """Return network ID for given network code."""
    
    tn = tables['network']
    
    s = select([tn.c.oid]).where(tn.c.name == net_code)
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        network_id = None
    else:
        network_id = r[0][0]

    return network_id


def find_db_networkepoch_id(connection, tables, net):
    """Return network epoch ID for given network object."""
    
    tn = tables['network']
    tne = tables['networkepoch']
    
    s = select([tne.c.oid]).where(
        and_(
            tn.c.name == net['name'],
            tne.c.network_ref  == tn.c.oid,
            tne.c.description == net['description'],
            tne.c.starttime == to_db_timestamp(net['starttime']),
            tne.c.endtime == to_db_timestamp(net['endtime'])
        )  
    )
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        network_id = None
    else:
        network_id = r[0][0]
        update_lastseen(connection, tne, network_id)

    return network_id


def find_db_station_id(connection, tables, sta_code):
    """Return station ID for given station code."""
    
    ts = tables['station']
    
    s = select([ts.c.oid]).where(ts.c.name == sta_code)
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        station_id = None
    else:
        station_id = r[0][0]
        
    return station_id
        

def find_db_stationepoch_id(connection, tables, sta):
    """Return station epoch ID for given station object."""
    
    ts = tables['station']
    tse = tables['stationepoch']
    
    s = select([tse.c.oid]).where(
        and_(
            ts.c.name == sta['name'],
            tse.c.station_ref == ts.c.oid,
            tse.c.description == sta['description'],
            tse.c.starttime == to_db_timestamp(sta['starttime']),
            tse.c.endtime == to_db_timestamp(sta['endtime']),
            tse.c.longitude == sta['longitude'],
            tse.c.latitude == sta['latitude']
        )  
    )
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        station_id = None
    else:
        station_id = r[0][0]
        update_lastseen(connection, tse, station_id)
        
    return station_id


def find_db_channel_id(connection, tables, channel, station_id, network_id):
    """Return channel ID for given channel object and network/station IDs."""
    
    tc = tables['channel']

    s = select([tc.c.oid]).where(
        and_(
            tc.c.code == channel['code'],
            tc.c.locationcode == channel['locationcode'],
            tc.c.network_ref == network_id,
            tc.c.station_ref == station_id,
            tc.c.longitude == channel['longitude'],
            tc.c.latitude == channel['latitude'],
            tc.c.starttime == to_db_timestamp(channel['starttime']),
            tc.c.endtime == to_db_timestamp(channel['endtime'])
        )  
    )
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        channel_id = None
    else:
        channel_id = r[0][0]
        update_lastseen(connection, tc, channel_id)
        
    return channel_id


def find_db_routing_id(connection, tables, channel_id, endpoint_id, st, et):
    """Return routing ID for given channel/endpoint IDs and epoch."""

    tr = tables['routing']

    s = select([tr.c.oid]).where(
        and_(
            tr.c.channel_ref == channel_id,
            tr.c.endpoint_ref == endpoint_id,
            tr.c.starttime == to_db_timestamp(st),
            tr.c.endtime == to_db_timestamp(et)
        )  
    )
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        routing_id = None
    else:
        routing_id = r[0][0]
        update_lastseen(connection, tr, routing_id)
        
    return routing_id


def db_insert_network(connection, tables, net, node_id):

    network_id = find_db_network_id(connection, tables, net['name'])

    if network_id is not None:
        log_msg = "insert_network: network {} already exists, in "\
            "nodes:".format(net['name'])
        
    else:
        log_msg = "insert_network: ADDING network {}, in nodes:".format(
            net['name'])
        ins = tables['network'].insert({'name': net['name']})
        r = connection.execute(ins)
        network_id = r.inserted_primary_key[0]
    
    # add to network-node relation (network may be related to several nodes)
    nodes = db_insert_network_node_relation(
        connection, tables, network_id, node_id)
    
    #print "{} {}".format(log_msg, ' '.join(nodes))
        
    # insert network epoch, if new
    networkepoch_id = find_db_networkepoch_id(connection, tables, net)
    
    if networkepoch_id is None:
        ins = tables['networkepoch'].insert({
            'network_ref': network_id,
            'description': net['description'],
            'starttime': to_db_timestamp(net['starttime']),
            'endtime': to_db_timestamp(net['endtime'])
        })
        r = connection.execute(ins)
        
    return network_id

    
def db_insert_network_node_relation(connection, tables, network_id, node_id):
    
    tnnr = tables['network_node_relation']
    tn = tables['node']
    
    # check if relation already exists
    # update lastseen for existing entries
    upd = tnnr.update().where(
        and_(
            tnnr.c.network_ref == network_id,
            tnnr.c.node_ref == node_id
        )).values(lastseen=datetime.datetime.utcnow())
    rp = connection.execute(upd)

    # if it doesn't exist, insert it
    if rp.rowcount == 0:
        ins = tnnr.insert({'network_ref': network_id, 'node_ref': node_id})
        r = connection.execute(ins)
    
    # unique list of nodes that contain network, in ascending order of names
    s = select([tn.c.name.distinct().asc()]).where(
        and_(
            tnnr.c.network_ref == network_id,
            tnnr.c.node_ref == tn.c.oid
        )
    )
    rp = connection.execute(s)
    r = rp.fetchall()
    
    return map(itemgetter(0), r)


def db_insert_station(connection, tables, station, network_code):
    
    station_id = find_db_station_id(connection, tables, station['name'])

    # insert unless station ID is already there
    if station_id is None:

        ins = tables['station'].insert({'name': station['name']})
        r = connection.execute(ins)
        station_id = r.inserted_primary_key[0]
        
        # network ID
        network_id = find_db_network_id(connection, tables, network_code)
        
        _ = db_insert_station_network_relation(
            connection, tables, station_id, network_id, station['starttime'], 
            station['endtime'])
        
    stationepoch_id = find_db_stationepoch_id(connection, tables, station)
    
    if stationepoch_id is None:
        ins = tables['stationepoch'].insert({
            'station_ref': station_id,
            'description': station['description'],
            'longitude': station['longitude'],
            'latitude': station['latitude'],
            'starttime': to_db_timestamp(station['starttime']),
            'endtime': to_db_timestamp(station['endtime'])
        })
        r = connection.execute(ins)
  
    return station_id


def db_insert_station_network_relation(
    connection, tables, station_id, network_id, st, et):
    
    ins = tables['station_network_relation'].insert({
        'station_ref': station_id,
        'network_ref': network_id,
        'starttime': to_db_timestamp(st),
        'endtime': to_db_timestamp(et)
    })
    r = connection.execute(ins)
    
    return r.inserted_primary_key[0]


def db_insert_channel(connection, tables, channel, station_id, network_id):

    # check if not already there (from other node)
    channel_id = find_db_channel_id(
        connection, tables, channel, station_id, network_id)
    
    if channel_id is None:
        
        ins = tables['channel'].insert({
            'code': channel['code'],
            'locationcode': channel['locationcode'],
            'starttime': to_db_timestamp(channel['starttime']),
            'endtime': to_db_timestamp(channel['endtime']),
            'network_ref': network_id,
            'station_ref': station_id,
            'longitude': channel['longitude'],
            'latitude': channel['latitude']
        })
        r = connection.execute(ins)
        channel_id = r.inserted_primary_key[0]

    return channel_id


def db_insert_routing(
    connection, tables, channel_id, endpoint_url, service, st, et):

    routing_inserted = False
    
    # find endpoint and node IDs for given URL and service
    # if not found, insert into endpoint table
    endpoint_id, _ = get_db_endpoint_id_from_url(
        connection, tables, endpoint_url, service)
                            
    # check if entry is already in table 'routing' (updates lastseen)
    # if routing endpoint URL has changed, a new entry in table 'routing'
    # is created, 'lastseen' column of old entry is not updated
    routing_id = find_db_routing_id(
        connection, tables, channel_id, endpoint_id, st, et)
    
    if routing_id is None:

        ins = tables['routing'].insert({
            'channel_ref': channel_id,
            'endpoint_ref': endpoint_id,
            'starttime': to_db_timestamp(st),
            'endtime': to_db_timestamp(et)
        })
        _ = connection.execute(ins)
        routing_inserted = True
    
    return routing_inserted


def db_insert_endpoint(connection, tables, url, service_id, node_id=None):
    
    node_ins = {'url': url, 'service_ref': service_id}
    if node_id is not None:
        node_ins['node_id'] = node_id
    
    ins = tables['endpoint'].insert(node_ins)
    r = connection.execute(ins)
    
    return r.inserted_primary_key[0]


def update_lastseen(connection, table, oid):
    """Update lastseen column for given table and ID."""
    
    upd = table.update().where(table.c.oid == oid).values(
        lastseen=datetime.datetime.utcnow())
    _ = connection.execute(upd)


def db_remove_outdated_rows(connection, tables, now_utc):
    """Remove rows with 'lastseen' before starting time of last run."""
    
    for tablename in (
        'stationepoch', 'networkepoch', 'network_node_relation', 'channel', 
        'routing'):
        
        tb = tables[tablename]
        d = tb.delete().where(tb.c.lastseen < now_utc)
        r = connection.execute(d)
        
        print "table {}: deleted {} rows".format(tablename, r.rowcount)

    
def to_db_timestamp(timestamp_iso):
    
    if timestamp_iso is not None:
        timestamp_iso = dateutil.parser.parse(timestamp_iso)
        
    return timestamp_iso
