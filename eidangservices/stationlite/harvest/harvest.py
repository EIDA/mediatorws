# -*- coding: utf-8 -*-
"""
EIDA NG stationlite harvesting facilities.
"""

import collections
import datetime
import functools
import logging
import sys
import traceback
import warnings

import requests

from urllib.parse import urlparse

from fasteners import InterProcessLock
from lxml import etree
from obspy import read_inventory, UTCDateTime
from sqlalchemy import inspect
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.exc import OperationalError

from eidangservices import settings
from eidangservices.stationlite import __version__
from eidangservices.stationlite.engine import db, orm
from eidangservices.stationlite.misc import db_engine, node_generator
from eidangservices.utils.app import CustomParser, App, AppError
from eidangservices.utils.error import Error, ExitCodes
from eidangservices.utils.sncl import Stream, StreamEpoch
from eidangservices.utils.request import (binary_request, RequestsError,
                                          NoContent)


class NothingToDo(Error):
    """Nothing to do."""


class AlreadyHarvesting(Error):
    """There seems to be a harvesting process already in action ({})."""


# ----------------------------------------------------------------------------
class Harvester:
    """
    Abstract base class for harvesters, harvesting EIDA nodes.

    :param str node_id: EIDA node identifier
    :param str url_routing_config: URL to routing configuration file.
    """
    LOGGER = 'eidangservices.stationlite.harvest.harvester'

    NS_ROUTINGXML = '{http://geofon.gfz-potsdam.de/ns/Routing/1.0/}'

    class HarvesterError(Error):
        """Base harvester error ({})."""

    class ValidationError(HarvesterError):
        """ValidationError ({})."""

    class RoutingConfigXMLParsingError(HarvesterError):
        """Error while parsing routing configuration ({})."""

    class IntegrityError(HarvesterError):
        """IntegrityError ({})."""

    def __init__(self, node_id, url_routing_config):
        self.node_id = node_id
        self._url_config = url_routing_config
        self._config = None

        self.logger = logging.getLogger(self.LOGGER)

    @property
    def node(self):
        return self.node_id

    @property
    def url(self):
        return self._url_config

    @property
    def config(self):
        # proxy for fetching the config from the EIDA node
        if self._config is None:
            req = functools.partial(requests.get, self.url)
            with binary_request(req) as resp:
                self._config = resp

        return self._config

    @staticmethod
    def _update_lastseen(obj):
        obj.lastseen = datetime.datetime.utcnow()

    def harvest(self, session):
        raise NotImplementedError


