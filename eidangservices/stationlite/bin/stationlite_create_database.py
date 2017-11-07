#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create SQLite database for "station light" service (routing cache for
EIDA federator web service).

"""

import sys

from gflags import DEFINE_string
from gflags import FLAGS


from eidangservices import settings
from eidangservices.stationlite.engine import db


DB_FILE = 'eida_stationlite.db'

DEFINE_string('db', DB_FILE, 'SQLite database file')


def main():
    _ = FLAGS(sys.argv)
    
    db.create_and_init_tables(FLAGS.db)


if __name__ == '__main__':
    main()
