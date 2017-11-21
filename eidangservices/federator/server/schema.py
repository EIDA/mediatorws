# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <schema.py>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/10/19        V0.1    Daniel Armbruster
# =============================================================================
"""
Federator schema definitions
"""

import datetime
import functools
import webargs 

import marshmallow as ma
from marshmallow import (Schema, SchemaOpts, fields, validate,
    ValidationError, post_load, post_dump, validates_schema)

from eidangservices import settings
from eidangservices.federator.server.misc import \
        from_fdsnws_datetime, fdsnws_isoformat


# TODO(damb): Improve error messages.
# TODO(damb): Improve 'format' field implementation.

validate_percentage = validate.Range(min=0, max=100)
validate_latitude = validate.Range(min=-90., max=90)
validate_longitude = validate.Range(min=-180., max=180.)
validate_radius = validate.Range(min=0., max=180.)

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
        validate=validate.OneOf([
            settings.FDSN_DEFAULT_NO_CONTENT_ERROR_CODE,
            404
        ])
    )
Quality = functools.partial(
        fields.Str,
        validate=validate.OneOf(['D', 'R', 'Q', 'M', 'B'])
    )

# -----------------------------------------------------------------------------
class JSONBool(fields.Bool):
    """
    A field serialializing to a JSON boolean.
    """
    #: Values that will (de)serialize to `True`. If an empty set, any non-falsy
    #  value will deserialize to `true`.
    truthy = set((u'true', True))
    #: Values that will (de)serialize to `False`.
    falsy = set((u'false', False))

    def _serialize(self, value, attr, obj):

        if value is None:
            return None
        elif value in self.truthy:
            return u'true'
        elif value in self.falsy:
            return u'false'

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

    DATEFORMAT_SERIALIZATION_FUNCS['fdsnws'] = fdsnws_isoformat
    DATEFORMAT_DESERIALIZATION_FUNCS['fdsnws'] = from_fdsnws_datetime

# class FDSNWSDateTime     


class RequestList(fields.List):
    """
    A list providing a request context dependent serialization.

    I.e. in case the list contains just a single value it serializes by means
    of returning the values serialized result. 
    """
    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        if self.context.get('request'):
            if self.context.get('request').method == 'GET' and 1 == len(value):
                # flatten list content for a single value
                return self.container._serialize(value[0], attr, obj)
        return super(RequestList, self)._serialize(value, attr, obj)

# class RequestList


class DelimitedRequestList(webargs.fields.DelimitedList):
    """
    A delimited list providing a request context dependent serialization.

    For *GET* requests the list serializes the same way as for :py:attr:
    as_string.
    """
    def _serialize(self, value, attr, obj):
        ret = super(DelimitedRequestList, self)._serialize(value, attr, obj)
        if not 'request' in self.context:
            return ret
        if self.as_string or self.context.get('request').method == 'GET':
            return self.delimiter.join(format(each) for each in value)
        return ret

# class DelimitedRequestList  


