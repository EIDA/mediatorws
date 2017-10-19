#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch stationlite server.

This file is part of the EIDA mediator/federator webservices.

"""

import argparse

from eidangservices.stationlite.server.app import main as start_app

def main():
    
    parser = argparse.ArgumentParser(
        prog="python -m stationlite.server",
        description='Launch EIDA stationlite web service.')
    
    # required=True
    parser.add_argument('--port', type=int, help='Server port')
    parser.add_argument(
        '--debug', action='store_true', default=False, 
        help="Run in debug mode.")

    args = parser.parse_args()

    start_app(debug=args.debug, port=args.port)
    

if __name__ == "__main__":
    main()
