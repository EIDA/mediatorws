# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <__init__.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices.
#
# EIDA NG webservices is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EIDA NG webservices is distributed in the hope that it will be useful,
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
#
# REVISION AND CHANGES
# 2018/03/14        V0.1    Daniel Armbruster
# =============================================================================
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_dict={}):
    """
    Factory function for Flask application.

    :param :cls:`flask.Config config` flask configuration object
    """
    app = Flask(__name__)
    app.config.update(config_dict)

    db.init_app(app)
    return app

# create_app ()

# ---- END OF <__init__.py> ----
