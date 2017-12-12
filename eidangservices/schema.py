# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <schema.py>
# -----------------------------------------------------------------------------
#
# This file is part of EIDA NG webservices (eida-federator).
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
# 2017/12/12        V0.1    Daniel Armbruster
# =============================================================================
"""
General marshmallow schema definitions for EIDA NG webservices.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import *

import datetime

from marshmallow import (Schema, fields, validate, ValidationError,
                         post_load, post_dump, validates_schema)

from eidangservices import settings, utils


validate_net_sta_cha = validate.Regexp(r'[A-Z0-9_*?]*$')

# -----------------------------------------------------------------------------
class FDSNWSDateTime(fields.DateTime):
    """
    Class extends marshmallow standard DateTime with a *FDSNWS datetime*
    format.

    The *FDSNWS DateTime* format is described in the `FDSN Web Service
    Specifications
    <http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.1.pdf>`_.
    """

    DATEFORMAT_SERIALIZATION_FUNCS = \
        fields.DateTime.DATEFORMAT_SERIALIZATION_FUNCS.copy()

    DATEFORMAT_DESERIALIZATION_FUNCS = \
        fields.DateTime.DATEFORMAT_DESERIALIZATION_FUNCS.copy()

    DATEFORMAT_SERIALIZATION_FUNCS['fdsnws'] = utils.fdsnws_isoformat
    DATEFORMAT_DESERIALIZATION_FUNCS['fdsnws'] = utils.from_fdsnws_datetime

# class FDSNWSDateTime

# -----------------------------------------------------------------------------
class SNCLSchema(Schema):
    """
    A SNCL Schema. The name *SNCL* refers to the *FDSNWS* POST format. A SNCL
    is a line consisting of:

        network station location channel starttime endtime
    """
    network = fields.Str(load_from='net', missing = '*',
                         validate=validate_net_sta_cha)
    station = fields.Str(load_from='sta', missing = '*',
                         validate=validate_net_sta_cha)
    location = fields.Str(load_from='loc', missing = '*',
                          validate=validate.Regexp(r'[A-Z0-9_*?]*$|--|\s\s'))
    channel = fields.Str(load_from='cha', missing = '*',
                         validate=validate_net_sta_cha)
    starttime = FDSNWSDateTime(format='fdsnws', load_from='start')
    endtime = FDSNWSDateTime(format='fdsnws', load_from='end')

    @post_load
    def make_sncl(self, data):
        return utils.SNCL(**data)

    @post_dump
    def skip_empty_datetimes(self, data):
        if (self.context.get('request') and 
                self.context.get('request').method == 'GET'):
            if data.get('starttime') is None:
                del data['starttime']
            if data.get('endtime') is None:
                del data['endtime']
            return data

    @validates_schema
    def validate_temporal_constraints(self, data):
        # NOTE(damb): context dependent validation
        if self.context.get('request'):

            starttime = data.get('starttime')
            endtime = data.get('endtime')

            if self.context.get('request').method == 'GET':
                if not endtime:
                    endtime = datetime.datetime.utcnow()

                # reset endtime silently if in future
                if endtime > datetime.datetime.utcnow():
                    endtime = datetime.datetime.utcnow()
                    data['endtime'] = endtime

            elif self.context.get('request').method == 'POST':
                if starttime is None or endtime is None:
                    raise ValidationError('missing temporal constraints')

            if starttime and starttime >= endtime:
                raise ValidationError(
                        'endtime must be greater than starttime')
        else:
            raise ValidationError('missing context')


    class Meta:
        strict = True
        ordered = True

# class SNCLSchema


class ManySNCLSchema(Schema):
    """
    A schema class intended to provide a :code:`many=True` replacement for
    webargs locations different from *json*. This way we are able to treat
    SNCLs like json bulk type arguments.
    """
    sncls = fields.Nested('SNCLSchema', many=True)

    @validates_schema
    def validate_schema(self, data):
        # at least one SNCL must be defined for request.method == 'POST'
        if (self.context.get('request') and
            self.context.get('request').method == 'POST'):
            if 'sncls' not in data or not data['sncls']:
                raise ValidationError('No SNCL defined.')
            if [v for v in data['sncls'] if v is None]:
                raise ValidationError('Invalid SNCL defined.')


    class Meta:
        strict = True

# class ManySNCLSchema

# ---- END OF <schema.py> ----
