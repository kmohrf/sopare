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

import multiprocessing
import unittest
import audioop
import math
import time

import sopare.log
import sopare.config
import sopare.audiofactory

from . import util


class AudioTest(unittest.TestCase):
    SAMPLE_RATES = [8000, 11025, 12000, 16000, 22050, 32000, 44100, 48000]
    CHUNKS = [512, 1024, 2048, 4096, 8192]
    TEST_RESULTS = {}

    @classmethod
    def setUpClass(cls):
        cfg = sopare.config.Config()
        logger = sopare.log.Log(True, False)
        cfg.addlogger(logger)

        cls.audio_factory = sopare.audiofactory.AudioFactory(cfg)
        cls.queue = multiprocessing.JoinableQueue()
        cls.multi = util.Multi(cls.queue)

        cls.good_sample_rates = []
        cls.good_chunks = []
        cls.silence = []
        cls.stream = None

    @classmethod
    def tearDownClass(cls):
        while cls.queue.qsize() > 0:
            time.sleep(.1)  # wait for all threads to finish their work
        cls.queue.close()
        cls.multi.stop()
        cls.queue.join_thread()
        cls.audio_factory.close()
        cls.audio_factory.terminate()

    def read(self, chunks, loops):
        vol = 0
        try:
            for x in range(loops):
                buf = self.stream.read(chunks)
                self.queue.put(buf)
                current_vol = audioop.rms(buf, 2)
                if current_vol > vol:
                    vol = current_vol
            self.silence.append(vol)
            test_result = True
            print(('Excellent. Got all ' + str(chunks * loops) + ' chunks.'))
        except IOError as exc:
            test_result = False
            print(("Error: " + str(exc)))
        return test_result

    def test_environment(self):
        # FIXME: this should not be part of a unit test, because this can be implemented
        #        as a runtime check in the application runner
        self.assertGreaterEqual(multiprocessing.cpu_count(), 4,
                                'SOPARE requires a multiprocessor architecture and was '
                                'tested with at least 4 cores (e.g. RPi2/3)')

    def test_sample_rates(self):
        print('testing different SAMPLE_RATEs ... this may take a while!\n\n')
        for test_sample_rate in AudioTest.SAMPLE_RATES:
            self.stream = self.audio_factory.open(test_sample_rate)
            if self.stream is not None:
                self.good_sample_rates.append(test_sample_rate)
                self.audio_factory.close()

    def test_chunks(self):
        print('testing different CHUNK sizes ... this may take a while!\n\n')
        for good_sample_rate in self.good_sample_rates:
            for chunks in AudioTest.CHUNKS:
                self.stream = self.audio_factory.open(good_sample_rate)
                if self.stream is not None:
                    if good_sample_rate not in AudioTest.TEST_RESULTS:
                        AudioTest.TEST_RESULTS[good_sample_rate] = []
                    read_test_result = self.read(chunks, 10)
                    if read_test_result is True:
                        self.good_chunks.append(chunks)
                        AudioTest.TEST_RESULTS[good_sample_rate].append(chunks)
                self.audio_factory.close()

    def test_results(self):
        recommendations = {}
        found = False
        for sample_rate in AudioTest.TEST_RESULTS:
            if len(AudioTest.TEST_RESULTS[sample_rate]) > 0:
                recommendations[sample_rate] = len(AudioTest.TEST_RESULTS[sample_rate])
                found = True
        print('\n\n')
        if found is True:
            best = sorted(recommendations, key=recommendations.__getitem__, reverse=True)
            print('Your sopare/config.py recommendations:\n')
            print(('SAMPLE_RATE = ' + str(max(best))))
            print(('CHUNK = ' + str(min(AudioTest.TEST_RESULTS[best[0]]))))
            threshold = int(math.ceil(max(self.silence) / 100.0)) * 100
            print(('THRESHOLD = ' + str(threshold)))
        else:
            print('No recommendations, please fix your environment and try again!')
            print('However, here are the successful tested sample rates:')
            print((str(AudioTest.TEST_RESULTS)))
