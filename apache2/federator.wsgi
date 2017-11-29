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
activate_this = '/var/www/madiatorws/venv/bin/activate_this.py'

try:
  # Python 2
  execfile(activate_this, dict(__file__=activate_this))
except:
  # Python 3
  with open(activate_this) as file_:
      exec(file_.read(), dict(__file__=activate_this))

from eidangservice.federator.server.app import main
application = main()

# ---- END OF <federator.wsgi> ----