class RoutingHarvester(Harvester):
    """
    Implementation of an harvester harvesting the routing information from an
    EIDA node's routing service local configuration. The routing configuration
    is stored within

    .. code::

        <ns0:routing>
            <ns0:route>
                ...
            <ns0:route>
        </ns0:routing>

    elements.

    This harvester relies on the :code:`eida-routing` :code:`localconfig`
    configuration files.

    :param str node_id: EIDA node identifier
    :param str url_routing_config: URL to :code:`eida-routing`
        :code:`localconfig: configuration files
    :param list services: List of EIDA services to be harvested
    """

    STATION_TAG = 'station'

    DEFAULT_RESTRICTED_STATUS = 'open'

    class StationXMLParsingError(Harvester.HarvesterError):
        """Error while parsing StationXML: ({})"""

    BaseNode = collections.namedtuple('BaseNode', ['restricted_status'])

    def __init__(self, node_id, url_routing_config, **kwargs):
        super().__init__(node_id, url_routing_config)

        self._services = kwargs.get(
            'services', settings.EIDA_STATIONLITE_HARVEST_SERVICES)

    # __init__ ()

    def harvest(self, session):
        """Harvest the routing configuration."""

        route_tag = '{}route'.format(self.NS_ROUTINGXML)
        _services = ['{}{}'.format(self.NS_ROUTINGXML, s)
                     for s in self._services]

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

                # extract fdsn-station service url for each route
                urls = set([
                    e.get('address') for e in route_element.iter(
                        '{}{}'.format(self.NS_ROUTINGXML, self.STATION_TAG))
                    if int(e.get('priority', 0)) == 1])

                if (len(urls) == 0 and len([e for e in
                    route_element.iter() if int(e.get('priority',
                                                0)) == 1]) == 0):
                    # NOTE(damb): Skip routes which contain exclusively
                    # 'priority == 2' services
                    continue

                elif len(urls) > 1:
                    # NOTE(damb): Currently we cannot handle multiple
                    # fdsn-station urls i.e. for multiple routed epochs
                    raise self.IntegrityError(
                        ('Missing <station></station> element for '
                         '{} ({}).'.format(route_element, urls)))

                _url_fdsn_station = '{}?{}&level=channel'.format(
                    urls.pop(), query_params)

                self._validate_url_path(_url_fdsn_station, 'station')

                # XXX(damb): For every single route resolve FDSN wildcards
                # using the route's station service.
                # XXX(damb): Use the station service's GET method since the
                # POST method requires temporal constraints (both starttime and
                # endtime).
                # ----
                self.logger.debug('Resolving routing: (Request: %r).' %
                                  _url_fdsn_station)
                nets = []
                stas = []
                chas = []
                try:
                    # TODO(damb): Request might be too large. Implement fix.
                    req = functools.partial(requests.get, _url_fdsn_station)
                    with binary_request(req) as station_xml:
                        nets, stas, chas = \
                            self._harvest_from_stationxml(session, station_xml)

                except NoContent as err:
                    self.logger.warning(str(err))
                    continue

                for service_element in route_element.iter(*_services):
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

                    self._validate_url_path(endpoint_url, service_tag)

                    service = self._emerge_service(session, service_tag)
                    endpoint = self._emerge_endpoint(session, endpoint_url,
                                                     service)

                    self.logger.debug('Processing routes for %r '
                                      '(service=%s, endpoint=%s).' %
                                      (stream, service_element.tag,
                                       endpoint.url))

                    try:
                        routing_starttime = UTCDateTime(
                            service_element.get('start'),
                            iso8601=True).datetime
                        routing_endtime = service_element.get('end')
                        # reset endtime due to 'end=""'
                        routing_endtime = (
                            UTCDateTime(routing_endtime,
                                        iso8601=True).datetime if
                            routing_endtime is not None and
                            routing_endtime.strip() else None)
                    except Exception as err:
                        raise self.RoutingConfigXMLParsingError(err)

                    # configure routings
                    for cha_epoch in chas:

                        if inspect(cha_epoch).deleted:
                            # In case a orm.ChannelEpoch object is marked as
                            # deleted but harvested within the same harvesting
                            # run this is a strong hint for an integrity issue
                            # within the FDSN station InventoryXML.
                            msg = ('InventoryXML integrity issue for '
                                   '{0!r}'.format(cha_epoch))
                            warnings.warn(msg)
                            self.logger.warning(msg)
                            continue

                        self.logger.debug(
                            'Processing ChannelEpoch<->Endpoint relation '
                            '{}<->{} ...'.format(cha_epoch, endpoint))

                        _ = self._emerge_routing(
                            session, cha_epoch, endpoint, routing_starttime,
                            routing_endtime)

        # TODO(damb): Show stats for updated/inserted elements

    def _harvest_from_stationxml(self, session, station_xml):
        """
        Create/update Network, Station and ChannelEpoch objects from a
        station.xml file.

        :param :cls:`sqlalchemy.orm.sessionSession` session: SQLAlchemy session
        :param :cls:`io.BinaryIO` station_xml: Station XML file stream
        """

        try:
            inventory = read_inventory(station_xml, format='STATIONXML')
        except Exception as err:
            raise self.StationXMLParsingError(err)

        nets = []
        stas = []
        chas = []
        for inv_network in inventory.networks:
            self.logger.debug("Processing network: {0!r}".format(
                              inv_network))
            net, base_node = self._emerge_network(session, inv_network)
            nets.append(net)

            for inv_station in inv_network.stations:
                self.logger.debug("Processing station: {0!r}".format(
                                  inv_station))
                sta, base_node = self._emerge_station(session, inv_station,
                                                      base_node)
                stas.append(sta)

                for inv_channel in inv_station.channels:
                    self.logger.debug(
                        "Processing channel: {0!r}".format(inv_channel))
                    cha_epoch = self._emerge_channelepoch(
                        session, inv_channel, net, sta, base_node)
                    chas.append(cha_epoch)

        return nets, stas, chas

    def _emerge_service(self, session, service_tag):
        """
        Factory method for a orm.Service object.
        """
        try:
            service = session.query(orm.Service).\
                filter(orm.Service.name == service_tag).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        if service is None:
            service = orm.Service(name=service_tag)
            session.add(service)
            self.logger.debug(
                "Created new service object '{}'".format(
                    service))

        return service

    def _emerge_endpoint(self, session, url, service):
        """
        Factory method for a orm.Endpoint object.
        """

        try:
            endpoint = session.query(orm.Endpoint).\
                filter(orm.Endpoint.url == url).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        if endpoint is None:
            endpoint = orm.Endpoint(url=url,
                                    service=service)
            session.add(endpoint)
            self.logger.debug(
                "Created new endpoint object '{}'".format(
                    endpoint))

        return endpoint

    def _emerge_network(self, session, network):
        """
        Factory method for a :py:class:`orm.Network` object.

        .. note::

            Currently for network epochs there is no validation performed if an
            overlapping epoch exists.
        """
        try:
            net = session.query(orm.Network).\
                filter(orm.Network.name == network.code).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        end_date = network.end_date
        if end_date is not None:
            end_date = end_date.datetime

        restricted_status = (self.DEFAULT_RESTRICTED_STATUS
                             if network.restricted_status is None else
                             network.restricted_status)

        # check if network already available - else create a new one
        if net is None:
            net = orm.Network(name=network.code)
            net_epoch = orm.NetworkEpoch(
                description=network.description,
                starttime=network.start_date.datetime,
                endtime=end_date,
                restrictedstatus=restricted_status)
            net.network_epochs.append(net_epoch)
            self.logger.debug("Created new network object '{}'".format(net))

            session.add(net)

        else:
            self.logger.debug("Updating '{}'".format(net))
            # check for available network_epoch - else create a new one
            try:
                net_epoch = session.query(orm.NetworkEpoch).join(orm.Network).\
                    filter(orm.NetworkEpoch.network == net).\
                    filter(orm.NetworkEpoch.description ==
                           network.description).\
                    filter(orm.NetworkEpoch.starttime ==
                           network.start_date.datetime).\
                    filter(orm.NetworkEpoch.endtime == end_date).\
                    filter(orm.NetworkEpoch.restrictedstatus ==
                           restricted_status).\
                    one_or_none()
            except MultipleResultsFound as err:
                raise self.IntegrityError(err)

            if net_epoch is None:
                net_epoch = orm.NetworkEpoch(
                    description=network.description,
                    starttime=network.start_date.datetime,
                    endtime=end_date,
                    restrictedstatus=restricted_status)
                net.network_epochs.append(net_epoch)
                self.logger.debug(
                    "Created new network_epoch object '{}'".format(
                        net_epoch))
            else:
                # XXX(damb): silently update epoch parameters
                self._update_epoch(net_epoch,
                                   restricted_status=restricted_status)
                self._update_lastseen(net_epoch)

        return net, self.BaseNode(restricted_status=restricted_status)

    def _emerge_station(self, session, station, base_node):
        """
        Factory method for a :py:class:`orm.Station` object.

        .. note::

            Currently for station epochs there is no validation performed if an
            overlapping epoch exists.
        """
        try:
            sta = session.query(orm.Station).\
                filter(orm.Station.name == station.code).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        end_date = station.end_date
        if end_date is not None:
            end_date = end_date.datetime

        restricted_status = (
            base_node.restricted_status
            if station.restricted_status is None else
            station.restricted_status)

        # check if station already available - else create a new one
        if sta is None:
            sta = orm.Station(name=station.code)
            station_epoch = orm.StationEpoch(
                description=station.description,
                starttime=station.start_date.datetime,
                endtime=end_date,
                latitude=station.latitude,
                longitude=station.longitude,
                restrictedstatus=station.restricted_status)
            sta.station_epochs.append(station_epoch)
            self.logger.debug("Created new station object '{}'".format(sta))

            session.add(sta)

        else:
            self.logger.debug("Updating '{}'".format(sta))
            # check for available station_epoch - else create a new one
            try:
                sta_epoch = session.query(orm.StationEpoch).\
                    filter(orm.StationEpoch.station == sta).\
                    filter(orm.StationEpoch.description ==
                           station.description).\
                    filter(orm.StationEpoch.starttime ==
                           station.start_date.datetime).\
                    filter(orm.StationEpoch.endtime == end_date).\
                    filter(orm.StationEpoch.latitude == station.latitude).\
                    filter(orm.StationEpoch.longitude == station.longitude).\
                    one_or_none()
            except MultipleResultsFound as err:
                raise self.IntegrityError(err)

            if sta_epoch is None:
                station_epoch = orm.StationEpoch(
                    description=station.description,
                    starttime=station.start_date.datetime,
                    endtime=end_date,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    restrictedstatus=restricted_status)
                sta.station_epochs.append(station_epoch)
                self.logger.debug(
                    "Created new station_epoch object '{}'".format(
                        station_epoch))
            else:
                # XXX(damb): silently update inherited base node parameters
                self._update_epoch(sta_epoch,
                                   restricted_status=restricted_status)
                self._update_lastseen(sta_epoch)

        return sta, self.BaseNode(restricted_status=restricted_status)

    def _emerge_channelepoch(self, session, channel, network, station,
                             base_node):
        """
        Factory method for a :py:class:`orm.ChannelEpoch` object.
        """
        end_date = channel.end_date
        if end_date is not None:
            end_date = end_date.datetime

        restricted_status = (
            base_node.restricted_status
            if channel.restricted_status is None else
            channel.restricted_status)

        # check for available, overlapping channel_epoch (not identical)
        # XXX(damb) Overlapping orm.ChannelEpochs regarding time constraints
        # are updated (i.e. implemented as: delete - insert).
        query = session.query(orm.ChannelEpoch).\
            filter(orm.ChannelEpoch.network == network).\
            filter(orm.ChannelEpoch.station == station).\
            filter(orm.ChannelEpoch.channel == channel.code).\
            filter(orm.ChannelEpoch.locationcode == channel.location_code)

        # check if overlapping with ChannelEpoch already existing
        if end_date is None:
            query = query.\
                filter(((orm.ChannelEpoch.starttime <
                         channel.start_date.datetime) &
                        ((orm.ChannelEpoch.endtime == None) |  # noqa
                         (channel.start_date.datetime <
                          orm.ChannelEpoch.endtime))) |
                       (orm.ChannelEpoch.starttime >
                        channel.start_date.datetime))
        else:
            query = query.\
                filter(((orm.ChannelEpoch.starttime <
                         channel.start_date.datetime) &
                       ((orm.ChannelEpoch.endtime == None) |  # noqa
                        (channel.start_date.datetime <
                         orm.ChannelEpoch.endtime))) |
                       ((orm.ChannelEpoch.starttime >
                         channel.start_date.datetime) &
                        (end_date > orm.ChannelEpoch.starttime)))

        cha_epochs_to_update = query.all()

        if cha_epochs_to_update:
            self.logger.warning('Found overlapping orm.ChannelEpoch objects '
                                '{}'.format(cha_epochs_to_update))

        # check for ChannelEpochs with changed restricted status property
        query = session.query(orm.ChannelEpoch).\
            filter(orm.ChannelEpoch.network == network).\
            filter(orm.ChannelEpoch.station == station).\
            filter(orm.ChannelEpoch.channel == channel.code).\
            filter(orm.ChannelEpoch.locationcode == channel.location_code).\
            filter(orm.ChannelEpoch.restrictedstatus !=
                   channel.restricted_status)

        cha_epochs_to_update.extend(query.all())

        # delete affected (overlapping/ changed restrictedstatus) epochs
        # including the corresponding orm.Routing entries
        for cha_epoch in cha_epochs_to_update:
            _ = session.query(orm.Routing).\
                filter(orm.Routing.channel_epoch == cha_epoch).delete()

            if session.delete(cha_epoch):
                self.logger.info(
                    'Removed referenced {0!r}.'.format(cha_epoch))

        # check for an identical orm.ChannelEpoch
        try:
            cha_epoch = session.query(orm.ChannelEpoch).\
                filter(orm.ChannelEpoch.channel == channel.code).\
                filter(orm.ChannelEpoch.locationcode ==
                       channel.location_code).\
                filter(orm.ChannelEpoch.starttime ==
                       channel.start_date.datetime).\
                filter(orm.ChannelEpoch.endtime == end_date).\
                filter(orm.ChannelEpoch.station == station).\
                filter(orm.ChannelEpoch.network == network).\
                filter(orm.ChannelEpoch.restrictedstatus ==
                       channel.restricted_status).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        if cha_epoch is None:
            cha_epoch = orm.ChannelEpoch(
                channel=channel.code,
                locationcode=channel.location_code,
                starttime=channel.start_date.datetime,
                endtime=end_date,
                station=station,
                network=network,
                restrictedstatus=restricted_status)
            self.logger.debug("Created new channel_epoch object '{}'".format(
                              cha_epoch))
            session.add(cha_epoch)
        else:
            self._update_lastseen(cha_epoch)

        return cha_epoch

    def _emerge_routing(self, session, cha_epoch, endpoint, start, end):
        """
        Factory method for a :py:class:`orm.Routing` object.
        """
        # check for available, overlapping routing(_epoch)(not identical)
        # XXX(damb): Overlapping orm.Routing regarding time constraints
        # are updated (i.e. implemented as: delete - insert).
        query = session.query(orm.Routing).\
            filter(orm.Routing.endpoint == endpoint).\
            filter(orm.Routing.channel_epoch == cha_epoch)

        # check if overlapping with ChannelEpoch already existing
        if end is None:
            query = query.\
                filter(((orm.Routing.starttime < start) &
                        ((orm.Routing.endtime == None) |  # noqa
                         (start < orm.Routing.endtime))) |
                       (orm.Routing.starttime > start))
        else:
            query = query.\
                filter(((orm.Routing.starttime < start) &
                       ((orm.Routing.endtime == None) |  # noqa
                        (start < orm.Routing.endtime))) |
                       ((orm.Routing.starttime > start) &
                        (end > orm.Routing.starttime)))

        routings = query.all()

        if routings:
            self.logger.warning('Found overlapping orm.Routing objects '
                                '{}'.format(routings))

        # delete overlapping orm.Routing entries
        for routing in routings:
            if session.delete(routing):
                self.logger.info(
                    'Removed {0!r} (matching query: {}).'.format(
                        routing, query))

        # check for an identical orm.Routing
        try:
            routing = session.query(orm.Routing).\
                filter(orm.Routing.endpoint == endpoint).\
                filter(orm.Routing.channel_epoch == cha_epoch).\
                filter(orm.Routing.starttime == start).\
                filter(orm.Routing.endtime == end).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        if routing is None:
            routing = orm.Routing(
                endpoint=endpoint,
                channel_epoch=cha_epoch,
                starttime=start,
                endtime=end)
            self.logger.debug('Created routing object {0!r}'.format(routing))
        else:
            self._update_lastseen(routing)

        return routing

    @staticmethod
    def _update_epoch(epoch, **kwargs):
        """
        Update basenode epoch properties.

        :param epoch: Epoch to be updated.
        :param kwargs: Keyword value parameters to be updated.

        Allowed parameters are:
        * :code:`restricted_status`
        """
        restricted_status = kwargs.get('restricted_status')

        if (epoch.restrictedstatus != restricted_status and
                restricted_status is not None):
            epoch.restrictedstatus = restricted_status

    @staticmethod
    def _validate_url_path(url, service):
        """
        Validate FDSN/EIDA service URLs.

        :param str url: URL to validate
        :param str service: Service identifier.
        :raises Harvester.ValidationError: If the URL path does not match the
            the service specifications.
        """
        p = urlparse(url).path

        if ('station' == service and
            p == '{}{}'.format(settings.FDSN_STATION_PATH,
                               settings.FDSN_QUERY_METHOD_TOKEN)):
            return
        elif ('dataselect' == service and
              p in ('{}{}'.format(settings.FDSN_DATASELECT_PATH,
                                  settings.FDSN_QUERY_METHOD_TOKEN),
                    '{}{}'.format(
                        settings.FDSN_DATASELECT_PATH,
                        settings.FDSN_DATASELECT_QUERYAUTH_METHOD_TOKEN))):
            return
        elif ('wfcatalog' == service and
              p == '{}{}'.format(settings.EIDA_WFCATALOG_PATH,
                                 settings.FDSN_QUERY_METHOD_TOKEN)):
            return

        raise Harvester.ValidationError(
            'Invalid path {!r} for URL {!r}.'.format(p, url))