# -----------------------------------------------------------------------------
class SNCLSchema(Schema):
    """
    A SNCL Schema. SNCLs refer to the *FDSNWS* POST format. A SNCL is a line
    consisting of::

        network station location channel starttime endtime
    """
    network = DelimitedRequestList(
        fields.Str(),
        load_from='net', 
        delimiter=settings.FDSNWS_QUERY_LIST_SEPARATOR_CHAR,
        missing = ['*']
    )
    station = DelimitedRequestList(
        fields.Str(),
        load_from='sta', 
        delimiter=settings.FDSNWS_QUERY_LIST_SEPARATOR_CHAR,
        missing = ['*']
    )
    location = DelimitedRequestList(
        fields.Str(),
        load_from='loc', 
        delimiter=settings.FDSNWS_QUERY_LIST_SEPARATOR_CHAR,
        missing=['*']
    )
    channel = DelimitedRequestList(
        fields.Str(),
        load_from='cha', 
        delimiter=settings.FDSNWS_QUERY_LIST_SEPARATOR_CHAR,
        missing = ['*']
    )
    starttime = RequestList(
        FDSNWSDateTime(format='fdsnws'),
        load_from='start',
        missing = []
    )
    endtime = RequestList(
        FDSNWSDateTime(format='fdsnws'),
        load_from='end',
        missing = []
    )

    @post_dump
    def skip_empty_datetimes(self, data):
        if (self.context.get('request') and 
                self.context.get('request').method == 'GET'):
            if not data.get('starttime'):
                del data['starttime']
            if not data.get('endtime'):
                del data['endtime']
            return data


    @validates_schema
    def validate(self, data):
        """
        SNCL schema validator
        """
        def validate_datetimes(context, data):
            # NOTE(damb): context dependent validation
            invalid = []
            if context.get('request'):
                if context.get('request').method == 'GET':
                    # for request.method == 'GET' only accept one datetime item
                    # in the list
                    starttime = data.get('starttime')
                    if not starttime:
                        starttime = []

                    endtime = data.get('endtime')
                    if not endtime:
                        endtime = [datetime.datetime.utcnow()]

                    if (len(starttime) > 1 or len(endtime) > 1):
                        raise ValidationError('invalid number of times passed')
                    if ((len(starttime) == 1 and not starttime[0]) or
                    (len(endtime) == 1 and not endtime[0])):
                        raise ValidationError('invalid values passed')

                    # reset endtime silently if in future
                    if endtime[0] > datetime.datetime.utcnow():
                        endtime = [datetime.datetime.utcnow()]
                        data['endtime'] = endtime

                    if (len(starttime) == 1 and starttime[0] >= endtime[0]): 
                        invalid.append((starttime[0], endtime[0]))

                elif context.get('request').method == 'POST':
                    try:
                        invalid = [(s_time, e_time) for s_time, e_time in
                                zip(data['starttime'], data['endtime']) 
                                if s_time >= e_time]
                    except TypeError:
                        raise ValidationError('invalid temporal constraints')
                    except KeyError:
                        raise ValidationError('missing temporal constraints')
                else:
                    pass

            if invalid:
                raise ValidationError('endtime must be greater than starttime')

        def validate_schema(context, data):
            # at least one SNCL must be defined for request.method == 'POST'
            if (context.get('request') and 
                    context.get('request').method == 'POST'):
                if [v for v in data.values() if len(v) < 1]:
                    raise ValidationError('No SNCL defined.')
                if 1 != len(set([len(v) for v in data.values()])):
                    raise ValidationError('Invalid SNCL definition')
       
        validate_datetimes(self.context, data)
        validate_schema(self.context, data)


    class Meta:
        strict = True
        ordered = True

# class SNCLSchema


class ServiceOpts(SchemaOpts):
    """
    Same as the default class Meta options, but adds the *service* option.
    """

    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.service = getattr(meta, 'service', 'dataselect')

# class ServiceOpts


# -----------------------------------------------------------------------------
class ServiceSchema(Schema):
    """
    Base class for webservice schema definitions.
    """
    OPTIONS_CLASS = ServiceOpts

    # read-only (the parameter is not parsed by webargs)
    service = fields.Str(dump_only=True)

    @post_load
    def set_service(self, item):
        item['service'] = self.opts.service

    class Meta:
        strict = True

# class ServiceSchema


class DataselectSchema(ServiceSchema):
    """
    Dataselect webservice schema definition

    The parameters defined correspond to the definition
    `<http://www.orfeus-eu.org/data/eida/webservices/dataselect/>`_.
    """
    format = fields.Str(
            missing='miniseed',
            validate=validate.OneOf(['miniseed'])
        )
    nodata = NoData()

    quality = Quality()#missing='B')
    minimumlength = fields.Float(
            missing=0.,
            validate=lambda n: 0. <= n
        )
    longestonly = FDSNWSBool(missing=u'false')

    class Meta:
        service = 'dataselect'
        strict = True

# class DataselectSchema 


