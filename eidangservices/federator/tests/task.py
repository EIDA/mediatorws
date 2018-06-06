# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <task.py>
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
# REVISION AND CHANGES
# 2018/06/04        V0.1    Daniel Armbruster
#
# =============================================================================
"""
Task related test facilities.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import * # noqa

import datetime
import io
import json
import os
import tempfile
import unittest

from eidangservices.federator.server.task import (
    SplitAndAlignTask, WFCatalogSplitAndAlignTask, Result)
from eidangservices.federator.server.request import RequestsError
from eidangservices.utils.sncl import Stream, StreamEpoch

try:
    import mock
except ImportError:
    import unittest.mock as mock


# -----------------------------------------------------------------------------
class Response(object):

    def __init__(self, status_code=500, data=None):
        self.status_code = status_code
        self.data = data

# class Response

class HTTP413(RequestsError):
    def __init__(self):
        self.response = Response(status_code=413,
                                 data='RequestTooLarge')

class HTTP500(RequestsError):
    def __init__(self):
        self.response = Response(status_code=500,
                                 data='InternalServerError')

# -----------------------------------------------------------------------------
# SplitAndAlign task related test cases

class SplitAndAlignTaskTestCase(unittest.TestCase):

    def setUp(self):
        self.stream = Stream(network='CH', station='DAVOX', location='',
                             channel='HHZ')
        self.url = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        self.query_params = {}

    def tearDown(self):
        self.url = None
        self.query_params = None

    def test_split_once(self):
        stream_epoch = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 8))

        reference_result = [
            StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 1),
                endtime=datetime.datetime(2018, 1, 4, 12)),
            StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 4, 12),
                endtime=datetime.datetime(2018, 1, 8))]

        # NOTE(damb): Use the same stream epoch both for testing the splitting
        # method as well as for task initialization. In case of just testing
        # splitting we could have used any arbitrary stream epoch for task
        # initialization.

        t = SplitAndAlignTask(self.url, stream_epoch, self.query_params)
        self.assertEqual(t.split(stream_epoch, t.DEFAULT_SPLITTING_CONST),
                         reference_result)
        self.assertEqual(t.stream_epochs, reference_result)

    # test_split_once ()

    def test_split_multiple(self):
        stream_epoch_orig = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 8))

        sub_reference_result = [
            StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 1),
                endtime=datetime.datetime(2018, 1, 2, 18)),
            StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 2, 18),
                endtime=datetime.datetime(2018, 1, 4, 12))]
        reference_result = (
            sub_reference_result +
            [StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 4, 12),
                endtime=datetime.datetime(2018, 1, 8))])

        # NOTE(damb): Use the same stream epoch both for testing the splitting
        # method as well as for task initialization. In case of just testing
        # splitting we could have used any arbitrary stream epoch for task
        # initialization.

        t = SplitAndAlignTask(self.url, stream_epoch_orig, self.query_params)
        stream_epochs = t.split(stream_epoch_orig, t.DEFAULT_SPLITTING_CONST)
        sub_stream_epochs = t.split(stream_epochs[0],
                                    t.DEFAULT_SPLITTING_CONST)

        self.assertEqual(sub_stream_epochs, sub_reference_result)
        self.assertEqual(t.stream_epochs, reference_result)

    # test_split_multiple ()

# class SplitAndAlignTaskTestCase


class WFCatalogSAATaskTestCase(unittest.TestCase):

    def setUp(self):
        _, self.path_tempfile = tempfile.mkstemp()

        self.stream = Stream(network='CH', station='DAVOX', location='',
                             channel='HHZ')
        self.url = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        self.query_params = {}

    def tearDown(self):
        try:
            os.remove(self.path_tempfile)
        except OSError:
            pass
        self.path_tempfile = None

    @mock.patch('eidangservices.federator.server.task.raw_request')
    @mock.patch('eidangservices.federator.server.task.get_temp_filepath')
    def test_split_missing(self, mock_get_temp_filepath, mock_raw_request):

        err = HTTP500()
        mock_get_temp_filepath.return_value = self.path_tempfile
        mock_raw_request.side_effect = [
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            err]
        reference_result = Result.error('EndpointError',
                                        err.response.status_code,
                                        data=err.response.data,
                                        warning=str(err))

        stream_epoch_orig = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 3))

        result = WFCatalogSplitAndAlignTask(self.url, stream_epoch_orig,
                                            self.query_params)()
        self.assertEqual(result, reference_result)
        mock_raw_request.has_calls()

    # test_split_missing ()

    @mock.patch('eidangservices.federator.server.task.raw_request')
    @mock.patch('eidangservices.federator.server.task.get_temp_filepath')
    def test_split_single_without_overlap(self, mock_get_temp_filepath,
                                          mock_raw_request):

        mock_get_temp_filepath.return_value = self.path_tempfile
        mock_raw_request.side_effect = [
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]')] # noqa

        reference_result = json.loads(
            '[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]') # noqa

        stream_epoch_orig = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 3))

        result = WFCatalogSplitAndAlignTask(self.url, stream_epoch_orig,
                                            self.query_params)()
        data = None
        with open(result.data, 'rb') as ifd:
            data = json.loads(ifd.read().decode('utf-8'))

        self.assertEqual(data, reference_result)
        mock_raw_request.has_calls()

    # test_split_single_without_overlap ()

    @mock.patch('eidangservices.federator.server.task.raw_request')
    @mock.patch('eidangservices.federator.server.task.get_temp_filepath')
    def test_split_single_with_overlap(self, mock_get_temp_filepath,
                                       mock_raw_request):

        mock_get_temp_filepath.return_value = self.path_tempfile
        mock_raw_request.side_effect = [
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]')] # noqa

        reference_result = json.loads(
            '[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]') # noqa

        stream_epoch_orig = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 3))

        result = WFCatalogSplitAndAlignTask(self.url, stream_epoch_orig,
                                            self.query_params)()
        data = None
        with open(result.data, 'rb') as ifd:
            data = json.loads(ifd.read().decode('utf-8'))

        self.assertEqual(data, reference_result)
        mock_raw_request.has_calls()

    # test_split_single_with_overlap ()

    @mock.patch('eidangservices.federator.server.task.raw_request')
    @mock.patch('eidangservices.federator.server.task.get_temp_filepath')
    def test_split_multiple_without_overlap(self, mock_get_temp_filepath,
                                            mock_raw_request):
        # NOTE(damb): We do not care about stream epoch splitting. We simply
        # test the task's aligning facilities.
        mock_get_temp_filepath.return_value = self.path_tempfile
        mock_raw_request.side_effect = [
            HTTP413(),
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:59.201Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":175,"max_gap":null,"max_overlap":175,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":352,"start_time":"2018-01-03T00:00:00.000Z","end_time":"2018-01-04T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-11T10:16:43.104Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":0,"max_gap":null,"max_overlap":0,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":320,"start_time":"2018-01-04T00:00:00.000Z","end_time":"2018-01-05T00:00:00.000Z","format":"miniSEED","quality":"D"}]')] # noqa

        reference_result = json.loads(
            '[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:59.201Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":175,"max_gap":null,"max_overlap":175,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":352,"start_time":"2018-01-03T00:00:00.000Z","end_time":"2018-01-04T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-11T10:16:43.104Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":0,"max_gap":null,"max_overlap":0,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":320,"start_time":"2018-01-04T00:00:00.000Z","end_time":"2018-01-05T00:00:00.000Z","format":"miniSEED","quality":"D"}]') # noqa

        stream_epoch_orig = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 5))

        result = WFCatalogSplitAndAlignTask(self.url, stream_epoch_orig,
                                            self.query_params)()
        data = None
        with open(result.data, 'rb') as ifd:
            data = json.loads(ifd.read().decode('utf-8'))

        self.assertEqual(data, reference_result)
        mock_raw_request.has_calls()

    # test_split_multiple_without_overlap ()

    @mock.patch('eidangservices.federator.server.task.raw_request')
    @mock.patch('eidangservices.federator.server.task.get_temp_filepath')
    def test_split_multiple_with_overlap(self, mock_get_temp_filepath,
                                         mock_raw_request):
        # NOTE(damb): We do not care about stream epoch splitting. We simply
        # test the task's aligning facilities.
        mock_get_temp_filepath.return_value = self.path_tempfile
        mock_raw_request.side_effect = [
            HTTP413(),
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"}]'), # noqa
            io.BytesIO(b'[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:59.201Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":175,"max_gap":null,"max_overlap":175,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":352,"start_time":"2018-01-03T00:00:00.000Z","end_time":"2018-01-04T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-11T10:16:43.104Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":0,"max_gap":null,"max_overlap":0,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":320,"start_time":"2018-01-04T00:00:00.000Z","end_time":"2018-01-05T00:00:00.000Z","format":"miniSEED","quality":"D"}]')] # noqa

        reference_result = json.loads(
            '[{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:25.563Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":161,"max_gap":null,"max_overlap":161,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":313,"start_time":"2018-01-01T00:00:00.000Z","end_time":"2018-01-02T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:43.021Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":2,"sum_gaps":0,"sum_overlaps":251,"max_gap":null,"max_overlap":251,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":301,"start_time":"2018-01-02T00:00:00.000Z","end_time":"2018-01-03T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-10T18:19:59.201Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":175,"max_gap":null,"max_overlap":175,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":352,"start_time":"2018-01-03T00:00:00.000Z","end_time":"2018-01-04T00:00:00.000Z","format":"miniSEED","quality":"D"},{"version":"1.0.0","producer":{"name":"SED","agent":"ObsPy mSEED-QC","created":"2018-01-11T10:16:43.104Z"},"station":"DAVOX","network":"CH","location":"","channel":"LHZ","num_gaps":0,"num_overlaps":1,"sum_gaps":0,"sum_overlaps":0,"max_gap":null,"max_overlap":0,"record_length":[512],"sample_rate":[1],"percent_availability":100,"encoding":["STEIM2"],"num_records":320,"start_time":"2018-01-04T00:00:00.000Z","end_time":"2018-01-05T00:00:00.000Z","format":"miniSEED","quality":"D"}]') # noqa

        stream_epoch_orig = StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 5))

        result = WFCatalogSplitAndAlignTask(self.url, stream_epoch_orig,
                                            self.query_params)()
        data = None
        with open(result.data, 'rb') as ifd:
            data = json.loads(ifd.read().decode('utf-8'))

        self.assertEqual(data, reference_result)
        mock_raw_request.has_calls()

    # test_split_multiple_with_overlap ()

# class WFCatalogSplitAndAlignTask


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()

# ---- END OF <task.py> ----
