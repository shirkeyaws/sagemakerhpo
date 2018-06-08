#!/usr/bin/env python3
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


"""
Simple utility to launch a TuningJob from a JSON request definition.
"""
import argparse
import json
import os
import sys

from smhpolib.client import get_smhpo_client

def get_parser():
    # --help text taken from docstring at top of file.
    parser = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-j","--request-json",
            help="JSON file with CreateTuningJobRequest",
            type=str,
            required=True)
    parser.add_argument("-n","--tuning-job-name",
            help="Tuning job name",
            type=str,
            required=True)
    parser.add_argument("--aws-region",
                        help="AWS region",
                        type=str,
                        required=False)

    return parser


def main(opts):
    if opts.aws_region:
        os.environ["AWS_REGION"] = opts.aws_region

    smhpo_client = get_smhpo_client()
    request = json.load(open(opts.request_json))
    request['TuningJobName'] = opts.tuning_job_name
    result = smhpo_client.create_tuning_job(**request)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    opts = get_parser().parse_args()
    main(opts)


