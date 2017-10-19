#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DB query tools for stationlite web service.

"""

import datetime
import dateutil
import os

from operator import itemgetter


from sqlalchemy import (
    MetaData, Table, Column, Integer, Float, String, Unicode, DateTime, 
    ForeignKey, create_engine, insert, select, update, and_, func)


from mediator import settings

from eidangservices.stationlite.engine import db



def find_db_networkepoch_id(connection, tables, net):
    """Return network epoch ID for given network object."""
    
    tn = tables['network']
    tne = tables['networkepoch']
    
    s = select([tne.c.oid]).where(
        and_(
            tn.c.name == net['name'],
            tne.c.network_ref  == tn.c.oid,
            tne.c.description == net['description'],
            tne.c.starttime == db.to_db_timestamp(net['starttime']),
            tne.c.endtime == db.to_db_timestamp(net['endtime'])
        )  
    )
    
    rp = connection.execute(s)
    r = rp.fetchall()
    
    if len(r) == 0:
        network_id = None
    else:
        network_id = r[0][0]
        db.update_lastseen(connection, tne, network_id)

    return network_id

