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

import base64
import json
import numpy


class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            if obj.flags['C_CONTIGUOUS']:
                obj_data = obj.data
            else:
                cont_obj = numpy.ascontiguousarray(obj)
                if cont_obj.flags['C_CONTIGUOUS']:
                    obj_data = cont_obj.data
                else:
                    raise Exception('numpyjsonencoder err: C_CONTIGUOUS not present in object!')
            data_base64 = base64.b64encode(obj_data).decode()
            return dict(__ndarray__=data_base64, dtype=str(obj.dtype), shape=obj.shape)
        if hasattr(obj, '__class__') and issubclass(obj.__class__, numpy.integer):
            obj_type = obj.__class__.__name__.rsplit('.', 1)[0]
            return dict(__numpy_integer__=obj_type, value=int(obj))
        return json.JSONEncoder.default(self, obj)


def numpy_json_hook(obj):
    if isinstance(obj, dict) and '__ndarray__' in obj:
        data = base64.b64decode(obj['__ndarray__'].encode())
        return numpy.frombuffer(data, obj['dtype']).reshape(obj['shape'])
    if isinstance(obj, dict) and '__numpy_integer__' in obj:
        obj_type = getattr(numpy, obj['__numpy_integer__'])
        return obj_type(obj['value'])
    return obj
