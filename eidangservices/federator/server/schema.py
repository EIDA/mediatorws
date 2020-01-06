# -*- coding: utf-8 -*-
"""
Federator schema definitions
"""

import functools

from marshmallow import (Schema, SchemaOpts, fields, validate, ValidationError,
                         pre_load, post_load, validates_schema)

from eidangservices.utils.schema import (Percentage, NotEmptyString,
                                         NotEmptyInt, NotEmptyFloat,
                                         FDSNWSDateTime, Latitude, Longitude,
                                         Radius, FDSNWSBool, NoData)


Quality = functools.partial(fields.Str,
                            validate=validate.OneOf(['D', 'R', 'Q', 'M', 'B']))


# -----------------------------------------------------------------------------
class ServiceOpts(SchemaOpts):
    """
    Same as the default class Meta options, but adds the *service* option.
    """

    def __init__(self, meta, **kwargs):
        SchemaOpts.__init__(self, meta, **kwargs)
        self.service = getattr(meta, 'service', 'dataselect')


# -----------------------------------------------------------------------------
class ServiceSchema(Schema):
    """
    Base class for webservice schema definitions.
    """
    OPTIONS_CLASS = ServiceOpts

    # read-only (the parameter is not parsed by webargs)
    service = fields.Str(dump_only=True)

    @post_load
    def set_service(self, data, **kwargs):
        data['service'] = self.opts.service
        return data

    class Meta:
        strict = True


class DataselectSchema(ServiceSchema):
    """
    Dataselect webservice schema definition

    The parameters defined correspond to the definition
    `<http://www.orfeus-eu.org/data/eida/webservices/dataselect/>`_.
    """
    format = fields.Str(
        missing='miniseed',
        validate=validate.OneOf(['miniseed']))
    nodata = NoData()

    class Meta:
        service = 'dataselect'
        strict = True
        ordered = True


class StationSchema(ServiceSchema):
    """
    Station webservice schema definition

    The parameters defined correspond to the definition
    `<http://www.orfeus-eu.org/data/eida/webservices/station/>`_.
    """

    format = fields.Str(
        missing='xml',
        validate=validate.OneOf(['xml', 'text']))
    nodata = NoData()

    # temporal options
    startbefore = FDSNWSDateTime(format='fdsnws')
    startafter = FDSNWSDateTime(format='fdsnws')
    endbefore = FDSNWSDateTime(format='fdsnws')
    endafter = FDSNWSDateTime(format='fdsnws')

    # geographic (rectangular spatial) options
    minlatitude = Latitude()
    minlat = Latitude(load_only=True)
    maxlatitude = Latitude()
    maxlat = Latitude(load_only=True)
    minlongitude = Longitude()
    minlon = Latitude(load_only=True)
    maxlongitude = Longitude()
    maxlon = Latitude(load_only=True)

    # geographic (circular spatial) options
    latitude = Latitude()
    lat = Latitude(load_only=True)
    longitude = Longitude()
    lon = Latitude(load_only=True)
    minradius = Radius()
    maxradius = Radius()

    # request options
    level = fields.Str(
        missing='station',
        validate=validate.OneOf(
            ['network', 'station', 'channel', 'response']))
    includerestricted = FDSNWSBool(missing='true')
    includeavailability = FDSNWSBool(missing='false')
    updateafter = FDSNWSDateTime(format='fdsnws')
    matchtimeseries = FDSNWSBool(missing='false')

    @pre_load
    def merge_keys(self, data, **kwargs):
        """
        Merge alternative field parameter values.

        .. note::
            The default webargs parser does not provide this feature by
            default such that `load_from` fields parameters are exclusively
            parsed.
        """
        _mappings = [
            ('minlat', 'minlatitude'),
            ('maxlat', 'maxlatitude'),
            ('minlon', 'minlongitude'),
            ('maxlon', 'maxlongitude'),
            ('lat', 'latitude'),
            ('lon', 'longitude')]

        for alt_key, key in _mappings:
            if alt_key in data and key not in data:
                data[key] = data[alt_key]
                data.pop(alt_key)

        return data

    @validates_schema
    def validate_level(self, data, **kwargs):
        if data['format'] == 'text' and data['level'] == 'response':
            raise ValidationError("Invalid level for format 'text'.")

    @validates_schema
    def validate_spatial_params(self, data, **kwargs):
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
        ordered = True


class WFCatalogSchema(ServiceSchema):
    """
    WFCatalog webservice schema definition

    The parameters defined correspond to the definition
    `<http://www.orfeus-eu.org/data/eida/webservices/wfcatalog/>`_ .
    """
    # NOTE(damb): starttime and endtime are required for this schema; for GET
    # requests the extistance of these parameters must be verified, manually

    csegments = FDSNWSBool(missing='false')
    format = fields.Str(
        missing='json',
        validate=validate.OneOf(['json']))
    granularity = fields.Str(missing='day')
    include = fields.Str(
        missing='default',
        validate=validate.OneOf(['default', 'sample', 'header', 'all'])
    )
    longestonly = FDSNWSBool(missing='false')
    # TODO(damb): check with a current WFCatalog webservice
    # minimumlength = fields.Float(missing=0.)
    minimumlength = NotEmptyFloat()

    # record options
    encoding = NotEmptyString()
    num_records = NotEmptyInt()
    quality = Quality()
    record_length = NotEmptyInt()
    # sample_rate = NotEmptyFloat()
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
        ordered = True
