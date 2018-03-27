# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <schema.py>
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
# 2017/12/12        V0.1    Daniel Armbruster
# =============================================================================
"""
General marshmallow schema definitions for EIDA NG webservices.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import datetime
import functools

from marshmallow import (Schema, fields, validate, ValidationError,
                         post_load, post_dump, validates_schema)

from eidangservices import utils
from eidangservices.utils import sncl


validate_percentage = validate.Range(min=0, max=100)
validate_latitude = validate.Range(min=-90., max=90)
validate_longitude = validate.Range(min=-180., max=180.)
validate_radius = validate.Range(min=0., max=180.)
validate_net_sta_cha = validate.Regexp(r'[A-Z0-9_*?]*$')
not_empty = validate.NoneOf([None, ''])


def NotEmptyField(field_type, **kwargs):
    return functools.partial(field_type, validate=not_empty, **kwargs)


Percentage = functools.partial(fields.Float, validate=validate_percentage)
NotEmptyString = NotEmptyField(fields.Str)
NotEmptyInt = NotEmptyField(fields.Int, as_string=True)
NotEmptyFloat = NotEmptyField(fields.Float, as_string=True)

Degree = functools.partial(fields.Float, as_string=True)
Latitude = functools.partial(Degree, validate=validate_latitude)
Longitude = functools.partial(Degree, validate=validate_longitude)
Radius = functools.partial(Degree, validate=validate_radius)


# -----------------------------------------------------------------------------
class JSONBool(fields.Bool):
    """
    A field serialializing to a JSON boolean.
    """
    #: Values that will (de)serialize to `True`. If an empty set, any non-falsy
    #  value will deserialize to `true`.
    truthy = set(('true', True))
    #: Values that will (de)serialize to `False`.
    falsy = set(('false', False))

    def _serialize(self, value, attr, obj):

        if value is None:
            return None
        elif value in self.truthy:
            return 'true'
        elif value in self.falsy:
            return 'false'

        return bool(value)

# class JSONBool


FDSNWSBool = JSONBool


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
class StreamEpochSchema(Schema):
    """
    A StreamEpoch Schema. The name *StreamEpoch* refers to the *FDSNWS* POST
    format. A StreamEpoch is a line consisting of:

        network station location channel starttime endtime
    """
    network = fields.Str(load_from='net', missing='*',
                         validate=validate_net_sta_cha)
    station = fields.Str(load_from='sta', missing='*',
                         validate=validate_net_sta_cha)
    location = fields.Str(load_from='loc', missing='*',
                          validate=validate.Regexp(r'[A-Z0-9_*?]*$|--|\s\s'))
    channel = fields.Str(load_from='cha', missing='*',
                         validate=validate_net_sta_cha)
    starttime = FDSNWSDateTime(format='fdsnws', load_from='start')
    endtime = FDSNWSDateTime(format='fdsnws', load_from='end',
                             allow_none=True)

    @post_load
    def make_stream_epoch(self, data):
        if data['location'] == '--':
            data['location'] = ''
        return sncl.StreamEpoch.from_sncl(**data)

    @post_dump
    def skip_empty_datetimes(self, data):
        if (self.context.get('request') and
                self.context.get('request').method == 'GET'):
            if data.get('starttime') is None:
                del data['starttime']
            if data.get('endtime') is None:
                del data['endtime']
        elif self.context.get('routing'):
            if (data.get('endtime') is None or 
                    utils.from_fdsnws_datetime(
                        data.get('endtime')) == datetime.datetime.max):
                del data['endtime']

        return data

    @post_dump
    def replace_empty_location(self, data):
        """
        Replaces empty location identifiers when serializing.
        """
        if data['location'] == '':
            data['location'] = '--'
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

    class Meta:
        strict = True
        ordered = True

# class StreamEpochSchema


class ManyStreamEpochSchema(Schema):
    """
    A schema class intended to provide a :code:`many=True` replacement for
    webargs locations different from *json*. This way we are able to treat
    StreamEpoch objects like json bulk type arguments.
    """
    stream_epochs = fields.Nested('StreamEpochSchema', many=True)

    @validates_schema
    def validate_schema(self, data):
        # at least one SNCL must be defined for request.method == 'POST'
        if (self.context.get('request') and
                self.context.get('request').method == 'POST'):
            if 'stream_epochs' not in data or not data['stream_epochs']:
                raise ValidationError('No StreamEpoch defined.')
            if [v for v in data['stream_epochs'] if v is None]:
                raise ValidationError('Invalid StreamEpoch defined.')

    class Meta:
        strict = True

# class ManyStreamEpochSchema

# ---- END OF <schema.py> ----
