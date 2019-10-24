# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <sncl.py>
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
# REVISION AND CHANGES
# 2018/01/16        V0.1    Daniel Armbruster
#
# =============================================================================
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

    # test_modify_with_temporal_constraints_central_win ()

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

    # test_modify_with_temporal_constraints_slice_wins ()

    def test_modify_with_temporal_constraints_no_startend(self):
        reference_result = self.stream_epochs
        ses_handler = sncl.StreamEpochsHandler(self.stream_epochs)
        ses_handler.modify_with_temporal_constraints()
        self.assertEqual(list(ses_handler), reference_result)

    # test_modify_with_temporal_constraints_no_startend ()

# class StreamEpochsHandlerTestCase


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

    # test_slice_with_endtime ()

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

    # test_slice_with_endtime_default ()

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

    # test_slice_with_num ()

# class StreamEpochTestCase


# -----------------------------------------------------------------------------
if __name__ == '__main__': # noqa
    unittest.main()

# ---- END OF <sncl.py> ----
