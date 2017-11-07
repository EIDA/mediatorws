#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch federator server.

This file is part of the EIDA mediator/federator webservices.

"""

import argparse

from eidangservices.federator.server.app import main as start_app

def main():
    
    parser = argparse.ArgumentParser(
        prog="python -m federator.server",
        description='Launch EIDA federator web service.')
    
    # required=True
    parser.add_argument('--port', type=int, help='Server port')
    parser.add_argument(
        '--routing', type=str, default='gfz', help='Routing service')
    parser.add_argument(
        '--tmpdir', type=str, default='', help='Directory for temp files.')
    parser.add_argument(
        '--debug', action='store_true', default=False, 
        help="Run in debug mode.")

    args = parser.parse_args()

    start_app(
        debug=args.debug, port=args.port, routing=args.routing, 
        tmpdir=args.tmpdir)
    

if __name__ == "__main__":
    main()
