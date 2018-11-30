"""
Copyright (C) 2015 - 2017 Martin Kauss (yo@bishoph.org)

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import unittest
import sopare.config
from sopare.filter import Filtering


class FilterTest(unittest.TestCase):
    def test_filter_n_shift(self):
        chunks = 10
        cfg = sopare.config.Config()
        cfg.setoption('stream', 'CHUNKS', '10')
        filtering = Filtering(cfg)
        data_object_array = [v for v in range(0, 40)]
        for x in range(0, len(data_object_array), chunks):
            data_object = data_object_array[x:x + chunks]
            filtering.n_shift(data_object)
            if x == 0:
                filtering.first = False
            else:
                correct_object = data_object_array[x - chunks // 2:x + chunks // 2]
                self.assertSequenceEqual(filtering.data_shift, correct_object,
                                         'test_filter_n_shift 0 failed!')
        filtering.stop()
