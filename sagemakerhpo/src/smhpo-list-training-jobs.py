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
This effectively calls
aws sagemakerhpo list-training-jobs-for-tuning-job
"""
import argparse
import json
import os

from smhpolib import get_smhpo_client
from smhpolib import serialize_helper

def get_parser():
    # --help text taken from docstring at top of file.
    parser = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.RawTextHelpFormatter)
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
    result = smhpo_client.list_training_jobs_for_tuning_job(TuningJobName=opts.tuning_job_name, 
        MaxResults=100)
    print(json.dumps(result, indent=2, sort_keys=True, default=serialize_helper))


if __name__ == "__main__":
    opts = get_parser().parse_args()
    main(opts)