class VNetHarvester(Harvester):
    """
    Implementation of an harvester harvesting the virtual network information
    from an EIDA node. Usually, the information is stored within the routing
    service's local configuration.

    This harvester does not rely on the EIDA routing service anymore.
    """

    class VNetHarvesterError(Harvester.HarvesterError):
        """Base error for virtual netowork harvesting ({})."""

    def harvest(self, session):

        vnet_tag = '{}vnetwork'.format(self.NS_ROUTINGXML)
        stream_tag = '{}stream'.format(self.NS_ROUTINGXML)

        self.logger.debug('Harvesting virtual networks for %s.' % self.node)

        # event driven parsing
        for event, vnet_element in etree.iterparse(self.config,
                                                   events=('end',),
                                                   tag=vnet_tag):
            if event == 'end' and len(vnet_element):

                vnet = self._emerge_streamepoch_group(session, vnet_element)

                for stream_element in vnet_element.iter(tag=stream_tag):
                    self.logger.debug("Processing stream element: {}".
                                      format(stream_element))
                    # convert attributes to dict
                    stream = Stream.from_route_attrs(
                        **dict(stream_element.attrib))
                    try:
                        stream_starttime = UTCDateTime(
                            stream_element.get('start'),
                            iso8601=True).datetime
                        endtime = stream_element.get('end')
                        # reset endtime due to 'end=""'
                        stream_endtime = (
                            UTCDateTime(endtime, iso8601=True).datetime if
                            endtime is not None and
                            endtime.strip() else None)
                    except Exception as err:
                        raise self.RoutingConfigXMLParsingError(err)

                    # deserialize to StreamEpoch object
                    stream_epoch = StreamEpoch(stream=stream,
                                               starttime=stream_starttime,
                                               endtime=stream_endtime)

                    self.logger.debug("Processing {0!r} ...".format(
                        stream_epoch))

                    sql_stream_epoch = stream_epoch.fdsnws_to_sql_wildcards()

                    # check if the stream epoch definition is valid i.e. there
                    # must be at least one matching ChannelEpoch
                    query = session.query(orm.ChannelEpoch).\
                        join(orm.Network).\
                        join(orm.Station).\
                        filter(orm.Network.name.like(
                               sql_stream_epoch.network)).\
                        filter(orm.Station.name.like(
                               sql_stream_epoch.station)).\
                        filter(orm.ChannelEpoch.locationcode.like(
                               sql_stream_epoch.location)).\
                        filter(orm.ChannelEpoch.channel.like(
                               sql_stream_epoch.channel)).\
                        filter((orm.ChannelEpoch.endtime == None) |  # noqa
                               (orm.ChannelEpoch.endtime >
                                sql_stream_epoch.starttime))

                    if sql_stream_epoch.endtime:
                        query = query.\
                            filter(orm.ChannelEpoch.starttime <
                                   sql_stream_epoch.endtime)

                    cha_epochs = query.all()
                    if not cha_epochs:
                        self.logger.warn(
                            'No ChannelEpoch matching stream epoch '
                            '{0!r}'.format(stream_epoch))
                        continue

                    for cha_epoch in cha_epochs:
                        self.logger.debug(
                            'Processing virtual network configuration for '
                            'ChannelEpoch object {0!r}.'.format(cha_epoch))
                        self._emerge_streamepoch(
                            session, cha_epoch, stream_epoch, vnet)

        # TODO(damb): Show stats for updated/inserted elements

    def _emerge_streamepoch_group(self, session, element):
        """
        Factory method for a orm.StreamEpochGroup
        """
        net_code = element.get('networkCode')
        if not net_code:
            raise self.VNetHarvesterError("Missing 'networkCode' attribute.")

        try:
            vnet = session.query(orm.StreamEpochGroup).\
                filter(orm.StreamEpochGroup.name == net_code).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        # check if network already available - else create a new one
        if vnet is None:
            vnet = orm.StreamEpochGroup(name=net_code)
            self.logger.debug(
                "Created new StreamEpochGroup object '{}'".format(vnet))
            session.add(vnet)

        else:
            self.logger.debug(
                "Updating orm.StreamEpochGroup object '{}'".format(vnet))

        return vnet

    def _emerge_streamepoch(self, session, channel_epoch, stream_epoch, vnet):
        """
        Factory method for a orm.StreamEpoch object.
        """
        # check if overlapping with a StreamEpoch already existing
        # XXX(damb)_ Overlapping orm.StreamEpoch objects regarding time
        # constraints are updated (i.e. implemented as: delete - insert).
        query = session.query(orm.StreamEpoch).\
            join(orm.Network).\
            join(orm.Station).\
            filter(orm.Network.name == channel_epoch.network.name).\
            filter(orm.Station.name == channel_epoch.station.name).\
            filter(orm.StreamEpoch.stream_epoch_group == vnet).\
            filter(orm.StreamEpoch.channel ==
                   channel_epoch.channel).\
            filter(orm.StreamEpoch.location ==
                   channel_epoch.locationcode)

        if stream_epoch.endtime is None:
            query = query.\
                filter(((orm.StreamEpoch.starttime < stream_epoch.starttime) &
                        ((orm.StreamEpoch.endtime == None) |  # noqa
                         (stream_epoch.starttime < orm.StreamEpoch.endtime))) |
                       (orm.StreamEpoch.starttime > stream_epoch.starttime))
        else:
            query = query.\
                filter(((orm.StreamEpoch.starttime < stream_epoch.starttime) &
                        ((orm.StreamEpoch.endtime == None) |  # noqa
                         (stream_epoch.starttime < orm.StreamEpoch.endtime))) |
                       ((orm.StreamEpoch.starttime > stream_epoch.starttime) &
                        (stream_epoch.endtime > orm.StreamEpoch.starttime)))

        stream_epochs = query.all()

        if stream_epochs:
            self.logger.warning('Found overlapping orm.StreamEpoch objects '
                                '{}'.format(stream_epochs))

        for se in stream_epochs:
            if session.delete(se):
                self.logger.info(
                    'Removed orm.StreamEpoch {0!r}'
                    '(matching query: {}).'.format(se, query))

        # check for an identical orm.StreamEpoch
        try:
            se = session.query(orm.StreamEpoch).\
                join(orm.Network).\
                join(orm.Station).\
                filter(orm.Network.name == channel_epoch.network.name).\
                filter(orm.Station.name == channel_epoch.station.name).\
                filter(orm.StreamEpoch.stream_epoch_group == vnet).\
                filter(orm.StreamEpoch.channel == channel_epoch.channel).\
                filter(orm.StreamEpoch.location ==
                       channel_epoch.locationcode).\
                filter(orm.StreamEpoch.starttime == stream_epoch.starttime).\
                filter(orm.StreamEpoch.endtime == stream_epoch.endtime).\
                one_or_none()
        except MultipleResultsFound as err:
            raise self.IntegrityError(err)

        if se is None:
            se = orm.StreamEpoch(
                channel=channel_epoch.channel,
                location=channel_epoch.locationcode,
                starttime=stream_epoch.starttime,
                endtime=stream_epoch.endtime,
                station=channel_epoch.station,
                network=channel_epoch.network,
                stream_epoch_group=vnet)
            self.logger.debug(
                "Created new StreamEpoch object instance {0!r}".format(se))
            session.add(se)

        else:
            self._update_lastseen(se)
            self.logger.debug(
                "Found existing StreamEpoch object instance {0!r}".format(se))

        return se


