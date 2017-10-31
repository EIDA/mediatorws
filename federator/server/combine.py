# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <combine.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/10/20        V0.1    Daniel Armbruster; most of the code is based on
#                           https://github.com/GEOFON/fdsnws_scripts/blob/ \
#                               master/fdsnws_fetch.py
# =============================================================================
"""
Federator response combination facilities
"""

import datetime
import json
import logging

from federator.settings import STATION_RESPONSE_TEXT_HEADER, \
    STATIONXML_RESOURCE_METADATA_ELEMENTS, STATIONXML_NETWORK_ELEMENT, \
    FDSNWS_GEOMETRY_PARAMS_SHORT, FDSNWS_GEOMETRY_PARAMS_LONG

try:
    # Python 3.2 and earlier
    from xml.etree import cElementTree as ET  # NOQA
except ImportError:
    from xml.etree import ElementTree as ET  # NOQA


def get_geometry_par_type(qp):

    par_short_count = 0
    par_long_count = 0
    
    for (p, v) in qp.iteritems():
        
        if p in FDSNWS_GEOMETRY_PARAMS_SHORT:
            try:
                _ = float(v)
                par_short_count += 1
            except Exception:
                continue
            
        elif p in FDSNWS_GEOMETRY_PARAMS_LONG:
            try:
                _ = float(v)
                par_long_count += 1
            except Exception:
                continue
            
    if par_long_count == len(FDSNWS_GEOMETRY_PARAMS_LONG):
        par_type = 'long'
    elif par_short_count == len(FDSNWS_GEOMETRY_PARAMS_SHORT):
        par_type = 'short'
    else:
        par_type = None
    
    return par_type

# get_geometry_par_type ()


def remove_stations_outside_box(net, qp, geometry_par_type):
                    
    stations = net.findall(STATIONXML_STATION_ELEMENT)
                    
    for st in stations:
        lat = float(st.find(STATIONXML_LATITUDE_ELEMENT).text)
        lon = float(st.find(STATIONXML_LONGITUDE_ELEMENT).text)
                        
        if not is_within_box(lat, lon, qp, geometry_par_type):
            net.remove(st)

# remove_stations_outside_box ()

# -----------------------------------------------------------------------------
class Combiner(object):
    """
    Abstract interface for combiners
    """

    LOGGER = 'federator.combiner'

    def __init__(self):
        self.logger = logging.getLogger(self.LOGGER)

    def combine(self, text):
        raise NotImplementedError

    def dump(self, fd):
        raise NotImplementedError

# class Combiner

class JSONCombiner(Combiner):
    def __init__(self):
        super(JSONCombiner, self).__init__()
        self.__data = []

    def combine(self, text):
        json_data = json.loads(text)
        self.__data.extend(json_data)

    def dump(self, fd, **kwargs):
        if self.__data:
            json.dump(self.__data, fd, **kwargs)

# class JSONCombiner


class TextCombiner(Combiner):
    def __init__(self):
        super(TextCombiner, self).__init__()
        self.__text = ''

    def combine(self, text):
        if self.__text:
            self.__text = ''.join((self.__text, text))
        else:
            self.__text = '\n'.join((STATION_RESPONSE_TEXT_HEADER, text))

    def dump(self, fd):
        if self.__text:
            fd.write(self.__text)
            
# class TextCombiner


class XMLCombiner(Combiner):
    def __init__(self, qp):
        super(XMLCombiner, self).__init__()
        self.__et = None
        self.__qp = qp
        self.__geometry_par_type = get_geometry_par_type(qp)

    def __combine_element(self, one, other):
        mapping = {}

        for el in one:
            try:
                eid = (el.tag, el.attrib['code'], el.attrib['start'])
                mapping[eid] = el

            except KeyError:
                pass

        for el in other:
            
            # skip Sender, Source, Module, ModuleURI, Created elements of 
            # subsequent trees
            if el.tag in STATIONXML_RESOURCE_METADATA_ELEMENTS:
                continue
            
            # station coords: check lat-lon box, remove stations outside
            if self.__geometry_par_type is not None and \
                el.tag == STATIONXML_NETWORK_ELEMENT:

                remove_stations_outside_box(
                    el, self.__qp, self.__geometry_par_type)
            
            try:
                eid = (el.tag, el.attrib['code'], el.attrib['start'])

                try:
                    self.__combine_element(mapping[eid], el)

                except KeyError:
                    mapping[eid] = el
                    one.append(el)

            except KeyError:
                one.append(el)

    # FIXME(damb): correct iface such that it is matching with its parent class
    # Combiner
    def combine(self, fd):
        if self.__et:
            self.__combine_element(self.__et.getroot(), ET.parse(fd).getroot())

        else:
            self.__et = ET.parse(fd)
            root = self.__et.getroot()
            
            # Note: this assumes well-formed StationXML
            # first StationXML tree: modify Source, Created
            try:
                source = root.find(STATIONXML_RESOURCE_METADATA_ELEMENTS[0])
                source.text = 'EIDA'
            except Exception:
                pass
            
            try:
                created = root.find(STATIONXML_RESOURCE_METADATA_ELEMENTS[1])
                created.text = datetime.datetime.utcnow().strftime(
                    '%Y-%m-%dT%H:%M:%S')
            except Exception:
                pass
            
            # remove Sender, Module, ModuleURI
            for tag in STATIONXML_RESOURCE_METADATA_ELEMENTS[2:]:
                el = root.find(tag)
                if el is not None:
                    root.remove(el)
                    
            # station coords: check lat-lon box, remove stations outside
            if self.__geometry_par_type is not None:
                
                networks = root.findall(STATIONXML_NETWORK_ELEMENT)
                for net in networks:
                    remove_stations_outside_box(
                        net, self.__qp, self.__geometry_par_type)
           

    def dump(self, fd):
        if self.__et:
            self.__et.write(fd)

# class XMLCombiner

# ---- END OF <combine.py> ----
