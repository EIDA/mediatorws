# -*- coding: utf-8 -*-
"""
This file is part of the EIDA mediator/federator webservices.

"""

import os


EIDA_NODES = {
    'gfz': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://geofon.gfz-potsdam.de',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://geofon.gfz-potsdam.de',
                    'static_file': ''
                    }
                }
            }
        },
    'odc': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://www.orfeus-eu.org',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://www.orfeus-eu.org',
                    'static_file': ''
                    }
                }
            }
        },
    'eth': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://eida.ethz.ch',
                'station': True,
                'dataselect': True,
                'event': True}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.ethz.ch',
                    'static_file': ''
                    }
                }
            }
        },
    'resif': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://ws.resif.fr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': False,
                    'static_file': 'http://ws.resif.fr/eida_routing.xml'
                    }
                }
            }
        },
    'ingv': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://webservices.rm.ingv.it',
                'station': True,
                'dataselect': True,
                'event': True}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': ' http://eida.ingv.it',
                    'static_file': ''
                    }
                }
            }
        },
    'bgr': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://eida.bgr.de',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.bgr.de',
                    'static_file': ''
                    }
                }
            }
        },
    'lmu': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://erde.geophysik.uni-muenchen.de',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://erde.geophysik.uni-muenchen.de',
                    'static_file': ''
                    }
                }
            }
        },
    'ipgp': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://eida.ipgp.fr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eidaws.ipgp.fr',
                    'static_file': ''
                    }
                }
            }
        },
    'niep': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://eida-sc3.infp.ro',
                'station': True,
                'dataselect': True,
                'event': True}, 
            'eida': {
                'routing': {
                    'service': False,
                    'static_file': 'http://eida-routing.infp.ro/eidaws/routing/1/routing.xml'
                    }
                }
            }
        },
    'koeri': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://eida-service.koeri.boun.edu.tr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.koeri.boun.edu.tr',
                    'static_file': ''
                    }
                }
            }
        },
    'noa': {
        'name': '',
        'services': {
            'fdsn': {
                'server': 'http://eida.gein.noa.gr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.gein.noa.gr',
                    'static_file': ''
                    }
                }
            }
        },
    }

DEFAULT_ROUTING_SERVICE = 'gfz'
DEFAULT_SERVER_PORT = 5000
DEFAULT_ROUTING_TIMEOUT = 600
DEFAULT_ROUTING_RETRIES = 10
DEFAULT_ROUTING_RETRY_WAIT = 60
DEFAULT_ROUTING_NUM_DOWNLOAD_THREADS = 5

SERVER_NAME = 'EIDA Federator (alpha)'
VERSION = '0.9.1'
SHARE_DIR = 'share'


FDSN_STATION_PATH = '/fdsnws/station/1/'
FDSN_DATASELECT_PATH = '/fdsnws/dataselect/1/'
FDSN_WFCATALOG_PATH = '/fdsnws/wfcatalog/1/'
FDSN_EVENT_PATH = '/fdsnws/event/1/'

EIDA_ROUTING_PATH = '/eidaws/routing/1/'

FDSN_QUERY_METHOD_TOKEN = 'query'
FDSN_VERSION_METHOD_TOKEN = 'version'
FDSN_WADL_METHOD_TOKEN = 'application.wadl'
FDSN_DATASELECT_QUERYAUTH_METHOD_TOKEN = 'queryauth'

FDSN_DATASELECT_VERSION = '1.1.0'
FDSN_STATION_VERSION = '1.1.0'
FDSN_WFCATALOG_VERSION = '1.0.0'

FDSNWS_QUERY_VALUE_SEPARATOR_CHAR = '='
FDSNWS_QUERY_LIST_SEPARATOR_CHAR = ','

FDSN_WADL_DIR = SHARE_DIR
FDSN_DATASELECT_WADL_FILENAME = 'dataselect.wadl'
FDSN_STATION_WADL_FILENAME = 'station.wadl'
FDSN_WFCATALOG_WADL_FILENAME = 'wfcatalog.wadl'

MIMETYPE_MSEED = 'application/vnd.fdsn.mseed'
MIMETYPE_TEXT = 'text/plain' 
MIMETYPE_JSON = 'application/json'
MIMETYPE_XML = 'application/xml'

DATASELECT_MIMETYPE = MIMETYPE_MSEED
STATION_MIMETYPE_XML = MIMETYPE_XML
STATION_MIMETYPE_TEXT = MIMETYPE_TEXT
WFCATALOG_MIMETYPE = MIMETYPE_JSON
VERSION_MIMETYPE = MIMETYPE_TEXT
WADL_MIMETYPE = MIMETYPE_XML


STATION_RESPONSE_TEXT_HEADER = \
    '#Network|Station|Latitude|Longitude|Elevation|SiteName|StartTime|EndTime'

STATIONXML_RESOURCE_METADATA_ELEMENTS = (
    '{http://www.fdsn.org/xml/station/1}Source', 
    '{http://www.fdsn.org/xml/station/1}Created',
    '{http://www.fdsn.org/xml/station/1}Sender', 
    '{http://www.fdsn.org/xml/station/1}Module', 
    '{http://www.fdsn.org/xml/station/1}ModuleURI')
STATIONXML_NETWORK_ELEMENT = '{http://www.fdsn.org/xml/station/1}Network'
STATIONXML_STATION_ELEMENT = '{http://www.fdsn.org/xml/station/1}Station'
STATIONXML_LATITUDE_ELEMENT = '{http://www.fdsn.org/xml/station/1}Latitude'
STATIONXML_LONGITUDE_ELEMENT = '{http://www.fdsn.org/xml/station/1}Longitude'


FDSN_DEFAULT_NO_CONTENT_ERROR_CODE = 204

FDSN_SERVICE_DOCUMENTATION_URI = 'http://www.fdsn.org/webservices/'

FDSNWS_GEOMETRY_PARAMS_LONG = (
    'minlatitude', 'maxlatitude', 'minlongitude', 'maxlongitude')
FDSNWS_GEOMETRY_PARAMS_SHORT = ('minlat', 'maxlat', 'minlon', 'maxlon')

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_SHARE = os.path.join(APP_ROOT, SHARE_DIR)
