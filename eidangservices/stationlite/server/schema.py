# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <schema.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-stationlite).
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
#
# REVISION AND CHANGES
# 2017/12/13        V0.1    Daniel Armbruster
# =============================================================================
"""
Stationlite schema definitions
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

from marshmallow import (Schema, fields, validate, validates_schema,
                         ValidationError)

from eidangservices.utils.schema import FDSNWSBool, Latitude, Longitude

# ----------------------------------------------------------------------------
class StationLiteSchema(Schema):
    """
    Stationlite webservice schema definition.

    The parameters defined correspond to the definition
    `https://www.orfeus-eu.org/data/eida/webservices/routing/`
    """
    minlatitude = Latitude(load_from='minlat', missing=-90.)
    maxlatitude = Latitude(load_from='maxlat', missing=90.)
    minlongitude = Longitude(load_from='minlon', missing=-180.)
    maxlongitude = Longitude(load_from='maxlon', missing=180.)
    format = fields.Str(
        # NOTE(damb): formats different from 'post' are not implemented yet.
        # missing='xml'
        missing='post',
        #validate=validate.OneOf(['xml', 'json', 'get', 'post'])
        validate=validate.OneOf(['post']))
    service = fields.Str(
        missing='dataselect',
        validate=validate.OneOf(['dataselect', 'station', 'wfcatalog']))
    alternative = FDSNWSBool(missing='false')

    @validates_schema
    def validate_spatial(self, data):
        if (data['minlatitude'] >= data['maxlatitude'] or
                data['minlongitude'] >= data['maxlongitude']):
            raise ValidationError('Bad Request: Invalid spatial constraints.')

    class Meta:
        strict = True

# class StationLiteSchema

# ---- END OF <schema.py> ----
