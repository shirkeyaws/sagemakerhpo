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
Downloads all the metrics for the training jobs associated with a tuning job.
Generates a set of .csv files  (one per training job) from all the 
metrics in CloudWatch.
"""
import argparse
import json
import os
import traceback

import smhpolib
from smhpolib.trainingcurve import CloudWatchMetricFetcher

def get_parser():
    # --help text taken from docstring at top of file.
    parser = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-n","--tuning-job-name",
            help="Tuning job name",
            type=str,
            required=True)
    parser.add_argument("-mj","--max-training-jobs",
            help="Maximum number of training jobs to capture metrics for",
            type=int,
            default=100)
    parser.add_argument("-od","--output-directory",
            help="directory for saving metrics files",
            type=str,
            default="metrics-data")
    parser.add_argument("-mf","--max-failures",
            help="maximum number of failures before quitting",
            type=int,
            default=5)
    parser.add_argument("--aws-region",
                        help="AWS region",
                        type=str,
                        required=False)
    return parser

def generate_output_filename(training_job_name, opts):
    if not os.path.exists(opts.output_directory):
        os.mkdir(opts.output_directory)
    return "%s/metrics_%s.csv" % (opts.output_directory, training_job_name)

def main(opts):
    if opts.aws_region:
        os.environ["AWS_REGION"] = opts.aws_region
    tuning_job = smhpolib.analysis.TuningJob(opts.tuning_job_name,
            max_training_jobs=opts.max_training_jobs)
    metric_names = tuning_job.metric_names()
    training_names = tuning_job.training_job_names()
    print("Fetching %d metrics each for %d training jobs" % (len(metric_names), len(training_names)))
    failure_cnt = 0
    for n, training_job_name in enumerate(training_names):
        try:
            filename = generate_output_filename(training_job_name, opts)
            fetcher = CloudWatchMetricFetcher()
            for metric_name in metric_names:
                fetcher.fetch_metric(training_job_name, metric_name)
            tcd = fetcher.training_curve_data()
            tcd.save_csv(filename)
            print("  %d) Saved %s with %d records" % ((n+1), filename, len(tcd)))
        except:
            failure_cnt += 1
            print("Failure #%d on training_job %s" % (failure_cnt,training_job_name))
            traceback.print_exc()
            if failure_cnt >= opts.max_failures:
                sys.exit(-1)


if __name__ == "__main__":
    opts = get_parser().parse_args()
    main(opts)

