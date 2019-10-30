# -*- coding: utf-8 -*-
"""
Stationlite schema definitions
"""

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
        # validate=validate.OneOf(['xml', 'json', 'get', 'post'])
        validate=validate.OneOf(['post', 'get']))
    service = fields.Str(
        missing='dataselect',
        validate=validate.OneOf(['dataselect', 'station', 'wfcatalog']))

    nodata = NoData()
    alternative = FDSNWSBool(missing='false')

    level = fields.Str(
        missing='channel',
        validate=validate.OneOf(
            ['network', 'station', 'channel', 'response']))

    # geographic (rectangular spatial) options
    # XXX(damb): Default values are defined and assigned within merge_keys ()
    minlatitude = Latitude(missing=-90.)
    minlat = Latitude(load_only=True)
    maxlatitude = Latitude(missing=90.)
    maxlat = Latitude(load_only=True)
    minlongitude = Longitude(missing=-180.)
    minlon = Latitude(load_only=True)
    maxlongitude = Longitude(missing=180.)
    maxlon = Latitude(load_only=True)

    @pre_load
    def merge_keys(self, data, **kwargs):
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
            ('minlat', 'minlatitude'),
            ('maxlat', 'maxlatitude'),
            ('minlon', 'minlongitude'),
            ('maxlon', 'maxlongitude')]

        for alt_key, key in _mappings:
            if alt_key in data and key in data:
                data.pop(alt_key)
            elif alt_key in data and key not in data:
                data[key] = data[alt_key]
                data.pop(alt_key)

        return data

    @validates_schema
    def validate_spatial(self, data, **kwargs):
        if (data['minlatitude'] >= data['maxlatitude'] or
                data['minlongitude'] >= data['maxlongitude']):
            raise ValidationError('Bad Request: Invalid spatial constraints.')

    class Meta:
        strict = True
