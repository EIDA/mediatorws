# -*- coding: utf-8 -*-
"""
Mediator request handlers.

This file is part of the EIDA mediator/federator webservices.

"""

import datetime
import os

import flask
from flask import current_app
from flask_restful import abort, reqparse, request, Resource

from mediator import settings
from mediator.server import httperrors, parameters
from mediator.server.engine import dq
from mediator.utils import misc


QUERY_VALUE_SEPARATOR_CHAR = '='


class GeneralResource(Resource):
    """Handler for general resource."""

    def _process_request(self, fetch_args, mimetype, postfile=''):
        """Process request and send resulting file to client."""
        
        resource_path = process_request(fetch_args)

        if resource_path is None or os.path.getsize(resource_path) == 0:
            
            # TODO(fab): get user-supplied error code
            print "returned resource is empty"
            raise httperrors.NoDataError()
            
        else:
            
            # return contents of temp file
            try:
                return flask.send_file(resource_path, mimetype=mimetype)
            except Exception:
                # cannot send error code since response is already started
                # TODO(fab): how to let user know of error?
                pass


def process_request(args):
    """Write result of mediated query to file."""
    
    # foo = args.getpar(FDSNWSFETCH_OUTFILE_PARAM)
    tempfile_path = misc.get_temp_filepath()

    # TODO(fab): capture log output
    print args
    
    try:
        dq.process_dq(args, tempfile_path)
        
    except Exception, e:
        raise RuntimeError, "there was an exception: %s" % e

    # get contents of temp file
    if os.path.isfile(tempfile_path):
        return tempfile_path
    else:
        return None
