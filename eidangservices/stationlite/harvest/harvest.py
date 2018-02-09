# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <harvest.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
#
# EIDA NG webservices are free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices are distributed in the hope that it will be useful,
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
# REVISION AND CHANGES
# 2018/02/09        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA NG stationlite harvesting facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import argparse
import contextlib
import datetime
import io
import logging
import sys
import traceback

import requests

from intervaltree import IntervalTree
from lxml import etree
from sqlalchemy import create_engine, or_
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from eidangservices import settings, utils
from eidangservices.stationlite.engine import db, orm
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error, ErrorWithTraceback
from eidangservices.utils.sncl import Stream
from eidangservices.utils.schema import StreamEpochSchema


__version__ = utils.get_version("stationlite")

Epochs = IntervalTree

# TODO(damb): Move to settings.py
STATIONXML_NS = '{http://www.fdsn.org/xml/station/1}'
STATIONXML_NETWORK_ELEMENT = '{}Network'.format(STATIONXML_NS)
STATIONXML_STATION_ELEMENT = '{}Station'.format(STATIONXML_NS)
STATIONXML_CHANNEL_ELEMENT = '{}Channel'.format(STATIONXML_NS)

STATIONXML_LATITUDE_ELEMENT = '{}Latitude'.format(STATIONXML_NS)
STATIONXML_LONGITUDE_ELEMENT = '{}Longitude'.format(STATIONXML_NS)
STATIONXML_DESCRIPTION_ELEMENT = '{}Description'.format(STATIONXML_NS)

XPATH_STATION_DESCRIPTION_ELEMENT = '/{}Site/{}Description'.format(
    STATIONXML_NS, STATIONXML_NS)

# ----------------------------------------------------------------------------
def db_engine(url):
    """
    check if url is a valid url
    """
    try:
        return create_engine(url)
    except Exception:
        raise argparse.ArgumentTypeError('Invalid database URL.')

# path_relative ()

