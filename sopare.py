#!/usr/bin/env python3

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

import sys
import getopt
import sopare.config as config
import sopare.util as util
import sopare.recorder as recorder
import sopare.log as log
from sopare.version import __version__


def main(argv):
    endless_loop = False
    debug = False
    outfile = None
    infile = None
    dict = None
    plot = False
    wave = False
    error = False
    cfg_ini = None

    recreate = False

    print(('sopare ' + __version__))

    if len(argv) > 0:
        try:
            opts, args = getopt.getopt(argv, "ahelpv~cous:w:r:t:d:i:",
                                       ["analysis", "help", "error", "loop", "plot", "verbose",
                                        "wave", "create", "overview", "unit",
                                        "show=", "write=", "read=", "train=", "delete=", "ini="
                                        ])
        except getopt.GetoptError:
            usage()
            sys.exit(2)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit(0)
            if opt in ("-e", "--error"):
                error = True
            if opt in ("-l", "--loop"):
                endless_loop = True
            if opt in ("-p", "--plot"):
                if endless_loop is False:
                    plot = True
                else:
                    print("Plotting only works without loop option!")
                    sys.exit(0)
            if opt in ("-v", "--verbose"):
                debug = True
            if opt in ("-~", "--wave"):
                wave = True
            if opt in ("-c", "--create"):
                recreate = True
            if opt in ("-o", "--overview"):
                show_dict_ids(debug)
                sys.exit(0)
            if opt in ("-a", "--analysis"):
                show_dict_analysis(debug)
                sys.exit(0)
            if opt in ("-s", "--show"):
                show_word_entries(arg, debug)
                sys.exit(0)
            if opt in ("-w", "--write"):
                outfile = arg
            if opt in ("-r", "--read"):
                infile = arg
            if opt in ("-t", "--train"):
                dict = arg
            if opt in ("-d", "--delete"):
                delete_word(arg, debug)
                sys.exit(0)
            if opt in ("-i", "--ini"):
                cfg_ini = arg

    cfg = create_config(cfg_ini, endless_loop, debug, plot, wave, outfile, infile, dict, error)

    if recreate is True:
        recreate_dict(debug, cfg)
        sys.exit(0)

    recorder.Recorder(cfg)


def create_config(cfg_ini, endless_loop, debug, plot, wave, outfile, infile, dict, error):
    if cfg_ini is None:
        cfg = config.Config()
    else:
        cfg = config.Config(cfg_ini)
    logger = log.Log(debug, error, cfg)
    cfg.addsection('cmdlopt')
    cfg.setoption('cmdlopt', 'endless_loop', str(endless_loop))
    cfg.setoption('cmdlopt', 'debug', str(debug))
    cfg.setoption('cmdlopt', 'plot', str(plot))
    cfg.setoption('cmdlopt', 'wave', str(wave))
    cfg.setoption('cmdlopt', 'outfile', outfile)
    cfg.setoption('cmdlopt', 'infile', infile)
    cfg.setoption('cmdlopt', 'dict', dict)
    cfg.addlogger(logger)
    return cfg


def recreate_dict(debug, cfg):
    print("recreating dictionary from raw input files...")
    utilities = util.Util(debug, cfg.getfloatoption('characteristic', 'PEAK_FACTOR'))
    utilities.recreate_dict_from_raw_files()


def delete_word(dict, debug):
    if dict != "*":
        print(("deleting " + dict + " from dictionary"))
    else:
        print("deleting all enttries from dictionary")
    utilities = util.Util(debug, None)
    utilities.delete_from_dict(dict)


def show_word_entries(dict, debug):
    print((dict + " entries in dictionary:"))
    print()
    utilities = util.Util(debug, None)
    utilities.show_dict_entry(dict)


def show_dict_ids(debug):
    print("current entries in dictionary:")
    utilities = util.Util(debug, None)
    utilities.show_dict_entries_by_id()


def show_dict_analysis(debug):
    print("dictionary analysis:")
    utilities = util.Util(debug, None)
    analysis = utilities.compile_analysis(utilities.get_dict())
    for _id in analysis:
        print(_id)
        for k, v in analysis[_id].items():
            print((' ' + str(k) + ' ' + str(v)))


def usage():
    print("usage:")
    print(" -h --help           : this help")
    print(" -l --loop           : loop forever")
    print(" -e --error          : redirect sdterr to error.log")
    print(" -p --plot           : plot results (only without loop option)")
    print(" -v --verbose        : enable verbose mode")
    print(" -~ --wave           : create *.wav files (token/tokenN.wav) for")
    print("                       each detected word")
    print(" -c --create         : create dict from raw input files")
    print(" -o --overview       : list all dict entries")
    print(" -s --show   [word]  : show detailed [word] entry information")
    print("                       '*' shows all entries!")
    print(" -w --write  [file]  : write raw to [dir/filename]")
    print(" -r --read   [file]  : read raw from [dir/filename]")
    print(" -t --train  [word]  : add raw data to raw dictionary file")
    print(" -d --delete [word]  : delete [word] from dictionary and exits.")
    print("                       '*' deletes everything!")
    print(" -i --ini    [file]  : use alternative configuration file")
    print(" -a --analysis       : show dictionary analysis and exits.")


main(sys.argv[1:])
