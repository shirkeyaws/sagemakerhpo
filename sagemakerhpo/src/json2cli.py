#!/usr/bin/env python
# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Amazon Software License (the "License"). You may not
# use this file except in compliance with the License. A copy of the
# License is located at:
#    http://aws.amazon.com/asl/
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express
# or implied. See the License for the specific language governing permissions
# and limitations under the License.


"""Converts a .json file to command-line arguments.
e.g. {"epochs":"10"} as input converts to "--epochs 10"
"""

import argparse
import json
import sys
import traceback

def get_parser():
    # --help text taken from docstring at top of file.
    parser = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("filename",
            help="Name of .json file to convert",
            type=str)
    parser.add_argument("-eq", "--equals_delimiter",
            help="Use an equals between HP name and value instead of space",
            default=False,
            action='store_true')
    parser.add_argument("-ud","--underscore-dash",
            help="replace underscores with dash in hyperparam names",
            default=False,
            action='store_true')
    return parser

def parse_and_print(filename, opts):
    out = ""
    def map_name(hyperparam_name):
        if opts.underscore_dash:
            return hyperparam_name.replace("_","-")
        else:
            return hyperparam_name
    if opts.equals_delimiter:
        delimiter='='
    else:
        delimiter=' '
    with open(filename) as fh:
        config = json.load(fh)
        try:
            # Workaround for issues P8678765
            del config['TrainingJobName']  
        except KeyError:
            pass
        args = ["--%s%s%s"%(map_name(k),delimiter,v) for k,v in config.items()]
        outstr = " ".join(args)
        print(outstr)
            

def main():
    opts = get_parser().parse_args()
    filename = opts.filename
    try:
        parse_and_print(filename, opts)
    except Exception as e:
        print("--help # Error parsing JSON file %s: %s" % (filename, e))

if __name__ == "__main__":
    main()