class StationSchema(ServiceSchema):
    """
    Station webservice schema definition

    The parameters defined correspond to the definition
    `<http://www.orfeus-eu.org/data/eida/webservices/station/>`_.
    """
    
    format = fields.Str(
            missing='xml',
            validate=validate.OneOf(['xml', 'text'])
        )
    nodata = NoData()

    # temporal options
    startbefore = FDSNWSDateTime(format='fdsnws')
    startafter = FDSNWSDateTime(format='fdsnws')
    endbefore = FDSNWSDateTime(format='fdsnws')
    endafter = FDSNWSDateTime(format='fdsnws')

    # geographic (rectangular spatial) options
    minlatitude = Latitude(load_from='minlat')
    maxlatitude = Latitude(load_from='maxlat')
    minlongitude = Longitude(load_from='minlon')
    maxlongitude = Longitude(load_from='maxlon')

    # geographic (circular spatial) options
    latitude = Latitude(load_from='lat')
    longitude = Longitude(load_from='lon')
    minradius = Radius()
    maxradius = Radius()

    # request options
    level = fields.Str(
            missing='station',
            validate=validate.OneOf(
                ['network', 'station', 'channel', 'response']
            )
        )
    includerestricted = FDSNWSBool(missing=u'true')
    includeavailability = FDSNWSBool(missing=u'false')
    updateafter = FDSNWSDateTime(format='fdsnws')
    matchtimeseries = FDSNWSBool(missing=u'false')


    @validates_schema
    def validate_spatial_params(self, data):
        # NOTE(damb): Allow either rectangular or circular spatial parameters
        rectangular_spatial = ('minlatitude', 'maxlatitude', 'minlongitude',
                'maxlongitude')
        circular_spatial = ('latitude', 'longitude', 'minradius', 'maxradius')

        if (any(k in data for k in rectangular_spatial) and
                any(k in data for k in circular_spatial)):
            raise ValidationError(
                'Bad Request: Both rectangular spatial and circular spatial' +
                ' parameters defined.')
            # TODO(damb): check if min values are smaller than max values;
            # no default values are set

    class Meta:
        service = 'station'
        strict = True

# class StationSchema 


