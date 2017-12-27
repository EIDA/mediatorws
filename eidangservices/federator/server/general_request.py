# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
# This file is part of EIDA NG webservices (eida-federator).
# 
# eida-federator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version.
#
# eida-federator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----
# 
# Copyright (c) Daniel Armbruster (ETH), Fabian Euchner (ETH)
#
# -----------------------------------------------------------------------------
"""
Federator request handlers.

This file is part of the EIDA mediator/federator webservices.

"""

import logging
import os

import flask
from flask import current_app, request
from flask_restful import Resource

import eidangservices as eidangws
from eidangservices import settings, utils
from eidangservices.federator.server import httperrors, route, misc

try:
    # Python 2.x
    import urlparse
except ImportError:
    # Python 3.x
    import urllib.parse as urlparse


# -----------------------------------------------------------------------------
class GeneralResource(Resource):
    """Handler for general resource."""

    LOGGER = "flask.app.federator.general_resource"

    def __init__(self):
        self.logger = logging.getLogger(self.LOGGER)
   
    # __init__ ()

    @property
    def path_tempfile(self):
        return misc.get_temp_filepath() 

    def _process_request(self, query_params, sncls, mimetype, path_tempfile,
            post=False):
        """
        Process a GET request and send the resulting file to the client.

        :param dict query_params: Dictionary of query parameters
        :param list sncls: List of SNCL objects
        :param str mimetype: The responses's mimetype
        :param path_tempfile: Path to the temporary file the combined output
        will be stored
        :param bool post: Process a POST request if set to True
        :return: The combined response (read from the temporary file)
        """
        postdata = None
        sncl_schema = eidangws.schema.SNCLSchema(many=True,
                                                 context={'request': request})
        sncls = sncl_schema.dump(sncls).data
        self.logger.debug('SNCLs (serialized): %s' % sncls)

        if post:
            # convert to postlines
            postdata = '\n'.join([' '.join(sncl.values()) for sncl in sncls])
        else:
            # merge SNCLs back to query parameters
            sncls = utils.convert_scnl_dicts_to_query_params(sncls)
            query_params.update(sncls)

        # TODO(damb): Improve mimetype handling.
        self.logger.debug((
            "Processing request: query_params={0}, path_tempfile={1}, "
            "post={2}, timeout={3}, retries={4}, "
            "retry_wait={5}, retry_lock={6}, threads={7}").format(
                    query_params,
                    path_tempfile,
                    bool(postdata), current_app.config['ROUTING_TIMEOUT'], 
                    current_app.config['ROUTING_RETRIES'],
                    current_app.config['ROUTING_RETRY_WAIT'], 
                    current_app.config['ROUTING_RETRY_LOCK'], 
                    current_app.config['NUM_THREADS']))

        resource_path = process_request(query_params,
                path_tempfile=path_tempfile,
                postdata=postdata,
                timeout=current_app.config['ROUTING_TIMEOUT'],
                retries=current_app.config['ROUTING_RETRIES'],
                retry_wait=current_app.config['ROUTING_RETRY_WAIT'],
                retry_lock=current_app.config['ROUTING_RETRY_LOCK'],
                threads=current_app.config['NUM_THREADS'])

        if resource_path is None or os.path.getsize(resource_path) == 0:
            # TODO(fab): get user-supplied error code
            raise httperrors.NoDataError()
            
        else:
            # return contents of temp file
            try:
                return flask.send_file(resource_path, mimetype=mimetype)
            except Exception:
                # cannot send error code since response is already started
                # TODO(fab): how to let user know of error?
                pass

    # _process_request ()

# class GeneralResource

# -----------------------------------------------------------------------------
def process_request(query_params, 
        path_tempfile=None,
        postdata=None,
        timeout=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_TIMEOUT,
        retries=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRIES,
        retry_wait=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_WAIT, 
        retry_lock=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_RETRY_LOCK,
        threads=settings.EIDA_FEDERATOR_DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS):
    """
    Route a *new* request.
   
    Routing is delegated to the :py:class:`route.WebserviceRouter`.

    :param dict query_params: The requests query arguments
    :param path_tempfile: Path to a temporary file the combined output will be
    dumped to
    :param postdata: SNCLs formated in the *FDSNWS POST* format
    :type postdata: str or None

    :return: Path to the temporary file containing the combined output or None.
    :rtype: str or None
    """

    if path_tempfile is None:
        return None

    # TODO(fab): capture log output
    # TODO(damb): ... and handle different type of exceptions

    try:
        cred = {}
        authdata = None

        url = route.RoutingURL(urlparse.urlparse(get_routing_url(
                    current_app.config['ROUTING_SERVICE'])),
                query_params)
        dest = open(path_tempfile, 'wb')

        router = route.WebserviceRouter(
                    url,
                    query_params=query_params,
                    postdata=postdata,
                    dest=dest,
                    timeout=timeout,
                    num_retries=retries,
                    retry_wait=retry_wait,
                    retry_lock=retry_lock,
                    max_threads=threads)
        router()

    except Exception:
        return None
    
    # get contents of temp file
    if os.path.isfile(path_tempfile):
        return path_tempfile
    else:
        return None

# process_request ()


def get_routing_url(routing_service):
    """
    Utility function. Get routing URL for routing service abbreviation.
   
    :param str routing_service: Routing service identifier
    :return: URL of the EIDA routing service
    :rtype: str

    In case an unknown identifier was passed the URL of a default EIDA routing
    service is returned.
    """
    
    try:
        server = settings.EIDA_NODES[routing_service]['services']['eida']\
            ['routing']['server']
    except KeyError:
        server = settings.EIDA_NODES[settings.DEFAULT_ROUTING_SERVICE]\
            ['services']['eida']['routing']['server']
        
    return "%s%s" % (server, settings.EIDA_ROUTING_PATH)

# get_routing_url ()
