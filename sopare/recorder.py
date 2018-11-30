"""
Copyright (C) 2015 - 2018 Martin Kauss (yo@bishoph.org)

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
import logging
import numpy
import time
import sys
import io
import sopare.audiofactory
import sopare.buffering
import sopare.visual


class Recorder:
    def __init__(self, cfg):
        self.cfg = cfg
        self.audio_factory = sopare.audiofactory.AudioFactory(cfg)
        self.queue = multiprocessing.JoinableQueue()
        self.running = True
        self.visual = sopare.visual.Visual()
        self.logger = self.cfg.getlogger().get_log()
        self.logger = logging.getLogger(__name__)
        self.buffering = sopare.buffering.Buffering(self.cfg, self.queue)

        if self.cfg.getoption('cmdlopt', 'infile') is None:
            self.recording()
        else:
            self.read_from_file()

    def debug_info(self):
        self.logger.debug('SAMPLE_RATE: ' + str(self.cfg.getintoption('stream', 'SAMPLE_RATE')))
        self.logger.debug('CHUNK: ' + str(self.cfg.getintoption('stream', 'CHUNK')))

    def read_from_file(self):
        self.debug_info()
        self.logger.info("* reading file " + self.cfg.getoption('cmdlopt', 'infile'))
        file = io.open(self.cfg.getoption('cmdlopt', 'infile'), 'rb',
                       buffering=self.cfg.getintoption('stream', 'CHUNK'))
        while True:
            buf = file.read(self.cfg.getintoption('stream', 'CHUNK') * 2)
            if buf:
                self.queue.put(buf)
                if self.cfg.getbool('cmdlopt', 'plot') is True:
                    data = numpy.fromstring(buf, dtype=numpy.int16)
                    self.visual.extend_plot_cache(data)
            else:
                self.queue.close()
                break
        file.close()
        once = False

        if self.cfg.getbool('cmdlopt', 'plot') is True:
            self.visual.create_sample(self.visual.get_plot_cache(), 'sample.png')

        while self.queue.qsize() > 0:
            if once is False:
                self.logger.debug('waiting for queue to finish...')
                once = True
            time.sleep(.1)  # wait for all threads to finish their work
        self.queue.close()
        self.buffering.flush('end of file')
        self.logger.info("* done ")
        self.stop()
        sys.exit()

    def recording(self):
        chunk = self.cfg.getintoption('stream', 'CHUNK')
        stream = self.audio_factory.open(self.cfg.getintoption('stream', 'SAMPLE_RATE'))
        self.debug_info()
        self.logger.info('start endless recording')

        while self.running:
            try:
                if self.buffering.is_alive():
                    buf = stream.read(chunk)
                    self.queue.put(buf)
                else:
                    self.logger.info('Buffering not alive, stop recording')
                    self.queue.close()
                    break
            except IOError as exc:
                self.logger.warning('error reading from stream', exc_info=exc)

        self.stop()
        sys.exit()

    def stop(self):
        self.logger.info("stop endless recording")
        self.running = False
        try:
            self.queue.join_thread()
            self.buffering.terminate()
        # FIXME should except specific exceptions. The way it is it even handles SyntaxError
        except:  # noqa: E722
            pass
        self.audio_factory.close()
        self.audio_factory.terminate()
