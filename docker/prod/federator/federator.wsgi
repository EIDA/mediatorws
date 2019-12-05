# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <federator.wsgi>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/11/27        V0.1    Daniel Armbruster
# =============================================================================
"""
federator webservice wsgi file

see also:
  - http://flask.pocoo.org/docs/0.12/deploying/mod_wsgi/
"""

import sys

# use a virtual environment
activate_this = '/var/www/federator/venv3/bin/activate_this.py'

with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# NOTE: In case you would like to place the eidangws_conf file on a custom
# location comment out the two lines bellow. Also, adjust the path to the
# configuration file.
#import eidangservices.settings as settings
#settings.PATH_EIDANGWS_CONF = '/path/to/your/custom/eidangws_config'

from eidangservices.federator.server.app import main
application = main()

# ---- END OF <federator.wsgi> ----
