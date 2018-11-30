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
import sopare.worker
import sopare.characteristics


class Filtering:
    def __init__(self, cfg):
        self.cfg = cfg
        self.first = True
        self.queue = multiprocessing.Queue()
        self.characteristic = sopare.characteristics.Characteristic(
            self.cfg.getfloatoption('characteristic', 'PEAK_FACTOR'))
        self.worker = sopare.worker.Worker(self.cfg, self.queue)
        self.data_shift = []
        self.last_data = None
        self.data_shift_counter = 0
        self.logger = self.cfg.getlogger().get_log()
        self.logger = logging.getLogger(__name__)

    def stop(self):
        self.queue.put({'action': 'stop'})
        self.queue.close()
        self.queue.join_thread()

    def reset(self):
        self.queue.put({'action': 'reset'})

    @staticmethod
    def check_for_windowing(meta):
        for m in meta:
            if m['token'] == 'start analysis' or m['token'] == 'silence':
                return True
        return False

    def get_chunked_norm(self, nfft):
        chunked_norm = []
        progessive = 1
        min_prog_step = self.cfg.getintoption('characteristic', 'MIN_PROGRESSIVE_STEP')
        max_prog_step = self.cfg.getintoption('characteristic', 'MAX_PROGRESSIVE_STEP')
        start_prog_factor = self.cfg.getfloatoption('characteristic', 'START_PROGRESSIVE_FACTOR',
                                                    fallback=None)
        for x in range(0, nfft.size, min_prog_step):
            if start_prog_factor is not None and x >= start_prog_factor:
                progessive += progessive * start_prog_factor
                min_prog_step += int(progessive)
                if min_prog_step > max_prog_step:
                    min_prog_step = max_prog_step
            chunked_norm.append(nfft[x:x + min_prog_step].sum())

        return numpy.array(chunked_norm)

    @staticmethod
    def normalize(fft):
        norm = numpy.linalg.norm(fft)
        if norm > 0:
            return (fft / norm).tolist()
        return []

    def n_shift(self, data):
        if self.first is True:
            self.data_shift = []
            self.data_shift_counter = 0
        if self.data_shift_counter == 0:
            self.data_shift = [v for v in range(0, self.cfg.getintoption('stream', 'CHUNKS') // 2)]
            self.data_shift.extend(data[len(data) // 2:])
        elif self.data_shift_counter == 1:
            self.data_shift = self.data_shift[len(self.data_shift) // 2:]
            self.data_shift.extend(data[0:len(data) // 2])
        else:
            self.data_shift = self.last_data[len(self.last_data) // 2:]
            self.data_shift.extend(data[0:len(data) // 2])

        self.last_data = data
        self.data_shift_counter += 1

    def filter(self, data, meta):
        self.n_shift(data)
        shift_fft = None
        chunks = self.cfg.getintoption('stream', 'CHUNKS')

        if (self.first is False or
                self.cfg.getbool('characteristic', 'HANNING') is False or
                len(data) < chunks):
            fft = numpy.fft.rfft(data)
            if len(self.data_shift) >= chunks:
                shift_fft = numpy.fft.rfft(self.data_shift)
            self.first = self.check_for_windowing(meta)
        elif self.first is True:
            self.logger.debug('New window!')
            hl = len(data)
            if hl % 2 != 0:
                hl += 1
            hw = numpy.hanning(hl)
            fft = numpy.fft.rfft(data * hw)
            if len(self.data_shift) >= chunks:
                hl = len(self.data_shift)
                if hl % 2 != 0:
                    hl += 1
                hw = numpy.hanning(hl)
                shift_fft = numpy.fft.rfft(self.data_shift * hw)
                self.first = False

        # FIXME: fft may not be set
        fft[self.cfg.getintoption('characteristic', 'HIGH_FREQ'):] = 0
        fft[:self.cfg.getintoption('characteristic', 'LOW_FREQ')] = 0
        data = numpy.fft.irfft(fft)
        nfft = fft[self.cfg.getintoption('characteristic', 'LOW_FREQ'):self.cfg.getintoption(
            'characteristic', 'HIGH_FREQ')]
        nfft = numpy.abs(nfft)
        nfft[nfft == 0] = numpy.NaN
        nfft = numpy.log10(nfft) ** 2
        nfft[numpy.isnan(nfft)] = 0
        nam = numpy.amax(nfft)
        normalized = [0]

        if nam > 0:
            nfft = numpy.tanh(nfft / nam)
            chunked_norm = self.get_chunked_norm(nfft)
            normalized = self.normalize(chunked_norm)
        characteristic = self.characteristic.get_characteristic(fft, normalized, meta)

        experimental_fft_shift = self.cfg.getbool('experimental', 'FFT_SHIFT', fallback=False)
        if shift_fft is not None and experimental_fft_shift is True:
            shift_fft[self.cfg.getintoption('characteristic', 'HIGH_FREQ'):] = 0
            shift_fft[:self.cfg.getintoption('characteristic', 'LOW_FREQ')] = 0
            # FIXME shift_data is never used and shift_nfft immediately overwriten
            shift_data = numpy.fft.irfft(shift_fft)  # noqa: F841
            shift_nfft = fft[
                         self.cfg.getintoption('characteristic', 'LOW_FREQ'):self.cfg.getintoption(
                             'characteristic', 'HIGH_FREQ')]
            shift_nfft = numpy.abs(nfft)
            shift_nfft[nfft == 0] = numpy.NaN
            shift_nfft = numpy.log10(nfft) ** 2
            shift_nfft[numpy.isnan(shift_nfft)] = 0
            shift_nam = numpy.amax(shift_nfft)
            shift_normalized = [0]

            if shift_nam > 0:
                shift_nfft = numpy.tanh(shift_nfft / shift_nam)
                shift_chunked_norm = self.get_chunked_norm(shift_nfft)
                shift_normalized = self.normalize(shift_chunked_norm)
            # TODO: Do some shift meta magic!
            shift_characteristic = self.characteristic.get_characteristic(shift_fft,
                                                                          shift_normalized, meta)
            characteristic['shift'] = shift_characteristic

        self.queue.put({
            'action': 'data',
            'token': data,
            'fft': fft,
            'norm': normalized,
            'meta': meta,
            'characteristic': characteristic
        })