class WFCatalogSchema(ServiceSchema):
    """
    WFCatalog webservice schema definition

    The parameters defined correspond to the definition
    `<http://www.orfeus-eu.org/data/eida/webservices/wfcatalog/>`_ .
    """
    # TODO(damb): starttime and endtime are required for this schema; howto
    # implement a proper validator/ required=True

    csegments = FDSNWSBool(missing=u'false')
    format = fields.Str(
            missing='json',
            validate=validate.OneOf(['json'])
        )
    granularity = fields.Str(missing='day')
    include = fields.Str(
        missing='default',
        validate=validate.OneOf(['default', 'sample', 'header', 'all'])
    )
    longestonly = FDSNWSBool(missing=u'false')
    #minimumlength = fields.Float(missing=0.)
    minimumlength = NotEmptyFloat()

    # record options
    encoding = NotEmptyString()
    num_records = NotEmptyInt()
    quality = Quality()
    record_length = NotEmptyInt()
    #sample_rate = NotEmptyFloat()
    sample_rate = fields.Float(as_string=True)

    # sample metric options (including metric filtering)
    max_gap = NotEmptyFloat()
    max_gap_eq = NotEmptyFloat()
    max_gap_gt = NotEmptyFloat()
    max_gap_ge = NotEmptyFloat()
    max_gap_lt = NotEmptyFloat()
    max_gap_le = NotEmptyFloat()
    max_gap_ne = NotEmptyFloat()

    max_overlap = NotEmptyFloat()
    max_overlap_eq = NotEmptyFloat()
    max_overlap_gt = NotEmptyFloat()
    max_overlap_ge = NotEmptyFloat()
    max_overlap_lt = NotEmptyFloat()
    max_overlap_le = NotEmptyFloat()
    max_overlap_ne = NotEmptyFloat()

    num_gaps = NotEmptyInt()
    num_gaps_eq = NotEmptyInt()
    num_gaps_gt = NotEmptyInt()
    num_gaps_ge = NotEmptyInt()
    num_gaps_lt = NotEmptyInt()
    num_gaps_le = NotEmptyInt()
    num_gaps_ne = NotEmptyInt()

    num_overlaps = NotEmptyInt()
    num_overlaps_eq = NotEmptyInt()
    num_overlaps_gt = NotEmptyInt()
    num_overlaps_ge = NotEmptyInt()
    num_overlaps_lt = NotEmptyInt()
    num_overlaps_le = NotEmptyInt()
    num_overlaps_ne = NotEmptyInt()

    num_samples = NotEmptyInt()
    num_samples_eq = NotEmptyInt()
    num_samples_gt = NotEmptyInt()
    num_samples_ge = NotEmptyInt()
    num_samples_lt = NotEmptyInt()
    num_samples_le = NotEmptyInt()
    num_samples_ne = NotEmptyInt()

    percent_availability = Percentage()
    percent_availability_eq = Percentage()
    percent_availability_gt = Percentage()
    percent_availability_ge = Percentage()
    percent_availability_lt = Percentage()
    percent_availability_le = Percentage()
    percent_availability_ne = Percentage()

    sample_max = NotEmptyInt()
    sample_max_eq = NotEmptyInt()
    sample_max_gt = NotEmptyInt()
    sample_max_ge = NotEmptyInt()
    sample_max_lt = NotEmptyInt()
    sample_max_le = NotEmptyInt()
    sample_max_ne = NotEmptyInt()

    samples_min = NotEmptyInt()
    samples_min_eq = NotEmptyInt()
    samples_min_gt = NotEmptyInt()
    samples_min_ge = NotEmptyInt()
    samples_min_lt = NotEmptyInt()
    samples_min_le = NotEmptyInt()
    samples_min_ne = NotEmptyInt()

    sample_mean = NotEmptyInt()
    sample_mean_eq = NotEmptyInt()
    sample_mean_gt = NotEmptyInt()
    sample_mean_ge = NotEmptyInt()
    sample_mean_lt = NotEmptyInt()
    sample_mean_le = NotEmptyInt()
    sample_mean_ne = NotEmptyInt()

    samples_rms = NotEmptyFloat()
    samples_rms_eq = NotEmptyFloat()
    samples_rms_gt = NotEmptyFloat()
    samples_rms_ge = NotEmptyFloat()
    samples_rms_lt = NotEmptyFloat()
    samples_rms_le = NotEmptyFloat()
    samples_rms_ne = NotEmptyFloat()

    sample_stdev = NotEmptyFloat()
    sample_stdev_eq = NotEmptyFloat()
    sample_stdev_gt = NotEmptyFloat()
    sample_stdev_ge = NotEmptyFloat()
    sample_stdev_lt = NotEmptyFloat()
    sample_stdev_le = NotEmptyFloat()
    sample_stdev_ne = NotEmptyFloat()

    sample_lower_quartile = NotEmptyFloat()
    sample_lower_quartile_eq = NotEmptyFloat()
    sample_lower_quartile_gt = NotEmptyFloat()
    sample_lower_quartile_ge = NotEmptyFloat()
    sample_lower_quartile_lt = NotEmptyFloat()
    sample_lower_quartile_le = NotEmptyFloat()
    sample_lower_quartile_ne = NotEmptyFloat()

    sample_median = NotEmptyFloat()
    sample_median_eq = NotEmptyFloat()
    sample_median_gt = NotEmptyFloat()
    sample_median_ge = NotEmptyFloat()
    sample_median_lt = NotEmptyFloat()
    sample_median_le = NotEmptyFloat()
    sample_median_ne = NotEmptyFloat()

    sample_upper_quartile = NotEmptyFloat()
    sample_upper_quartile_eq = NotEmptyFloat()
    sample_upper_quartile_gt = NotEmptyFloat()
    sample_upper_quartile_ge = NotEmptyFloat()
    sample_upper_quartile_lt = NotEmptyFloat()
    sample_upper_quartile_le = NotEmptyFloat()
    sample_upper_quartile_ne = NotEmptyFloat()

    sum_gaps = NotEmptyFloat()
    sum_gaps_eq = NotEmptyFloat()
    sum_gaps_gt = NotEmptyFloat()
    sum_gaps_ge = NotEmptyFloat()
    sum_gaps_lt = NotEmptyFloat()
    sum_gaps_le = NotEmptyFloat()
    sum_gaps_ne = NotEmptyFloat()

    sum_overlaps = NotEmptyFloat()
    sum_overlaps_eq = NotEmptyFloat()
    sum_overlaps_gt = NotEmptyFloat()
    sum_overlaps_ge = NotEmptyFloat()
    sum_overlaps_lt = NotEmptyFloat()
    sum_overlaps_le = NotEmptyFloat()
    sum_overlaps_ne = NotEmptyFloat()

    # header flag options (including metric filtering)
    amplifier_saturation = Percentage()
    amplifier_saturation_eq = Percentage()
    amplifier_saturation_gt = Percentage()
    amplifier_saturation_ge = Percentage()
    amplifier_saturation_lt = Percentage()
    amplifier_saturation_le = Percentage()
    amplifier_saturation_ne = Percentage()

    calibration_signal = Percentage()
    calibration_signal_eq = Percentage()
    calibration_signal_gt = Percentage()
    calibration_signal_ge = Percentage()
    calibration_signal_lt = Percentage()
    calibration_signal_le = Percentage()
    calibration_signal_ne = Percentage()

    clock_locked = Percentage()
    clock_locked_eq = Percentage()
    clock_locked_gt = Percentage()
    clock_locked_ge = Percentage()
    clock_locked_lt = Percentage()
    clock_locked_le = Percentage()
    clock_locked_ne = Percentage()

    digital_filter_charging = Percentage()
    digital_filter_charging_eq = Percentage()
    digital_filter_charging_gt = Percentage()
    digital_filter_charging_ge = Percentage()
    digital_filter_charging_lt = Percentage()
    digital_filter_charging_le = Percentage()
    digital_filter_charging_ne = Percentage()

    digitizer_clipping = Percentage()
    digitizer_clipping_eq = Percentage()
    digitizer_clipping_gt = Percentage()
    digitizer_clipping_ge = Percentage()
    digitizer_clipping_lt = Percentage()
    digitizer_clipping_le = Percentage()
    digitizer_clipping_ne = Percentage()

    start_time_series = Percentage()
    start_time_series_eq = Percentage()
    start_time_series_gt = Percentage()
    start_time_series_ge = Percentage()
    start_time_series_lt = Percentage()
    start_time_series_le = Percentage()
    start_time_series_ne = Percentage()

    end_time_series = Percentage()
    end_time_series_eq = Percentage()
    end_time_series_gt = Percentage()
    end_time_series_ge = Percentage()
    end_time_series_lt = Percentage()
    end_time_series_le = Percentage()
    end_time_series_ne = Percentage()

    event_begin = Percentage()
    event_begin_eq = Percentage()
    event_begin_gt = Percentage()
    event_begin_ge = Percentage()
    event_begin_lt = Percentage()
    event_begin_le = Percentage()
    event_begin_ne = Percentage()

    event_end = Percentage()
    event_end_eq = Percentage()
    event_end_gt = Percentage()
    event_end_ge = Percentage()
    event_end_lt = Percentage()
    event_end_le = Percentage()
    event_end_ne = Percentage()

    event_in_progress = Percentage()
    event_in_progress_eq = Percentage()
    event_in_progress_gt = Percentage()
    event_in_progress_ge = Percentage()
    event_in_progress_lt = Percentage()
    event_in_progress_le = Percentage()
    event_in_progress_ne = Percentage()

    glitches = Percentage()
    glitches_eq = Percentage()
    glitches_gt = Percentage()
    glitches_ge = Percentage()
    glitches_lt = Percentage()
    glitches_le = Percentage()
    glitches_ne = Percentage()

    long_record_read = Percentage()
    long_record_read_eq = Percentage()
    long_record_read_gt = Percentage()
    long_record_read_ge = Percentage()
    long_record_read_lt = Percentage()
    long_record_read_le = Percentage()
    long_record_read_ne = Percentage()

    missing_padded_data = Percentage()
    missing_padded_data_eq = Percentage()
    missing_padded_data_gt = Percentage()
    missing_padded_data_ge = Percentage()
    missing_padded_data_lt = Percentage()
    missing_padded_data_le = Percentage()
    missing_padded_data_ne = Percentage()

    positive_leap = Percentage()
    positive_leap_eq = Percentage()
    positive_leap_gt = Percentage()
    positive_leap_ge = Percentage()
    positive_leap_lt = Percentage()
    positive_leap_le = Percentage()
    positive_leap_ne = Percentage()

    short_record_read = Percentage()
    short_record_read_eq = Percentage()
    short_record_read_gt = Percentage()
    short_record_read_ge = Percentage()
    short_record_read_lt = Percentage()
    short_record_read_le = Percentage()
    short_record_read_ne = Percentage()

    spikes = Percentage()
    spikes_eq = Percentage()
    spikes_gt = Percentage()
    spikes_ge = Percentage()
    spikes_lt = Percentage()
    spikes_le = Percentage()
    spikes_ne = Percentage()

    station_volume = Percentage()
    station_volume_eq = Percentage()
    station_volume_gt = Percentage()
    station_volume_ge = Percentage()
    station_volume_lt = Percentage()
    station_volume_le = Percentage()
    station_volume_ne = Percentage()

    suspect_time_tag = Percentage()
    suspect_time_tag_eq = Percentage()
    suspect_time_tag_gt = Percentage()
    suspect_time_tag_ge = Percentage()
    suspect_time_tag_lt = Percentage()
    suspect_time_tag_le = Percentage()
    suspect_time_tag_ne = Percentage()

    telemetry_sync_error = Percentage()
    telemetry_sync_error_eq = Percentage()
    telemetry_sync_error_gt = Percentage()
    telemetry_sync_error_ge = Percentage()
    telemetry_sync_error_lt = Percentage()
    telemetry_sync_error_le = Percentage()
    telemetry_sync_error_ne = Percentage()

    time_correction_applied = Percentage()
    time_correction_applied_eq = Percentage()
    time_correction_applied_gt = Percentage()
    time_correction_applied_ge = Percentage()
    time_correction_applied_lt = Percentage()
    time_correction_applied_le = Percentage()
    time_correction_applied_ne = Percentage()

    # timing quality options (including metric filtering) 
    timing_correction = Percentage()
    timing_correction_eq = Percentage()
    timing_correction_gt = Percentage()
    timing_correction_ge = Percentage()
    timing_correction_lt = Percentage()
    timing_correction_le = Percentage()
    timing_correction_ne = Percentage()

    timing_quality_max = NotEmptyFloat()
    timing_quality_max_eq = NotEmptyFloat()
    timing_quality_max_gt = NotEmptyFloat()
    timing_quality_max_ge = NotEmptyFloat()
    timing_quality_max_lt = NotEmptyFloat()
    timing_quality_max_le = NotEmptyFloat()
    timing_quality_max_ne = NotEmptyFloat()

    timing_quality_min = NotEmptyFloat()
    timing_quality_min_eq = NotEmptyFloat()
    timing_quality_min_gt = NotEmptyFloat()
    timing_quality_min_ge = NotEmptyFloat()
    timing_quality_min_lt = NotEmptyFloat()
    timing_quality_min_le = NotEmptyFloat()
    timing_quality_min_ne = NotEmptyFloat()

    timing_quality_mean = NotEmptyFloat()
    timing_quality_mean_eq = NotEmptyFloat()
    timing_quality_mean_gt = NotEmptyFloat()
    timing_quality_mean_ge = NotEmptyFloat()
    timing_quality_mean_lt = NotEmptyFloat()
    timing_quality_mean_le = NotEmptyFloat()
    timing_quality_mean_ne = NotEmptyFloat()

    timing_quality_median = NotEmptyFloat()
    timing_quality_median_eq = NotEmptyFloat()
    timing_quality_median_gt = NotEmptyFloat()
    timing_quality_median_ge = NotEmptyFloat()
    timing_quality_median_lt = NotEmptyFloat()
    timing_quality_median_le = NotEmptyFloat()
    timing_quality_median_ne = NotEmptyFloat()

    timing_quality_lower_quartile = NotEmptyFloat()
    timing_quality_lower_quartile_eq = NotEmptyFloat()
    timing_quality_lower_quartile_gt = NotEmptyFloat()
    timing_quality_lower_quartile_ge = NotEmptyFloat()
    timing_quality_lower_quartile_lt = NotEmptyFloat()
    timing_quality_lower_quartile_le = NotEmptyFloat()
    timing_quality_lower_quartile_ne = NotEmptyFloat()

    timing_quality_upper_quartile = NotEmptyFloat()
    timing_quality_upper_quartile_eq = NotEmptyFloat()
    timing_quality_upper_quartile_gt = NotEmptyFloat()
    timing_quality_upper_quartile_ge = NotEmptyFloat()
    timing_quality_upper_quartile_lt = NotEmptyFloat()
    timing_quality_upper_quartile_le = NotEmptyFloat()
    timing_quality_upper_quartile_ne = NotEmptyFloat()


    class Meta:
        service = 'wfcatalog'
        strict = True

# class WfCatalogSchema

# ---- END OF <schema.py> ----
