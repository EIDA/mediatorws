# -*- coding: utf-8 -*-
"""
General marshmallow schema definitions for EIDA NG webservices.
"""

import datetime
import functools

from marshmallow import (Schema, fields, validate, ValidationError,
                         pre_load, post_load, post_dump,
                         validates_schema)

from eidangservices import settings, utils
from eidangservices.utils import sncl


validate_percentage = validate.Range(min=0, max=100)
validate_latitude = validate.Range(min=-90., max=90)
validate_longitude = validate.Range(min=-180., max=180.)
validate_radius = validate.Range(min=0., max=180.)
validate_net_sta_cha = validate.Regexp(r'[A-Za-z0-9_*?]*$')
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

NoData = functools.partial(
    fields.Int,
    as_string=True,
    missing=settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE,
    validate=validate.OneOf(settings.FDSN_NO_CONTENT_CODES))


# -----------------------------------------------------------------------------
class JSONBool(fields.Bool):
    """
    Custom field serialializing to a JSON boolean.
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


FDSNWSBool = JSONBool


class FDSNWSDateTime(fields.DateTime):
    """
    The class extends marshmallow standard DateTime with a FDSNWS *datetime*
    format.

    The FDSNWS *datetime* format is described in the `FDSN Web Service
    Specifications
    <http://www.fdsn.org/webservices/FDSN-WS-Specifications-1.1.pdf>`_.
    """

    SERIALIZATION_FUNCS = fields.DateTime.SERIALIZATION_FUNCS.copy()

    DESERIALIZATION_FUNCS = fields.DateTime.DESERIALIZATION_FUNCS.copy()

    SERIALIZATION_FUNCS['fdsnws'] = utils.fdsnws_isoformat
    DESERIALIZATION_FUNCS['fdsnws'] = utils.from_fdsnws_datetime


# -----------------------------------------------------------------------------
class StreamEpochSchema(Schema):
    """
    A marshmallow StreamEpoch Schema. The name *StreamEpoch* refers to the
    FDSNWS **POST** format. A StreamEpoch is a line consisting of:

    .. code::

        network station location channel starttime endtime

    """
    network = fields.Str(missing='*', validate=validate_net_sta_cha)
    net = fields.Str(load_only=True)

    station = fields.Str(missing='*', validate=validate_net_sta_cha)
    sta = fields.Str(load_only=True)

    location = fields.Str(missing='*',
                          validate=validate.Regexp(r'[A-Z0-9_*?]*$|--|\s\s'))
    loc = fields.Str(load_only=True)

    channel = fields.Str(missing='*', validate=validate_net_sta_cha)
    cha = fields.Str(load_only=True)

    starttime = FDSNWSDateTime(format='fdsnws')
    start = fields.Str(load_only=True)

    endtime = FDSNWSDateTime(format='fdsnws', allow_none=True)
    end = fields.Str(load_only=True)

    @pre_load
    def merge_keys(self, data, **kwargs):
        """
        Merge alternative field parameter values.

        .. note::

            The default :py:mod:`webargs` parser does not provide this feature
            by default such that :code:`data_key` field parameters are
            exclusively parsed.
        """
        _mappings = [
            ('net', 'network'),
            ('sta', 'station'),
            ('loc', 'location'),
            ('cha', 'channel'),
            ('start', 'starttime'),
            ('end', 'endtime')]

        for alt_key, key in _mappings:
            if alt_key in data and key not in data:
                data[key] = data[alt_key]
                data.pop(alt_key)

        return data

    @post_load
    def make_stream_epoch(self, data, **kwargs):
        """
        Factory method generating
        :py:class:`eidangservices.utils.sncl.StreamEpoch` objects.
        """
        if data['location'] == '--':
            data['location'] = ''
        return sncl.StreamEpoch.from_sncl(**data)

    @post_dump
    def skip_empty_datetimes(self, data, **kwargs):
        """
        Provides context dependend skipping of *empty* datetimes when
        serializing.
        """
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
    def replace_empty_location(self, data, **kwargs):
        """
        Replaces empty location identifiers when serializing.
        """
        if data['location'] == '':
            data['location'] = '--'
        return data

    @validates_schema
    def validate_temporal_constraints(self, data, **kwargs):
        """
        Validation of temporal constraints.
        """
        # NOTE(damb): context dependent validation
        if self.context.get('request'):

            starttime = data.get('starttime')
            endtime = data.get('endtime')
            now = datetime.datetime.utcnow()

            if self.context.get('request').method == 'GET':

                if not endtime:
                    endtime = now
                elif endtime > now:
                    endtime = now
                    if self.context.get('service') != 'eidaws-wfcatalog':
                        data['endtime'] = None

            elif self.context.get('request').method == 'POST':
                if starttime is None or endtime is None:
                    raise ValidationError('missing temporal constraints')

            if starttime:
                if starttime > now:
                    raise ValidationError('starttime in future')
                elif starttime >= endtime:
                    raise ValidationError(
                        'endtime must be greater than starttime')

    class Meta:
        strict = True
        ordered = True


class ManyStreamEpochSchema(Schema):
    """
    A schema class intended to provide a :code:`many=True` replacement for
    :py:mod:`webargs` locations different from *JSON*. This way we are able to
    treat :py:class:`eidangservices.utils.sncl.StreamEpoch` objects like JSON
    bulk type arguments.
    """
    stream_epochs = fields.List(fields.Nested('StreamEpochSchema'))

    @validates_schema
    def validate_schema(self, data, **kwargs):
        # at least one SNCL must be defined for request.method == 'POST'
        if (self.context.get('request') and
                self.context.get('request').method == 'POST'):
            if 'stream_epochs' not in data or not data['stream_epochs']:
                raise ValidationError('No StreamEpoch defined.')
            if not all(data['stream_epochs']):
                raise ValidationError('Invalid StreamEpoch defined.')

    class Meta:
        strict = True