class StationLiteHarvestApp(App):
    """
    Implementation of the harvesting application for EIDA StationLite.
    """

    PROG = 'eida-stationlite-harvest'

    DB_PRAGMAS = ['PRAGMA journal_mode=WAL']

    def build_parser(self, parents=[]):
        """
        Configure a parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(prog=self.PROG,
                              description='Harvest for EIDA StationLite.',
                              parents=parents)
        # optional arguments
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + __version__)
        parser.add_argument('-P', '--pid-file', type=str,
                            metavar='PATH', dest='path_pidfile',
                            default=settings.
                            EIDA_STATIONLITE_HARVEST_PATH_PIDFILE,
                            help=('Path to PID file. '
                                  '(default: {%(default)s})'))
        parser.add_argument('--nodes-exclude', nargs='+',
                            type=str, metavar='NODES', default='',
                            choices=sorted(settings.EIDA_NODES),
                            help=('Whitespace-separated list of nodes to be '
                                  'excluded. (choices: {%(choices)s})'))
        parser.add_argument('-S', '--services', nargs='+',
                            type=str, metavar='SERVICES',
                            default=sorted(
                                settings.EIDA_STATIONLITE_HARVEST_SERVICES),
                            choices=sorted(
                                settings.EIDA_STATIONLITE_HARVEST_SERVICES),
                            help=('Whitespace-separated list of services to '
                                  'be cached. (choices: {%(choices)s}) '
                                  '(default: {%(default)s})'))
        parser.add_argument('--no-routes', action='store_true', default=False,
                            dest='no_routes',
                            help=('Do not harvest <route></route> '
                                  'information.'))
        parser.add_argument('--no-vnetworks', action='store_true',
                            default=False, dest='no_vnetworks',
                            help=('Do not harvest <vnetwork></vnetwork> '
                                  'information.'))
        parser.add_argument('-t', '--truncate', type=UTCDateTime,
                            metavar='TIMESTAMP',
                            help=('Truncate DB (delete outdated information). '
                                  'The TIMESTAMP format must agree with '
                                  'formats supported by obspy.UTCDateTime.'))

        # positional arguments
        parser.add_argument('db_engine', type=db_engine, metavar='URL',
                            help=('DB URL indicating the database dialect and '
                                  'connection arguments'))
        return parser

    def run(self):
        """
        Run application.
        """
        # configure SQLAlchemy logging
        # log_level = self.logger.getEffectiveLevel()
        # logging.getLogger('sqlalchemy.engine').setLevel(log_level)

        exit_code = ExitCodes.EXIT_SUCCESS

        try:
            self.logger.info('{}: Version v{}'.format(self.PROG, __version__))
            self.logger.debug('Configuration: {!r}'.format(self.args))

            pid_lock = InterProcessLock(self.args.path_pidfile)
            pid_lock_gotten = pid_lock.acquire(blocking=False)
            if not pid_lock_gotten:
                raise AlreadyHarvesting(self.args.path_pidfile)
            self.logger.debug('Aquired PID lock {0!r}'.format(
                              self.args.path_pidfile))

            if (self.args.no_routes and self.args.no_vnetworks and not
                    self.args.truncate):
                raise NothingToDo()

            harvesting = not (self.args.no_routes and self.args.no_vnetworks)

            Session = db.ScopedSession()
            Session.configure(bind=self.args.db_engine)

            if self.args.db_engine.name == 'sqlite':
                db.configure_sqlite(self.DB_PRAGMAS)

            # TODO(damb): Implement multithreaded harvesting using a thread
            # pool.
            try:
                if harvesting:
                    self.logger.info('Start harvesting.')

                if not self.args.no_routes:
                    self._harvest_routes(Session)
                else:
                    self.logger.warn(
                        'Disabled processing <route></route> information.')

                if not self.args.no_vnetworks:
                    self._harvest_vnetworks(Session)
                else:
                    self.logger.warn(
                        'Disabled processing <vnetwork></vnetwork> '
                        'information.')

                if harvesting:
                    self.logger.info('Finished harvesting successfully.')

                if self.args.truncate:
                    self.logger.warning('Removing outdated data.')
                    session = Session()
                    with db.session_guard(session) as _session:
                        num_removed_rows = db.clean(_session,
                                                    self.args.truncate)
                        self.logger.info(
                            'Number of rows removed: {}'.format(
                                num_removed_rows))

            except OperationalError as err:
                raise db.StationLiteDBEngineError(err)

        # TODO(damb): signal handling
        except Error as err:
            self.logger.error(err)
            exit_code = ExitCodes.EXIT_ERROR
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.critical('Local Exception: %s' % err)
            self.logger.critical('Traceback information: ' +
                                 repr(traceback.format_exception(
                                     exc_type, exc_value, exc_traceback)))
            exit_code = ExitCodes.EXIT_ERROR
        finally:
            try:
                if pid_lock_gotten:
                    pid_lock.release()
            except NameError:
                pass

        sys.exit(exit_code)

    def _harvest_routes(self, Session):
        """
        Harvest the EIDA node's <route></route> information.

        :param :cls:`sqlalchemy.orm.session.Session` Session: A configured
        Session class reference.
        """
        for node_name, node_par in node_generator(
                exclude=self.args.nodes_exclude):
            url_routing_config = (
                node_par['services']['eida']['routing']['server'] +
                node_par['services']['eida']['routing']
                        ['uri_path_config'])

            self.logger.info(
                'Processing routes from EIDA node %r.' % node_name)
            try:
                h = RoutingHarvester(node_name, url_routing_config,
                                     services=self.args.services)

                session = Session()
                # XXX(damb): Maintain sessions within the scope of a
                # harvesting process.
                with db.session_guard(session) as _session:
                    h.harvest(_session)

            except RequestsError as err:
                self.logger.warning(str(err))

    def _harvest_vnetworks(self, Session):
        """
        Harvest the EIDA node's <vnetwork></vnetwork> information.

        :param :cls:`sqlalchemy.orm.session.Session` Session: A configured
        Session class reference.
        """
        for node_name, node_par in node_generator(
                exclude=self.args.nodes_exclude):
            url_vnet_config = (
                node_par['services']['eida']['routing']['server'] +
                node_par['services']['eida']['routing']
                        ['uri_path_config_vnet'])

            self.logger.info(
                'Processing vnetworks from EIDA node %r.' % node_name)
            try:
                # harvest virtual network configuration
                h = VNetHarvester(node_name, url_vnet_config)
                session = Session()
                # XXX(damb): Maintain sessions within the scope of a
                # harvesting process.
                with db.session_guard(session) as _session:
                    h.harvest(_session)

            except RequestsError as err:
                self.logger.warning(str(err))


# ----------------------------------------------------------------------------
def main():
    """
    main function for EIDA stationlite harvesting
    """

    app = StationLiteHarvestApp(log_id='STL')

    try:
        app.configure(
            settings.PATH_EIDANGWS_CONF,
            config_section=settings.EIDA_STATIONLITE_HARVEST_CONFIG_SECTION,
            positional_required_args=['db_engine'],
            capture_warnings=False)
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(ExitCodes.EXIT_ERROR)

    app.run()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()
