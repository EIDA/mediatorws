# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <stationlite.wsgi>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2018/03/22        V0.1    Daniel Armbruster
# =============================================================================
"""
EIDA StationLite webservice wsgi file

see also:
  - http://flask.pocoo.org/docs/0.12/deploying/mod_wsgi/
"""

import sys

"""
# use a virtual environment
activate_this = '/var/www/stationlite/venv/bin/activate_this.py'

try:
  # Python 2
  execfile(activate_this, dict(__file__=activate_this))
except:
  # Python 3
  with open(activate_this) as file_:
      exec(file_.read(), dict(__file__=activate_this))
"""
# NOTE: In case you would like to place the eidangws_conf file on a custom
# location comment out the two lines bellow. Also, adjust the path to the
# configuration file.
#import eidangservices.settings as settings
#settings.PATH_EIDANGWS_CONF = '/path/to/your/custom/eidangws_config'

from eidangservices.stationlite.server.app import main
application = main()

# ---- END OF <stationlite.wsgi> ----
