#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch mediator server.

This file is part of the EIDA mediator/federator webservices.

"""

import argparse

from eidangservices.mediator.server.app import main as start_app

def main():
    
    parser = argparse.ArgumentParser(
        prog="python -m mediator.server",
        description='Launch EIDA mediator web service.')
    
    # required=True
    parser.add_argument('--port', type=int, help='Server port')
    parser.add_argument(
        '--tmpdir', type=str, default='', help='Directory for temp files.')
    
    parser.add_argument(
        '--federator', type=str, default='', help='Federator server URL.')
    
    parser.add_argument(
        '--debug', action='store_true', default=False, 
        help="Run in debug mode.")

    args = parser.parse_args()

    start_app(
        debug=args.debug, port=args.port, tmpdir=args.tmpdir, 
        federator=args.federator)
    

if __name__ == "__main__":
    main()
