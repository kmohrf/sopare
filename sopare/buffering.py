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
import sopare.processing


class Buffering(multiprocessing.Process):
    def __init__(self, cfg, queue):
        super().__init__(name='buffering queue')
        self.cfg = cfg
        self.queue = queue
        self.proc = sopare.processing.Processor(self.cfg, self)
        self.PROCESS_ROUND_DONE = False
        self.test_counter = 0
        self.logger = self.cfg.getlogger().get_log()
        self.logger = logging.getLogger(__name__)
        self.start()

    def run(self):
        self.logger.info('buffering queue runner')
        endless_loop = self.cfg.getbool('cmdlopt', 'endless_loop')
        outfile = self.cfg.getoption('cmdlopt', 'outfile')

        while True:
            buf = self.queue.get()
            if (endless_loop is False or outfile is not None) and self.PROCESS_ROUND_DONE:
                break
            self.proc.check_silence(buf)
        self.logger.info('terminating queue runner')

    def flush(self, message):
        self.proc.stop(message)

    def stop(self):
        self.logger.info('stop buffering')
        self.PROCESS_ROUND_DONE = True
