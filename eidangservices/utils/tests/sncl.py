# -*- coding: utf-8 -*-
"""
EIDA NG webservices sncl module test facilities.
"""

import datetime
import unittest

from eidangservices.utils import sncl


# -----------------------------------------------------------------------------
class StreamEpochsHandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.stream_epochs = [sncl.StreamEpochs(
            network='GR',
            station='BFO',
            location='',
            channel='LHZ',
            epochs=[(datetime.datetime(2018, 1, 1),
                     datetime.datetime(2018, 1, 7)),
                    (datetime.datetime(2018, 1, 14),
                     datetime.datetime(2018, 1, 15)),
                    (datetime.datetime(2018, 1, 20),
                     datetime.datetime(2018, 1, 27))])]

    def tearDown(self):
        self.stream_epochs = None

    def test_modify_with_temporal_constraints_central_win(self):
        reference_result = [sncl.StreamEpochs(
            network='GR',
            station='BFO',
            location='',
            channel='LHZ',
            epochs=[(datetime.datetime(2018, 1, 14),
                     datetime.datetime(2018, 1, 15))])]

        ses_handler = sncl.StreamEpochsHandler(self.stream_epochs)
        ses_handler.modify_with_temporal_constraints(
            datetime.datetime(2018, 1, 13),
            datetime.datetime(2018, 1, 16))
        self.assertEqual(list(ses_handler), reference_result)

    def test_modify_with_temporal_constraints_slice_wins(self):
        start = datetime.datetime(2018, 1, 2)
        end = datetime.datetime(2018, 1, 21)

        reference_result = [sncl.StreamEpochs(
            network='GR',
            station='BFO',
            location='',
            channel='LHZ',
            epochs=[(start, datetime.datetime(2018, 1, 7)),
                    (datetime.datetime(2018, 1, 14),
                     datetime.datetime(2018, 1, 15)),
                    (datetime.datetime(2018, 1, 20), end)])]

        ses_handler = sncl.StreamEpochsHandler(self.stream_epochs)
        ses_handler.modify_with_temporal_constraints(start=start, end=end)
        self.assertEqual(list(ses_handler), reference_result)

    def test_modify_with_temporal_constraints_no_startend(self):
        reference_result = self.stream_epochs
        ses_handler = sncl.StreamEpochsHandler(self.stream_epochs)
        ses_handler.modify_with_temporal_constraints()
        self.assertEqual(list(ses_handler), reference_result)


class StreamEpochTestCase(unittest.TestCase):

    def setUp(self):
        self.stream = sncl.Stream(
            network='GR',
            station='BFO',
            location='',
            channel='LHZ')

    def tearDown(self):
        self.stream = None

    def test_slice_with_endtime(self):
        stream_epoch = sncl.StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 8))

        reference_result = [
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 1),
                endtime=datetime.datetime(2018, 1, 4, 12)),
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 4, 12),
                endtime=datetime.datetime(2018, 1, 8))]

        self.assertEqual(sorted(stream_epoch.slice(num=2)), reference_result)

    def test_slice_with_endtime_default(self):
        stream_epoch = sncl.StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=None)

        reference_result = [
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 1),
                endtime=datetime.datetime(2018, 1, 4, 12)),
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 4, 12),
                endtime=datetime.datetime(2018, 1, 8))]

        self.assertEqual(
            sorted(
                stream_epoch.slice(
                    num=2,
                    default_endtime=datetime.datetime(2018, 1, 8))),
            reference_result)

    def test_slice_with_num(self):
        stream_epoch = sncl.StreamEpoch(
            stream=self.stream,
            starttime=datetime.datetime(2018, 1, 1),
            endtime=datetime.datetime(2018, 1, 8))

        reference_result = [
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 1),
                endtime=datetime.datetime(2018, 1, 2, 18)),
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 2, 18),
                endtime=datetime.datetime(2018, 1, 4, 12)),
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 4, 12),
                endtime=datetime.datetime(2018, 1, 6, 6)),
            sncl.StreamEpoch(
                stream=self.stream,
                starttime=datetime.datetime(2018, 1, 6, 6),
                endtime=datetime.datetime(2018, 1, 8))]

        self.assertEqual(sorted(stream_epoch.slice(num=4)),
                         reference_result)


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
