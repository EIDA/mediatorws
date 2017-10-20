# -*- coding: utf-8 -*-
"""

EIDA Mediator settings.

This file is part of the EIDA mediator/federator webservices.

"""

import os


# NOTE: arclink servers/ports are from
# http://eida.gfz-potsdam.de/eida/status/master_table.php
# (last accessed 2017-08-17)
EIDA_NODES = {
    'gfz': {
        'name': 'GFZ',
        'services': {
            'arclink': {
                'server': 'eida.gfz-potsdam.de',
                'port': 18002},
            'fdsn': {
                'server': 'http://geofon.gfz-potsdam.de',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://geofon.gfz-potsdam.de',
                    'static_file': ''},
                'wfcatalog': {
                    'url': 'http://geofon.gfz-potsdam.de/eidaws/wfcatalog/"\
                        "alpha/query',
                    'server': 'http://geofon.gfz-potsdam.de'}
                }
            },
        'testquerysncls': {
            'network': 'CZ',
            'station': 'VRAC',
            'location': '--',
            'channel': 'HH?',
            'startdate': '2012-06-01T00:00:00'}
        },
        
    'odc': {
        'name': 'Orfeus Data Center',
        'services': {
            'arclink': {
                # was (until 2017-09-04):
                # bhlsa02.knmi.nl
                'server': 'eida.orfeus-eu.org',
                'port': 18002},
            'fdsn': {
                'server': 'http://www.orfeus-eu.org',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://www.orfeus-eu.org',
                    'static_file': ''},
                'wfcatalog': {
                    'url': 'http://www.orfeus-eu.org/eidaws/wfcatalog/1/query',
                    'server': 'http://www.orfeus-eu.org'}
                }
            },
        'testquerysncls': {
            'network': 'NL',
            'station': 'OPLO',
            'location': '01',
            'channel': 'BH?',
            'startdate': '2009-11-01T00:00:00'}
        },
        
    'eth': {
        'name': 'Swiss Seismological Service',
        'services': {
            'arclink': {
                'server': 'eida.ethz.ch',
                'port': 18001},
            'fdsn': {
                'server': 'http://eida.ethz.ch',
                'station': True,
                'dataselect': True,
                'event': True}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.ethz.ch',
                    'static_file': ''},
                'wfcatalog': {
                    'url': '',
                    'server': ''}
                }
            },
        'testquerysncls': {
            'network': 'CH',
            'station': 'DAVOX',
            'location': '--',
            'channel': 'HH?',
            'startdate': '2002-08-01T00:00:00'}
        },
        
    'resif': {
        'name': 'RESIF',
        'services': {
            'arclink': {
                'server': 'eida.resif.fr',
                'port': 18001},
            'fdsn': {
                'server': 'http://ws.resif.fr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': False,
                    'static_file': 'http://ws.resif.fr/eida_routing.xml'},
                'wfcatalog': {
                    'url': 'http://ws.resif.fr/eidaws/wfcatalog/1/query',
                    'server': 'http://ws.resif.fr'}
                }
            },
        'testquerysncls': {
            'network': 'FR',
            'station': 'SJAF',
            'location': '00',
            'channel': 'HH?',
            'startdate': '2007-02-01T00:00:00'}
        },
        
    'ingv': {
        'name': 'Italian Seismic Data Center',
        'services': {
            'arclink': {
                'server': 'eida.ingv.it',
                'port': 18002},
            'fdsn': {
                'server': 'http://webservices.rm.ingv.it',
                'station': True,
                'dataselect': True,
                'event': True}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': ' http://eida.ingv.it',
                    'static_file': ''},
                'wfcatalog': {
                    'url': 'http://catalog.data.ingv.it/wfcatalog/1/query',
                    'server': 'http://catalog.data.ingv.it'}
                }
            },
        'testquerysncls': {
            'network': 'IV',
            'station': 'BOB',
            'location': '--',
            'channel': 'HHZ',
            'startdate': '2003-08-01T00:00:00'}
        },
        
    'bgr': {
        'name': 'BGR Hannover',
        'services': {
            'arclink': {
                'server': 'eida.bgr.de',
                'port': 18001},
            'fdsn': {
                'server': 'http://eida.bgr.de',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.bgr.de',
                    'static_file': ''},
                'wfcatalog': {
                    'url': 'http://eida.bgr.de/eidaws/wfcatalog/alpha/query',
                    'server': 'http://eida.bgr.de'}
                }
            },
        'testquerysncls': {
            'network': 'GR',
            'station': 'BFO',
            'location': '--',
            'channel': 'HH?',
            'startdate': '1991-01-01T00:00:00'}
        },
        
    'lmu': {
        'name': 'BayernNetz',
        'services': {
            'arclink': {
                'server': 'erde.geophysik.uni-muenchen.de',
                'port': 18001},
            'fdsn': {
                'server': 'http://erde.geophysik.uni-muenchen.de',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://erde.geophysik.uni-muenchen.de',
                    'static_file': ''},
                'wfcatalog': {
                    'url': 'http://erde.geophysik.uni-muenchen.de/eidaws/"\
                        "wfcatalog/1/query',
                    'server': 'http://erde.geophysik.uni-muenchen.de'}
                }
            },
        'testquerysncls': {
            'network': 'BW',
            'station': 'ZUGS',
            'location': '--',
            'channel': 'EHZ',
            'startdate': '2006-03-01T00:00:00'}
        },
        
    'ipgp': {
        'name': 'IPGP Data Center',
        'services': {
            'arclink': {
                'server': 'eida.ipgp.fr',
                'port': 18001},
            'fdsn': {
                'server': 'http://eida.ipgp.fr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eidaws.ipgp.fr',
                    'static_file': ''},
                'wfcatalog': {
                    'url': '',
                    'server': ''}
                }
            },
        'testquerysncls': {
            'network': 'MQ',
            'station': 'LPM',
            'location': '00',
            'channel': 'HH?',
            'startdate': '2013-05-01T00:00:00'}
        },
        
    'niep': {
        'name': 'NIEP',
        'services': {
            'arclink': {
                'server': 'eida-sc3.infp.ro',
                'port': 18001},
            'fdsn': {
                'server': 'http://eida-sc3.infp.ro',
                'station': True,
                'dataselect': True,
                'event': True}, 
            'eida': {
                'routing': {
                    'service': False,
                    'static_file': 'http://eida-routing.infp.ro/eidaws/"\
                        "routing/1/routing.xml'},
                'wfcatalog': {
                    'url': '',
                    'server': ''}
                }
            },
        'testquerysncls': {
            'network': 'RO',
            'station': 'MLR',
            'location': '--',
            'channel': 'HH?',
            'startdate': '2001-04-01T00:00:00'}
        },
        
    'koeri': {
        'name': 'Bogazici University Kandilli Observatory and ERI',
        'services': {
            'arclink': {
                'server': 'eida-service.koeri.boun.edu.tr',
                'port': 18001},
            'fdsn': {
                'server': 'http://eida-service.koeri.boun.edu.tr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.koeri.boun.edu.tr',
                    'static_file': ''},
                'wfcatalog': {
                    'url': '',
                    'server': ''}
                }
            },
        'testquerysncls': {
            'network': 'KO',
            'station': 'ELL',
            'location': '--',
            'channel': 'BH?',
            'startdate': '2006-10-01T00:00:00'}
        },
        
    'noa': {
        'name': 'National Observatory of Athens, Institute of Geodynamics',
        'services': {
            'arclink': {
                'server': 'eida.gein.noa.gr',
                'port': 18001},
            'fdsn': {
                'server': 'http://eida.gein.noa.gr',
                'station': True,
                'dataselect': True,
                'event': False}, 
            'eida': {
                'routing': {
                    'service': True,
                    'server': 'http://eida.gein.noa.gr',
                    'static_file': ''},
                'wfcatalog': {
                    'url': '',
                    'server': ''}
                }
            },
        'testquerysncls': {
            'network': 'HL',
            'station': 'IDI',
            'location': '--',
            'channel': 'HH?',
            'startdate': '2011-01-01T00:00:00'}
        }
    }


