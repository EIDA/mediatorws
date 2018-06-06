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
                         pre_load, ValidationError)

from eidangservices.utils.schema import (FDSNWSBool, Latitude, Longitude,
                                         NoData)

# ----------------------------------------------------------------------------
class StationLiteSchema(Schema):
    """
    Stationlite webservice schema definition.

    The parameters defined correspond to the definition
    `https://www.orfeus-eu.org/data/eida/webservices/routing/`
    """
    format = fields.Str(
        # NOTE(damb): formats different from 'post' are not implemented yet.
        # missing='xml'
        missing='post',
        #validate=validate.OneOf(['xml', 'json', 'get', 'post'])
        validate=validate.OneOf(['post', 'get']))
    service = fields.Str(
        missing='dataselect',
        validate=validate.OneOf(['dataselect', 'station', 'wfcatalog']))

    nodata = NoData()
    alternative = FDSNWSBool(missing='false')

    # geographic (rectangular spatial) options
    # XXX(damb): Default values are defined and assigned within merge_keys ()
    minlatitude = Latitude()
    minlat = Latitude(load_only=True)
    maxlatitude = Latitude()
    maxlat = Latitude(load_only=True)
    minlongitude = Longitude()
    minlon = Latitude(load_only=True)
    maxlongitude = Longitude()
    maxlon = Latitude(load_only=True)

    @pre_load
    def merge_keys(self, data):
        """
        Merge both alternative field parameter values and assign default
        values.

        .. note::
            The default webargs parser does not provide this feature by
            default such that `load_from` fields parameters are exclusively
            parsed.

        :param dict data: data
        """
        _mappings = [
            ('minlat', 'minlatitude', -90.),
            ('maxlat', 'maxlatitude', 90.),
            ('minlon', 'minlongitude', -180.),
            ('maxlon', 'maxlongitude', 180.)]

        for alt_key, key, missing in _mappings:
            if alt_key in data and key in data:
                data.pop(alt_key)
            elif alt_key in data and key not in data:
                data[key] = data[alt_key]
                data.pop(alt_key)
            else:
                data[key] = missing

    # merge_keys ()

    @validates_schema
    def validate_spatial(self, data):
        if (data['minlatitude'] >= data['maxlatitude'] or
                data['minlongitude'] >= data['maxlongitude']):
            raise ValidationError('Bad Request: Invalid spatial constraints.')

    class Meta:
        strict = True

# class StationLiteSchema

# ---- END OF <schema.py> ----
