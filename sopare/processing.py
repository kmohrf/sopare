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

import logging
import audioop
from . import prepare
import time
import io


class Processor:
    def __init__(self, cfg, buffering, live=True):
        self.append = False
        self.cfg = cfg
        self.out = None
        if self.cfg.getoption('cmdlopt', 'outfile') is not None:
            self.out = io.open(self.cfg.getoption('cmdlopt', 'outfile'), 'wb')
        self.buffering = buffering
        self.live = live
        self.timer = 0
        self.silence_timer = 0
        self.silence_buffer = []
        self.prepare = prepare.Preparing(self.cfg)
        self.logger = self.cfg.getlogger().get_log()
        self.logger = logging.getLogger(__name__)

    def stop(self, message):
        self.logger.info(message)
        if self.out is not None:
            self.out.close()
        self.append = False
        self.silence_timer = 0
        if self.cfg.getbool('cmdlopt', 'endless_loop') is False:
            self.prepare.stop()
        else:
            self.prepare.force_tokenizer()
        if self.buffering is not None:
            self.buffering.stop()

    def check_silence(self, buf):
        max_silence_after_start = self.cfg.getfloatoption('stream', 'MAX_SILENCE_AFTER_START')
        max_time = self.cfg.getfloatoption('stream', 'MAX_TIME')
        volume = audioop.rms(buf, 2)

        if volume >= self.cfg.getintoption('stream', 'THRESHOLD'):
            self.silence_timer = time.time()
            if self.append is False:
                self.logger.info('starting append mode')
                self.timer = time.time()
                for sbuf in self.silence_buffer:
                    self.prepare.prepare(sbuf, audioop.rms(sbuf, 2))
                self.silence_buffer = []
            self.append = True
        else:
            self.silence_buffer.append(buf)
            if len(self.silence_buffer) > 3:
                del self.silence_buffer[0]
        if self.out is not None and self.out.closed is False:
            self.out.write(buf)
        if self.append is True:
            self.prepare.prepare(buf, volume)
        if (self.append is True and self.silence_timer > 0 and
                self.silence_timer + max_silence_after_start < time.time() and
                self.live is True):
            self.stop('stop append mode because of silence')
        if self.append is True and self.timer + max_time < time.time() and self.live is True:
            self.stop("stop append mode because time is up")