@contextlib.contextmanager
def binary_stream_request(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        if response.status_code != 200:
            raise ResponseCodeNot200(response.status_code)

        yield io.BytesIO(response.content)

    except requests.exceptions.RequestException as err:
        raise RequestsError(err)

# binary_stream_request ()

def node_generator(exclude=[]):

    nodes = list(settings.EIDA_NODES)

    for node in nodes:
        if node not in exclude:
            yield node, settings.EIDA_NODES[node]

# node_generator ()

# ----------------------------------------------------------------------------
class RequestsError(Error):
    """Base request error ({})."""

class ResponseCodeNot200(RequestsError):
    """Response code not OK ({})."""

class NothingToDo(Error):
    """Nothing to do."""

# ----------------------------------------------------------------------------
class Harvester(object):
    """
    Abstract base class for harvesters, harvesting EIDA nodes.
    """
    LOGGER = 'eidangservices.stationlite.harvest.harvester'

    NS_ROUTINGXML = '{http://geofon.gfz-potsdam.de/ns/Routing/1.0/}'

    class HarvesterError(Error):
        """Base harvester error ({})."""

    class NotConfigured(ErrorWithTraceback):
        """Harvester not configured."""

    class InvalidNodeConfiguration(HarvesterError):
        """DB Node configuration is not valid for node '{}'."""

    class RoutingConfigXMLParsingError(HarvesterError):
        """Error while parsing routing configuration ({})."""

    class IntegrityError(HarvesterError):
        """IntegritiyError ({})."""

    def __init__(self, node_id, url_routing_config):
        self.node_id = node_id
        self._url_config = url_routing_config
        self._config = None
        self._node = None

        self.logger = logging.getLogger(self.LOGGER)
        self.is_configured = False

    @property
    def node(self):
        if self.is_configured:
            return self._node
        return None

    @property
    def url(self):
        return self._url_config

    @property
    def config(self):
        # proxy for fetching the config from the EIDA node
        if self._config is None:
            with binary_stream_request(self.url) as resp:
                self._config = resp

        return self._config

    # config ()

    def configure(self, session):
        try:
            self._node = session.query(orm.Node).\
                filter(orm.Node.name==self.node_id).\
                one()
        except (NoResultFound, MultipleResultsFound) as err:
            raise self.InvalidNodeConfiguration(self.node_id)

        self.is_configured = True

    # configure ()

    def harvest(self, session):
        raise NotImplementedError

# class Harvester


class RoutingHarvester(Harvester):
    """
    Implementation of an harvester harvesting the routing information from an
    EIDA node's routing service local configuration. The routing configuration
    is stored within

    <ns0:routing>
        <ns0:route>
            ...
        <ns0:route>
    </ns0:routing>

    elements.

    This harvester does not rely on the EIDA routing service anymore.
    """

    class StationXMLParsingError(Harvester.HarvesterError):
        """Error while parsing StationXML: ({})"""

    class InvalidCoordinateParameter(StationXMLParsingError):
        """Error while parsing coordinate parameter: ({})"""

    def __init__(self, node_id, url_routing_config, url_fdsn_station):
        super().__init__(node_id, url_routing_config)
        self.url_fdsn_station = url_fdsn_station

    # __init__ ()

    def harvest(self, session):
        """Harvest the routing configuration."""
        if not self.is_configured:
            raise self.NotConfigured()

        route_tag = '{}route'.format(self.NS_ROUTINGXML)
        _cached_services = db.get_cached_services()
        _cached_services = ['{}{}'.format(self.NS_ROUTINGXML, s)
                            for s in _cached_services]

        self.logger.debug('Harvesting routes for %s.' % self.node)
        # event driven parsing
        for event, route_element in etree.iterparse(self.config,
                                                    events=('end',),
                                                    tag=route_tag):

            if event == 'end' and len(route_element):

                stream = Stream.from_route_attrs(**dict(route_element.attrib))
                attrs = dict(stream._asdict())
                # create query parameters from stream attrs
                query_params = '&'.join(['{}={}'.format(query_param, query_val)
                                        for query_param, query_val in
                                        attrs.items()])
                _url_fdsn_station = '{}?{}&level=channel'.format(
                    self.url_fdsn_station, query_params)

                # XXX(damb): For every single route resolve FDSN wildcards
                # using the EIDA node's station service.
                # XXX(damb): Use the station service's GET method since the
                # POST method requires temporal constraints (both starttime and
                # endtime).
                # ----
                self.logger.debug('Resolving routing: (Request: %r).' %
                                  _url_fdsn_station)
                # TODO(damb): Request might be too large. Implement fix.
                nets = []
                stas = []
                cha_epochs = []
                with binary_stream_request(
                        _url_fdsn_station) as station_xml:
                    nets, stas, cha_epochs = self._harvest_from_stationxml(
                        session, station_xml)

                # NOTE(damb): only consider CACHED_SERVICEs
                for service_element in route_element.iter(*_cached_services):
                    # only consider priority=1
                    priority = service_element.get('priority')
                    if not priority or int(priority) != 1:
                        self.logger.info(
                            "Skipping {} due to priority '{}'.".format(
                                service_element, priority))
                        continue

                    # remove xml namespace
                    service_tag = service_element.tag[len(self.NS_ROUTINGXML):]
                    endpoint_url = service_element.get('address')
                    if not endpoint_url:
                        raise self.RoutingConfigXMLParsingError(
                            "Missing 'address' attrib.")

                    # fetch Endpoint object from DB
                    try:
                        endpoint = session.query(orm.Endpoint).\
                            filter(orm.Endpoint.url==endpoint_url).\
                            one()
                    except (NoResultFound, MultipleResultsFound) as err:
                        raise self.IntegrityError(err)

                    self.logger.debug('Harvesting routes for %r '
                                      '(service=%s, endpoint=%s).' %
                                      (stream, service_element.tag,
                                       endpoint.url))

                    for net in nets:
                        self.logger.debug('Populating Network<->Node relation '
                                '{}<->{}.'.format(net, self.node))
                        try:
                            _ = session.query(orm.NodeNetworkInventory).\
                                filter(orm.NodeNetworkInventory.network ==
                                       net).\
                                filter(orm.NodeNetworkInventory.node ==
                                       self.node).\
                                one()
                        except NoResultFound:
                            # create a new relation - it will be
                            # automatically added to the session
                            _ = orm.NodeNetworkInventory(network=net,
                                                         node=self.node)
                        except MultipleResultsFound as err:
                            raise self.IntegrityError(err)

                    try:
                        routing_starttime = utils.from_fdsnws_datetime(
                            service_element.get('start'))
                        routing_endtime = service_element.get('end')
                        # reset endtime due to 'end=""'
                        routing_endtime = (
                            utils.from_fdsnws_datetime(routing_endtime) if
                            routing_endtime is not None and
                            routing_endtime.strip() else None)
                    except Exception as err:
                        raise self.RoutingConfigXMLParsingError(err)

                    # configure routings
                    for cha_epoch in cha_epochs:
                        self.logger.debug(
                            'Populating ChannelEpoch<->Endpoint relation '
                            '{}<->{} ...'.format(cha_epoch, endpoint))
                        routing = session.query(orm.Routing).\
                            filter(orm.Routing.endpoint == endpoint).\
                            filter(orm.Routing.channel_epoch == cha_epoch).\
                            scalar()

                        if not routing:
                            routing = orm.Routing(
                                endpoint=endpoint,
                                channel_epoch=cha_epoch,
                                starttime=routing_starttime,
                                endtime=routing_endtime)
                        # update times if reconfigured@localconfig
                        if routing.starttime != routing_starttime:
                            routing.starttime = routing_starttime
                        if routing.endtime != routing_endtime:
                            routing.endtime = routing_endtime

                    # TODO(damb): Show stats for updated/inserted elements

    # harvest ()

    def _harvest_from_stationxml(self, session, station_xml):
        nets = []
        stas = []
        cha_epochs = []
        # parse station xml response for networks
        for event, network_element in etree.iterparse(
                station_xml, events=('end',), tag=STATIONXML_NETWORK_ELEMENT):

            if event == 'end':
                self.logger.debug("Processing network element: {}".format(
                    network_element))
                if (network_element.get('code') is None or
                        network_element.get('startDate') is None):
                    raise self.StationXMLParsingError(network_element)

                net = self._emerge_network(session, network_element)
                nets.append(net)

                # loop over station elements
                for station_element in network_element.iter(
                        STATIONXML_STATION_ELEMENT):

                    self.logger.debug("Processing station element: {}".format(
                                      station_element))
                    if (station_element.get('code') is None or
                            station_element.get('startDate') is None):
                        raise self.StationXMLParsingError(station_element)

                    sta = self._emerge_station(session, station_element)
                    stas.append(sta)

                    # loop over channel elements
                    for channel_element in station_element.iter(
                            STATIONXML_CHANNEL_ELEMENT):

                        self.logger.debug("Processing channel element: {}".\
                                          format(channel_element))
                        if (channel_element.get('code') is None or
                                channel_element.get('startDate') is None):
                            raise self.StationXMLParsingError(channel_element)

                        cha_epoch = self._emerge_channelepoch(session,
                                                              channel_element)
                        cha_epochs.append(cha_epoch)

                        # associate ChannelEpoch<->Station
                        sta.channel_epochs.append(cha_epoch)
                        # associate ChannelEpoch<->Network
                        try:
                            _ = session.query(
                                orm.ChannelEpochNetworkRelation).\
                                filter(
                                    orm.ChannelEpochNetworkRelation.network ==
                                    net).\
                                filter(
                                    orm.ChannelEpochNetworkRelation.\
                                    channel_epoch == cha_epoch).\
                                one()
                        except NoResultFound:
                            _ = orm.ChannelEpochNetworkRelation(
                                network=net, channel_epoch=cha_epoch)
                        except MultipleResultsFound as err:
                            raise self.IntegrityError(err)

                return nets, stas, cha_epochs

    # _harvest_from_stationxml ()

    def _emerge_network(self, session, network_element):
        """
        Factory method for a orm.Network object.
        """
        net_code = network_element.get('code')
        net_description = network_element[0].text
        net_start = utils.from_fdsnws_datetime(
            network_element.get('startDate'))
        net_end = network_element.get('endDate')
        if net_end is not None:
            net_end = utils.from_fdsnws_datetime(net_end)

        net = session.query(orm.Network).\
            filter(orm.Network.name == net_code).\
            scalar()

        # check if network already available - else create a new one
        if net:
            self.logger.debug("Updating '{}'".format(net))
            # check for available network_epoch - else create a new one
            net_epoch = session.query(orm.NetworkEpoch).join(orm.Network).\
                filter(orm.NetworkEpoch.description == net_description).\
                filter(orm.NetworkEpoch.starttime == net_start).\
                filter(orm.NetworkEpoch.endtime == net_end).\
                scalar()

            if not net_epoch:
                net_epoch = orm.NetworkEpoch(
                    description=net_description,
                    starttime=net_start,
                    endtime=net_end)
                net.network_epochs.append(net_epoch)
                self.logger.debug(
                    "Created new network_epoch object '{}'".format(
                        net_epoch))

        else:
            net = orm.Network(name=net_code)
            net_epoch = orm.NetworkEpoch(
                description=net_description,
                starttime=net_start,
                endtime=net_end)
            net.network_epochs.append(net_epoch)
            self.logger.debug("Created new network object '{}'".format(net))

            session.add(net)

        return net

    # _emerge_network ()

    def _emerge_station(self, session, station_element):
        """
        Factory method for a orm.Station object.
        """
        sta_code = station_element.get('code')
        try:
            sta_description = station_element.find(
                XPATH_STATION_DESCRIPTION_ELEMENT)
        except Exception:
            sta_description = ''
        sta_start = utils.from_fdsnws_datetime(
            station_element.get('startDate'))
        sta_end = station_element.get('endDate')

        try:
            sta_lat = float(station_element.find(
                STATIONXML_LATITUDE_ELEMENT).text)
            sta_lon = float(station_element.find(
                STATIONXML_LONGITUDE_ELEMENT).text)
        except Exception:
            raise self.InvalidCoordinateParameter(station_element)

        if sta_end is not None:
            sta_end = utils.from_fdsnws_datetime(sta_end)

        sta = session.query(orm.Station).\
            filter(orm.Station.name == sta_code).\
            scalar()

        # check if station already available - else create a new one
        if sta:
            self.logger.debug("Updating '{}'".format(sta))
            # check for available station_epoch - else create a new one
            sta_epoch = session.query(orm.StationEpoch).join(orm.Station).\
                filter(orm.StationEpoch.description == sta_description).\
                filter(orm.StationEpoch.starttime == sta_start).\
                filter(orm.StationEpoch.endtime == sta_end).\
                filter(orm.StationEpoch.latitude == sta_lat).\
                filter(orm.StationEpoch.longitude == sta_lon).\
                scalar()

            if not sta_epoch:
                station_epoch = orm.StationEpoch(
                    description=sta_description,
                    starttime=sta_start,
                    endtime=sta_end,
                    latitude=sta_lat,
                    longitude=sta_lon)
                sta.station_epochs.append(station_epoch)
                self.logger.debug(
                    "Created new station_epoch object '{}'".format(
                        station_epoch))

        else:
            sta = orm.Station(name=sta_code)
            station_epoch = orm.StationEpoch(
                description=sta_description,
                starttime=sta_start,
                endtime=sta_end,
                latitude=sta_lat,
                longitude=sta_lon)
            sta.station_epochs.append(station_epoch)
            self.logger.debug("Created new station object '{}'".format(sta))

            session.add(sta)

        return sta

    # _emerge_station ()

    def _emerge_channelepoch(self, session, channel_element):
        """
        Factory method for a orm.ChannelEpoch object.
        """
        cha_code = channel_element.get('code')
        cha_loc = channel_element.get('locationCode')
        cha_start = utils.from_fdsnws_datetime(
            channel_element.get('startDate'))
        cha_end = channel_element.get('endDate')
        try:
            cha_lat = float(channel_element.find(
                STATIONXML_LATITUDE_ELEMENT).text)
            cha_lon = float(channel_element.find(
                STATIONXML_LONGITUDE_ELEMENT).text)
        except Exception:
            raise self.InvalidCoordinateParameter(channel_element)

        if cha_end is not None:
            cha_end = utils.from_fdsnws_datetime(cha_end)

        # check for available channel_epoch - else create a new one
        cha_epoch = session.query(orm.ChannelEpoch).\
            filter(orm.ChannelEpoch.channel == cha_code).\
            filter(orm.ChannelEpoch.locationcode == cha_loc).\
            filter(orm.ChannelEpoch.starttime == cha_start).\
            filter(orm.ChannelEpoch.endtime == cha_end).\
            filter(orm.ChannelEpoch.latitude == cha_lat).\
            filter(orm.ChannelEpoch.longitude == cha_lon).\
            scalar()

        if not cha_epoch:
            cha_epoch = orm.ChannelEpoch(
                channel=cha_code,
                locationcode=cha_loc,
                starttime=cha_start,
                endtime=cha_end,
                latitude=cha_lat,
                longitude=cha_lon)
            self.logger.debug("Created new channel_epoch object '{}'".format(
                              cha_epoch))
            session.add(cha_epoch)

        return cha_epoch

    # _emerge_channelepoch ()

# class RoutingHarvester


class VNetHarvester(Harvester):
    """
    Implementation of an harvester harvesting the virtual network information
    from an EIDA node. Usually, the information is stored within the routing
    service's local configuration.

    This harvester does not rely on the EIDA routing service anymore.
    """

    class VNetHarvesterError(Harvester.HarvesterError):
        """Base error for virtual netowork harvesting ({})."""

    class GET:
        method = 'GET'

    def __init__(self, node_id, url_vnet_config):
        super().__init__(node_id, url_vnet_config)

    def harvest(self, session):
        if not self.is_configured:
            raise self.NotConfigured()

        vnet_tag = '{}vnetwork'.format(self.NS_ROUTINGXML)
        stream_tag = '{}stream'.format(self.NS_ROUTINGXML)
        se_schema = StreamEpochSchema(context={'request': self.GET})

        self.logger.debug('Harvesting virtual networks for %s.' % self.node)

        # event driven parsing
        for event, vnet_element in etree.iterparse(self.config,
                                                   events=('end',),
                                                   tag=vnet_tag):
            if event == 'end' and len(vnet_element):

                vnet = self._emerge_network(session, vnet_element,
                                            is_virtual=True)

                for stream_element in vnet_element.iter(tag=stream_tag):
                    self.logger.debug("Processing stream element: {}".\
                                      format(stream_element))
                    # convert attributes to dict
                    stream = Stream.from_route_attrs(
                        **dict(stream_element.attrib))
                    attrs = stream._asdict()
                    attrs['starttime'] = stream_element.get('start')
                    endtime = stream_element.get('end')
                    attrs['endtime'] = endtime if (endtime is None or
                                                   endtime.strip()) else None
                    # deserialize to StreamEpoch object
                    stream_epoch = se_schema.load(attrs).data
                    self.logger.debug("Processing {0!r} ...".format(
                        stream_epoch))

                    sql_stream_epoch = stream_epoch.fdsnws_to_sql_wildcards()
                    # check if the stream epoch definition is valid i.e. there
                    # must be at least one matching ChannelEpoch
                    query = session.query(orm.ChannelEpoch).\
                        join(orm.ChannelEpochNetworkRelation).\
                        join(orm.Network).\
                        join(orm.Station).\
                        filter(
                            orm.ChannelEpochNetworkRelation.\
                            channel_epoch_ref ==
                            orm.ChannelEpoch.oid).\
                        filter(orm.Network.name.like(
                               sql_stream_epoch.network)).\
                        filter(orm.Station.name.like(
                               sql_stream_epoch.station)).\
                        filter(orm.ChannelEpoch.locationcode.like(
                               sql_stream_epoch.location)).\
                        filter(orm.ChannelEpoch.channel.like(
                               sql_stream_epoch.channel)).\
                        filter(or_((orm.ChannelEpoch.endtime >
                                    sql_stream_epoch.starttime),
                                   (orm.ChannelEpoch.endtime.is_(None))))

                    if sql_stream_epoch.endtime:
                        query = query.\
                            filter(orm.ChannelEpoch.starttime <
                                   sql_stream_epoch.endtime)

                    channel_epochs = query.all()
                    if not channel_epochs:
                        self.logger.warn(
                            'No ChannelEpoch matching stream epoch '
                            '{0!r}'.format(stream_epoch))
                        continue

                    for channel_epoch in channel_epochs:

                        self.logger.debug(
                            'Processing virtual network configuration for '
                            'ChannelEpoch object {0!r}.'.format(channel_epoch))

                        # TODO(damb): fetch processed relations for stats
                        self._emerge_vnet_relation(
                            session, vnet, channel_epoch, sql_stream_epoch)

            # populate VNetwork<->Node
            self.logger.debug('Populating relation Network<->Node '
                              '{}<->{} ...'.format(vnet, self.node))
            try:
                _ = session.query(orm.NodeNetworkInventory).\
                    filter(orm.NodeNetworkInventory.network ==
                           vnet).\
                    filter(orm.NodeNetworkInventory.node ==
                           self.node).\
                    one()
            except NoResultFound:
                # create a new relation - it will be
                # automatically added to the session
                _ = orm.NodeNetworkInventory(network=vnet,
                                             node=self.node)
            except MultipleResultsFound as err:
                raise self.IntegrityError(err)

    # harvest ()

    def _emerge_network(self, session, element, is_virtual=False):
        """
        Factory method for a orm.Network
        """
        net_code = element.get('networkCode')
        if not net_code:
            raise self.VNetHarvesterError("Missing 'networkCode' attribute.")

        net = session.query(orm.Network).\
            filter(orm.Network.name == net_code).\
            scalar()

        # check if network already available - else create a new one
        if net:
            self.logger.debug("Updating network object '{}'".format(net))
        else:
            net = orm.Network(name=net_code,
                              is_virtual=is_virtual)
            self.logger.debug("Created new network object '{}'".format(net))
            session.add(net)

        return net

    # _emerge_network ()

    def _emerge_vnet_relation(
            self, session, vnet, channel_epoch, stream_epoch):
        """
        Factory method for a orm.ChannelEpochNetworkRelation object.
        """
        network_relation = None
        try:
            network_relation = session.query(
                orm.ChannelEpochNetworkRelation).\
                filter(
                    orm.ChannelEpochNetworkRelation.channel_epoch ==
                    channel_epoch).\
                filter(orm.ChannelEpochNetworkRelation.network ==
                       vnet).one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        if network_relation is None:
            # reset time constraint parameters if necessary
            start = stream_epoch.starttime
            if stream_epoch.starttime < channel_epoch.starttime:
                start = channel_epoch.starttime
                self.logger.info(
                    'Resetting starttime for stream epoch {0!r}.'.format(
                        stream_epoch))
            end = stream_epoch.endtime
            if (channel_epoch.endtime is not None and
                stream_epoch.endtime is None and
                    stream_epoch.starttime > channel_epoch.endtime):
                end = channel_epoch.endtime

            # create a new relation
            epoch = orm.Epoch(starttime=start, endtime=end)
            self.logger.debug(
                'Creating new ChannelEpochNetworkRelation object with '
                'Epochs {}.'.format([epoch]))

            return orm.ChannelEpochNetworkRelation(
                network=vnet,
                channel_epoch=channel_epoch,
                epochs=[epoch])

        # update existing relation
        orig_epochs = network_relation.epochs
        epochs = Epochs.from_tuples([e._as_datetime_tuple() for e in
                                     orig_epochs])
        end = stream_epoch.endtime
        if stream_epoch.endtime is None:
            end = datetime.datetime.max
        epochs.addi(start, end)
        epochs.merge_overlaps()

        epochs = [(v.begin, v.end) if v.end != datetime.datetime.max
                  else (v.begin, None) for v in sorted(epochs)]

        # check if epoch already in DB
        new_epochs = []
        for s, e in epochs:
            try:
                epoch = session.query(orm.Epoch).\
                    filter(orm.Epoch.starttime == s).\
                    filter(orm.Epoch.endtime == e).\
                    one_or_none()
                if epoch is None:
                    new_epochs.append(orm.Epoch(starttime=s,
                                                endtime=e))
            except MultipleResultsFound as err:
                raise self.IntegrityError(err)

        network_relation.epochs = new_epochs

        # remove orphaned entries
        # TODO(damb): wrap into function
        orphaned_epochs = [e for e in new_epochs if e not in orig_epochs]
        for e in orphaned_epochs:
            # remove orphaned relations in link table
            orphaned_relations = session.query(
                orm.vnet_relation_epoch_relation).\
                filter(orm.vnet_relation_epoch_relation.c.vnet_relation_ref ==
                       network_relation.oid).\
                filter(orm.vnet_relation_epoch_relation.c.epoch_ref == e.oid).\
                all()
            for r in orphaned_relations:
                session.delete(r)
            # check if the orphaned epoch still has a reference in the link
            # table
            relations = session.query(
                orm.vnet_relation_epoch_relation).\
                filter(orm.vnet_relation_epoch_relation.c.epoch_ref == e.oid).\
                all()
            if not relations:
                session.delete(e)
        session.commit()

        self.logger.debug(
            'Updated ChannelEpochNetworkRelation object {} with Epochs '
            '{}.'.format())

        return network_relation

    # _emerge_vnet_relation ()

# class VNetHarvester


class StationLiteHarvestApp(App):
    """
    Implementation of the harvesting application for EIDA StationLite.
    """

    def build_parser(self, parents=[]):
        """
        Configure a parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(prog="eida-stationlite-harvest",
                              description='Harvest for EIDA StationLite.',
                              parents=parents)
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)
        parser.add_argument('-D', '--db', type=db_engine, required=True,
                            metavar='URL', dest='db_engine',
                            help=('URL indicating the database dialect and '
                                  'connection arguments'))
        parser.add_argument('--nodes-exclude', nargs='+',
                            type=str, metavar='NODES',
                            default=' '.join(sorted(settings.EIDA_NODES)),
                            choices=sorted(settings.EIDA_NODES),
                            help=('Whitespace-separated list of nodes to be '
                                  'excluded. (choices: {%(choices)s})'))
        parser.add_argument('--no-routes', action='store_true', default=False,
                            dest='no_routes',
                            help=('Do not harvest <route></route> '
                                  'information.'))
        parser.add_argument('--no-vnetworks', action='store_true',
                            default=False, dest='no_vnetworks',
                            help=('Do not harvest <vnetwork></vnetwork> '
                                  'information.'))
        # TODO(damb): equipe truncate flag with a threshold
        #parser.add_argument('-t', '--truncate', action='store_true',
        #                    default=False,
        #                    help='Truncate DB (delete outdated information).')
        return parser

    # build_parser ()

    def run(self):
        """
        Run application.
        """
        # output work with
        # configure SQLAlchemy logging
        # log_level = self.logger.getEffectiveLevel()
        # logging.getLogger('sqlalchemy.engine').setLevel(log_level)

        exit_code = utils.ExitCodes.EXIT_SUCCESS
        if not self.args.no_routes and not self.args.no_vnetworks:
            raise NothingToDo()

        try:
            engine = self.args.db_engine
            Session = db.ScopedSession()
            Session.configure(bind=self.args.db_engine)

            # TODO(damb): Implement multithreaded harvesting using a thread
            # pool.
            self.logger.debug('Nodes to be processed: {}'.format(
                [n for n, _ in node_generator(
                    exclude=self.args.nodes_exclude)]))

            if not self.args.no_vnetworks:
                self.logger.warn(
                    'Deleting virtual network related entries from DB ...')
                db.delete_vnetworks()


            for node_name, node_par in node_generator(
                    exclude=self.args.nodes_exclude):
                url_routing_config = (
                    node_par['services']['eida']['routing']['server'] +
                    node_par['services']['eida']['routing']['uri_path_config'])
                url_vnet_config = (
                    node_par['services']['eida']['routing']['server'] +
                    node_par['services']['eida']['routing']\
                            ['uri_path_config_vnet'])
                url_fdsn_station = (
                    node_par['services']['fdsn']['server'] +
                    settings.FDSN_STATION_PATH +
                    settings.FDSN_QUERY_METHOD_TOKEN)

                if not self.args.no_routes:
                    self.logger.info(
                        'Processing routes from EIDA node %r.' % node_name)
                    try:
                        # harvest the routing configuration
                        h = RoutingHarvester(
                            node_name, url_routing_config, url_fdsn_station)

                        session=Session()
                        # XXX(damb): Maintain sessions within the scope of a
                        # harvesting process.
                        h.configure(session)

                        with db.session_guard(session) as _session:
                            h.harvest(_session)

                    except RequestsError as err:
                        self.logger.warning(str(err))
                else:
                    self.logger.warn(
                        'Disabled processing <route></route> '
                        'information for %r.' % node_name)

                if not self.args.no_vnetworks:
                    self.logger.info(
                        'Processing vnetworks from EIDA node %r.' % node_name)
                    try:
                        # harvest virtual network configuration
                        h = VNetHarvester(node_name, url_vnet_config)
                        session=Session()
                        # XXX(damb): Maintain sessions within the scope of a
                        # harvesting process.
                        h.configure(session)

                        with db.session_guard(session) as _session:
                            h.harvest(_session)

                    except RequestsError as err:
                        self.logger.warning(str(err))
                else:
                    self.logger.warn(
                        'Disabled processing <vnetwork></vnetwork> '
                        'information for %r.' % node_name)

        except Error as err:
            self.logger.error(err)
            exit_code = utils.ExitCodes.EXIT_ERROR
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.critical('Local Exception: %s' % err)
            self.logger.critical('Traceback information: ' +
                                 repr(traceback.format_exception(
                                     exc_type, exc_value, exc_traceback)))
            exit_code = utils.ExitCodes.EXIT_ERROR

        sys.exit(utils.ExitCodes.EXIT_ERROR)

    # run ()

# class StationLiteHarvestApp

# ----------------------------------------------------------------------------
def main():
    """
    main function for EIDA stationlite harvesting
    """

    app = StationLiteHarvestApp(log_id='STL')

    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            config_section=settings.EIDA_STATIONLITE_HARVEST_CONFIG_SECTION)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(utils.ExitCodes.EXIT_ERROR)

    app.run()

# main ()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()

# ---- END OF <harvest.py> ----