FDSN_EVENT_SERVICES = {
    'eth': {
        'server': 'http://arclink.ethz.ch'},
    'ingv': {
        'server': 'http://webservices.rm.ingv.it'},
    'niep': {
        'server': 'http://eida-sc3.infp.ro'},
    'iris': {
        'server': 'http://service.iris.edu'},
    'usgs': {
        'server': 'https://earthquake.usgs.gov'},
    'ncedc': {
        'server': 'http://service.ncedc.org'},
    'scedc': {
        'server': 'http://service.scedc.caltech.edu'},
    'isc': {
        'server': 'http://www.isc.ac.uk'}
}

DEFAULT_ROUTING_SERVICE = 'gfz'
DEFAULT_EVENT_SERVICE = 'usgs'

SERVER_NAME = 'EIDA Mediator (alpha)'
VERSION = '0.9.1'
SHARE_DIR = 'share'


FDSN_STATION_PATH = '/fdsnws/station/1/'
FDSN_DATASELECT_PATH = '/fdsnws/dataselect/1/'
FDSN_EVENT_PATH = '/fdsnws/event/1/'

EIDA_ROUTING_PATH = '/eidaws/routing/1/'
EIDA_STATIONLITE_PATH = '/routing/'
EIDA_WILDCARDS_PATH = '/wildcardresolver/'

EIDA_MEDIATOR_PATH = '/eidaws/mediator/'

EIDA_MEDIATOR_DQ_PATH = '/eidaws/mediator/dq/'
EIDA_MEDIATOR_RQ_PATH = '/eidaws/mediator/rq/'
EIDA_MEDIATOR_AQ_PATH = '/eidaws/mediator/aq/'

MEDIATOR_QUERY_METHOD_TOKEN = 'query'
MEDIATOR_VERSION_METHOD_TOKEN = 'version'

EIDA_FEDERATOR_BASE_URL = 'http://mediator-devel.ethz.ch'
EIDA_FEDERATOR_PORT = 80

EIDA_FEDERATOR_SERVICES = ('dataselect', 'station')

# -----------


FDSN_QUERY_METHOD_TOKEN = 'query'
FDSN_VERSION_METHOD_TOKEN = 'version'
FDSN_WADL_METHOD_TOKEN = 'application.wadl'
FDSN_DATASELECT_QUERYAUTH_METHOD_TOKEN = 'queryauth'

FDSN_DATASELECT_VERSION = '1.1.0'
FDSN_STATION_VERSION = '1.1.0'

FDSN_WADL_DIR = SHARE_DIR
FDSN_DATASELECT_WADL_FILENAME = 'dataselect.wadl'
FDSN_STATION_WADL_FILENAME = 'station.wadl'

DATASELECT_MIMETYPE = 'application/vnd.fdsn.mseed'
STATION_MIMETYPE_XML = 'application/xml'
STATION_MIMETYPE_TEXT = 'text/plain'
VERSION_MIMETYPE = 'text/plain'
WADL_MIMETYPE = 'application/xml'

GENERAL_TEXT_MIMETYPE = 'text/plain'
GENERAL_XML_MIMETYPE = 'application/xml'


FDSN_DEFAULT_NO_CONTENT_ERROR_CODE = 204

FDSN_SERVICE_DOCUMENTATION_URI = 'http://www.fdsn.org/webservices/'


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_SHARE = os.path.join(APP_ROOT, SHARE_DIR)
