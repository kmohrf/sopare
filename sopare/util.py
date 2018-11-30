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


import datetime
import json
import os
import uuid
import wave

import numpy
from scipy.io.wavfile import write

import sopare.characteristics
import sopare.numpyjsonencoder
from sopare.path import __wavedestination__


class Util:
    def __init__(self, debug, peak_factor):
        self.debug = debug
        self.characteristic = sopare.characteristics.Characteristic(peak_factor)
        self.cache = {}

    def show_dict_entries_by_id(self):
        json_data = self.get_dict()
        for dict_entries in json_data['dict']:
            print((dict_entries['id'] + ' ' + dict_entries['uuid']))

    def show_dict_entry(self, sid):
        json_data = self.get_dict()
        ids = []
        for dict_entries in json_data['dict']:
            if (dict_entries['id'] == sid or sid == '*') and dict_entries['id'] not in ids:
                print((dict_entries['id'] + ' - ' + dict_entries['uuid']))
                for i, entry in enumerate(dict_entries['characteristic']):
                    output = str(entry['norm'])
                    print((str(i) + ', ' + str(entry['fc']) + ', ' + output[1:len(output) - 1]))

    @staticmethod
    def compile_analysis(json_data):
        analysis = {}
        for dict_entries in json_data['dict']:
            if dict_entries['id'] not in analysis:
                analysis[dict_entries['id']] = {
                    'min_tokens': 0, 'max_tokens': 0, 'peaks': [],
                    'df': [], 'minp': [], 'maxp': [], 'cp': [],
                    'mincp': [], 'maxcp': []}
            length = len(dict_entries['characteristic'])

            if length < 2:
                print('the following characteristic is < 2!')
                print((dict_entries['id'] + ', ' + dict_entries['uuid']))

            if length > analysis[dict_entries['id']]['max_tokens']:
                analysis[dict_entries['id']]['max_tokens'] = length

            if (length < analysis[dict_entries['id']]['min_tokens'] or
                    analysis[dict_entries['id']]['min_tokens'] == 0):
                analysis[dict_entries['id']]['min_tokens'] = length

            for i, entry in enumerate(dict_entries['characteristic']):
                if i == len(analysis[dict_entries['id']]['cp']):
                    analysis[dict_entries['id']]['cp'].append([len(entry['peaks'])])
                else:
                    peak_length = len(entry['peaks'])
                    if peak_length not in analysis[dict_entries['id']]['cp'][i]:
                        analysis[dict_entries['id']]['cp'][i].append(peak_length)

                if i == len(analysis[dict_entries['id']]['peaks']):
                    analysis[dict_entries['id']]['peaks'].append(entry['peaks'])
                else:
                    for miss in entry['peaks']:
                        if miss not in analysis[dict_entries['id']]['peaks'][i]:
                            analysis[dict_entries['id']]['peaks'][i].append(miss)
                    op = sorted(analysis[dict_entries['id']]['peaks'][i])
                    analysis[dict_entries['id']]['peaks'][i] = op

                if i == len(analysis[dict_entries['id']]['df']):
                    analysis[dict_entries['id']]['df'].append([])

                if entry['df'] not in analysis[dict_entries['id']]['df'][i]:
                    analysis[dict_entries['id']]['df'][i].append(entry['df'])
                    op = sorted(analysis[dict_entries['id']]['df'][i])
                    analysis[dict_entries['id']]['df'][i] = op

        for id in analysis:
            for p in analysis[id]['peaks']:
                if len(p) > 0:
                    analysis[id]['minp'].append(min(p))
                else:
                    analysis[id]['minp'].append(0)

                if len(p) > 0:
                    analysis[id]['maxp'].append(max(p))
                else:
                    analysis[id]['maxp'].append(0)

            for cp in analysis[id]['cp']:
                analysis[id]['mincp'].append(min(cp))
                analysis[id]['maxcp'].append(max(cp))
        return analysis

    @staticmethod
    def store_raw_dict_entry(dict_id, raw_characteristics):
        target_path = os.path.join('dict', '{}.raw'.format(str(uuid.uuid4())))
        json_obj = {
            'id': dict_id,
            'characteristic': raw_characteristics,
            'created': datetime.datetime.now().isoformat()}
        with open(target_path, mode='w') as json_file:
            json.dump(json_obj, json_file, cls=sopare.numpyjsonencoder.NumpyJSONEncoder)

    def learn_dict(self, characteristics, word_tendency, id):
        dict_model = self.prepare_dict_model(characteristics)
        self.add2dict(dict_model, word_tendency, id)

    @staticmethod
    def prepare_dict_model(characteristics):
        tokens = []
        for o in characteristics:
            characteristic, meta = o
            for m in meta:
                token = m['token']
                if token != 'stop':
                    if characteristic is not None:
                        tokens.append(characteristic)
                    if token == 'start analysis':
                        break
        return tokens

    def add2dict(self, obj, word_tendency, id):
        json_obj = self.get_dict()
        json_obj['dict'].append({
            'id': id,
            'characteristic': obj,
            'word_tendency': word_tendency,
            'uuid': str(uuid.uuid4())})
        self.write_dict(json_obj)
        return json_obj

    @staticmethod
    def write_dict(json_data):
        with open(os.path.join('dict', 'dict.json'), 'w') as json_file:
            json.dump(json_data, json_file, cls=sopare.numpyjsonencoder.NumpyJSONEncoder)

    @staticmethod
    def get_dict(filename="dict/dict.json"):
        with open(filename) as json_file:
            return json.load(json_file, object_hook=sopare.numpyjsonencoder.numpy_json_hook)

    def get_compiled_dict(self):
        compiled_dict = {'dict': []}
        for filename in os.listdir('dict'):
            if filename.endswith('.raw'):
                fu = filename.split('.')
                file_uuid = fu[0]
                tokens = []
                with open(os.path.join('dict', filename)) as raw_json_file:
                    json_obj = json.load(raw_json_file,
                                         object_hook=sopare.numpyjsonencoder.numpy_json_hook)
                    for raw_obj in json_obj['characteristic']:
                        meta = raw_obj['meta']
                        fft = raw_obj['fft']
                        norm = raw_obj['norm']
                        characteristic = self.characteristic.get_characteristic(fft, norm, meta)
                        if characteristic is not None:
                            for m in meta:
                                if m['token'] != 'stop':
                                    tokens.append(characteristic)
                    if len(tokens) > 0:
                        self.add_weighting(tokens)
                        compiled_dict['dict'].append({
                            'id': json_obj['id'],
                            'characteristic': tokens,
                            'uuid': file_uuid})
                    else:
                        print((json_obj['id'] + ' ' + file_uuid + ' got no tokens!'))
                raw_json_file.close()
        return compiled_dict

    @staticmethod
    def add_weighting(tokens):
        high = 0
        for token in tokens:
            cs = sum(token['token_peaks']) / 1000.0
            if cs > high:
                high = cs
        for token in tokens:
            token['weighting'] = sum(token['token_peaks']) / 1000.0 / high

    def delete_from_dict(self, id):
        json_obj = self.get_dict()
        new_dict = {'dict': []}
        if id != '*':
            dict_objects = json_obj['dict']
            for do in dict_objects:
                if do['id'] != id:
                    new_dict['dict'].append(do)
        self.write_dict(new_dict)

    def recreate_dict_from_raw_files(self):
        self.write_dict(self.get_compiled_dict())

    @staticmethod
    def save_raw_wave(filename, start, end, raw):
        wf = wave.open(__wavedestination__ + filename + '.wav', 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        data = raw[start:end]
        wf.writeframes(b''.join(data))

    @staticmethod
    def save_filtered_wave(filename, buffer):
        scaled = numpy.int16(buffer / numpy.max(numpy.abs(buffer)) * 32767)
        write(__wavedestination__ + filename + '.wav', 44100, scaled)

    @staticmethod
    def manhattan_distance(arr1, arr2):
        ll = int(max(len(arr1), len(arr2)) / 2)
        mdl = sum(abs(e - s) for s, e in zip(arr1[0:ll], arr2[0:ll]))
        mdr = sum(abs(e - s) for s, e in zip(arr1[ll:], arr2[ll:]))
        return mdl, mdr

    def similarity(self, a, b):
        len_a = len(a)
        len_b = len(b)
        a = numpy.array(a)
        a = numpy.array(a / 1000.0)
        b_id = id(b)
        if b_id not in self.cache:
            b = numpy.array(b)
            b = numpy.array(b / 1000.0)
            self.cache[b_id] = b
        else:
            b = self.cache[b_id]
        if len_a < len_b:
            a = numpy.resize(a, len_b)
            a[len_a:len_b] = 0
        elif len_b < len_a:
            b = numpy.resize(b, len_a)
            b[len_b:len_a] = 0
        np = (numpy.linalg.norm(a) * numpy.linalg.norm(b))
        if np > 0:
            return numpy.dot(a, b) / np
        else:
            return 0

    @staticmethod
    def single_similarity(a, b):
        if a == 0 and b == 0:
            return 1
        elif a == 0 or b == 0:
            return 0
        elif a < b:
            return float(a) / float(b)
        return float(b) / float(a)
