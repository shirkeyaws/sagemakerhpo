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
Base class for building launcher scripts.
Opinionated about how to form CreateTuningJob requests, but configurable.
"""

import argparse
import boto3
import botocore
import datetime
import json
import os
from string import Template
import sys
import time
import traceback
import uuid

from smhpolib.client import get_smhpo_client


class BaseLauncher(object):
    """TuningJob launcher helper. Can be sub-classed to be made more specific."""

    DEFAULT_HYPERPARAM_RANGES_FILE = "hp-ranges.json"

    INSTANCE_COUNT = 1

    def __init__(self):
        self.hyperparam_ranges = None  # Can set explicitly instead of loading from file.
        self.opts = self.default_opts()
        self.request_json = None

    def main(self):
        """This is the entry point for using this as a command-line utility.
        Parses options from sys.argv, creates a request, and launches unless --dry-run
        """
        self.opts = self.get_parser().parse_args()  # Parse from command-line args
        if self.opts.aws_region:
            os.environ["AWS_REGION"] = self.opts.aws_region
        self.create_tuning_job_request()
        if self.opts.verbose:
            print("Request JSON:\n%s" % json.dumps(self.request_json, indent=2, sort_keys=True))

        if self.opts.dryrun:
            print("Dry run only.  Not actually launching.")
        else:
            self.launch_tuning_job()

    def launch_tuning_job(self):
        if not self.request_json:
            self.create_tuning_job_request()
        request_json = self.request_json
        if 'UNSET_PARAMETER_WARNING' in json.dumps(request_json):
            raise ValueError("CreateTuningJob request contains unset parameters: %s" % request_json)
        smhpo = get_smhpo_client()
        response = smhpo.create_tuning_job(**self.request_json)
        print("Response: %s" % json.dumps(response, indent=2, sort_keys=True))
        print("Created Tuning job named %s" % self.request_json['TuningJobName'])
        print("Timestamp: %s" % str(datetime.datetime.now()))
        return response

    def get_jobname(self):
        name = self.opts.jobname
        if name is None:
            name = self.DEFAULT_NAME_PREFIX
        if self.opts.name_suffix.find('date') > -1:
            name += time.strftime("-%b%d-%H%M")
        if self.opts.name_suffix.find('rand') > -1:
            name += "-" + str(uuid.uuid4())[:5]
        if len(name) > 26:
            raise ValueError("TuningJob name can be at most 26 characters long. '%s' is too long" % name)
        return name

    def get_parser(self):
        # --help text taken from docstring at top of file.
        parser = argparse.ArgumentParser(description=self.__doc__,
                                         formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("-n", "--jobname",
                            help="Prefix for job name",
                            type=str,
                            default=None)
        parser.add_argument("-v", "--verbose",
                            help="verbose: Dump JSON request string",
                            default=False,
                            action="store_true")
        parser.add_argument("-dr", "--dryrun",
                            help="dry run only.  don't actually launch",
                            default=False,
                            action="store_true")
        parser.add_argument("-ns", "--name-suffix",
                            help="Kind of name suffix to auto-generate",
                            type=str,
                            default="date-rand",
                            choices=['none', 'date-rand', 'date', 'rand'])
        parser.add_argument("-pj", "--parallel_jobs",
                            help="How many parallel jobs to run at once",
                            default=3,
                            type=int)
        parser.add_argument("-in", "--input_data_url",
                            help="S3 location of input data",
                            default=self.DEFAULT_INPUT_DATA,
                            type=str)
        parser.add_argument("-out", "--output_data_url",
                            help="S3 location to put output",
                            default=self.DEFAULT_OUTPUT_LOCATION,
                            type=str)
        parser.add_argument("-r", "--hyperparam_ranges_file",
                            help="JSON (or YAML) file with hyperparameter ranges",
                            default=self.DEFAULT_HYPERPARAM_RANGES_FILE,
                            type=str)
        parser.add_argument("-tj", "--total_jobs",
                            help="Budget for total number of training jobs in this HPO search",
                            default=10,
                            type=int)
        parser.add_argument("--aws-region",
                            help="AWS region",
                            type=str,
                            required=False)
        return parser

    def default_opts(self):
        """Returns the default options if nothing is set.
        """
        parser = self.get_parser()
        opts = parser.parse_args([])
        return opts

    def get_tuning_job_config(self):
        return {
            "Strategy": "Bayesian",
            "TuningJobObjective": {
                "Type": self.OBJECTIVE_TYPE,
                "MetricName": self.OBJECTIVE_METRIC,
            },
            "ParameterRanges": self.get_hyperparameter_ranges(),
            "ResourceLimits": {
                "MaxParallelTrainingJobs": self.opts.parallel_jobs,
                "MaxNumberOfTrainingJobs": self.opts.total_jobs
            },
        }

    def get_metric_definitions(self):
        print("Error: incomplete base class.")
        print("You must configure the subclass to return a data structure defining")
        print("your metrics that looks like")
        metric_definitions = [
            {
                "Name": "loss",
                "Regex": "loss = ([0-9\\.]+)"
            },
            {
                "Name": "validation-precision",
                "Regex": "Validation-Precision: ([0-9\\.]+)"
            },
            {
                "Name": "epoch",
                "Regex": "Epoch ([0-9\\.]+)"
            }
        ]
        print(json.dumps(metric_definitions, indent=2))
        raise NotImplementedError()

    def clean_metric_definitions(self, metric_definition_list):
        """Automatically fixes case issue with earlier versions
        of CreateTuningJobRequest model
        """
        for md in metric_definition_list:

            if 'name' in md:
                md['Name'] = md['name']
                del md['name']
            if 'regex' in md:
                md['Regex'] = md['regex']
                del md['regex']
        return metric_definition_list

    def get_training_job_definition(self):
        result = {
            "RoleArn": self.TRAINING_ROLE,
            "OutputDataConfig": {
                "S3OutputPath": self.opts.output_data_url,
            },
            "ResourceConfig": {
                "VolumeSizeInGB": self.VOLUME_SIZE_IN_GB,
                "InstanceType": self.INSTANCE_TYPE,
                "InstanceCount": self.INSTANCE_COUNT,
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": self.MAX_RUNTIME_IN_HOURS * 3600,
            },
            "AlgorithmSpecification": {
                "TrainingImage": self.get_ecr_image(),
                "TrainingInputMode": "File",
                "MetricDefinitions": self.clean_metric_definitions(self.get_metric_definitions()),
            },
            "InputDataConfig": self.get_input_data_config(),
        }
        static_hp = self.get_static_hyperparameters()
        if static_hp:
            result["StaticHyperParameters"] = static_hp
        return result

    def get_static_hyperparameters(self):
        """By default, it looks in the hyper-parameter ranges file for a key
        called "StaticHyperParameters"
        """
        return self.get_static_hyperparmaeters_from_ranges_files()

    def get_input_data_config(self):
        return [
            {
                "ChannelName": "all",
                "CompressionType": "None",
                "DataSource": {
                    "S3DataSource": {
                        "S3Uri": self.opts.input_data_url,
                        "S3DataType": "S3Prefix",
                        "S3DataDistributionType": "FullyReplicated"
                    }
                },
            }
        ]

    def correct_instance_type(self, request):
        """Make sure the instance type is prefixed with "ml."
        """
        instance_type = request['TrainingJobDefinition']['ResourceConfig']['InstanceType']
        if not instance_type.startswith("ml."):
            new_instance_type = "ml." + instance_type
            print("Correcting instance type from %s to %s" % (instance_type, new_instance_type))
            request['TrainingJobDefinition']['ResourceConfig']['InstanceType'] = new_instance_type

    def create_tuning_job_request(self):
        request = {
            "TuningJobConfig": self.get_tuning_job_config(),
            "TrainingJobDefinition": self.get_training_job_definition(),
            "TuningJobName": self.get_jobname(),
        }
        self.correct_instance_type(request)
        self.request_json = request
        return request

    def get_static_hyperparmaeters_from_ranges_files(self):
        raw = self._get_hyperparameter_ranges_data()
        return raw.get('StaticHyperParameters', {})

    def get_hyperparameter_ranges(self):
        raw = self._get_hyperparameter_ranges_data()
        try:
            del raw['StaticHyperParameters']
        except KeyError:
            pass
        return raw

    def _get_hyperparameter_ranges_data(self):

        if self.hyperparam_ranges:
            return self.hyperparam_ranges.copy()

        fn = self.opts.hyperparam_ranges_file
        try:
            if fn.endswith(".yaml"):
                print("YAML support not added or tested.  Need to brazil and verify")
                return yaml.load(open(fn))
            return self.load_json(self.opts.hyperparam_ranges_file)
        except:
            print("Failed to load hyperparameter ranges file %s" % fn)
            raise

    def load_json(self, filename):
        with open(filename) as fh:
            return json.load(fh)

    def _display_attributes(self):
        """All the attributes that we want to show to the user.
        """
        out = {}
        out.update(vars(self.opts))
        return out

    def __repr__(self):
        klass = self.__class__
        pretty = json.dumps(self._display_attributes(), indent=2, sort_keys=True)
        return "%s: %s" % (klass.__name__, pretty)

    def _repr_html_(self):
        """Displays as HTML for Notebooks
        """

        def html_row(key, val):
            style = ""
            if "UNSET_PARAMETER_WARNING" in str(val):
                style = "style='background:#ff9'"
            return Template("""
                <tr $style>
                    <td>$key</td>
                    <td>$val</td>
                </tr>
            """).substitute(
                key=key,
                val=val,
                style=style,
            )

        html = Template("""
        <b>$name</b>
        <table>
            $table_rows
        </table>
        """).substitute(
            name=self.__class__.__name__,
            table_rows="\n".join([html_row(*kv) for kv in self._display_attributes().items()]),
        )
        return html

    def attributes(self):
        """Returns a list of the attributes used to control the job
        """
        possible_attr_names = self.__class__.__dict__.keys()



class XGBoostLauncher(BaseLauncher):
    # DEFAULT_HYPERPARAM_RANGES_FILE = "internal-xgb-ranges.json"  #TODO

    # The role you created in your account which your SageMaker training jobs will assume to access your data & write your logs
    TRAINING_ROLE = "UNSET_PARAMETER_WARNING: need to set training role"

    DEFAULT_REGION = 'us-west-2'
    REGION_TO_ECR_IMAGE_MAP = {
        'us-west-2':'433757028032.dkr.ecr.us-west-2.amazonaws.com/xgboost:latest',
        'us-east-1':'811284229777.dkr.ecr.us-east-1.amazonaws.com/xgboost:latest'
    }


    # Short string name for automatically generating names of TuningJobs
    DEFAULT_NAME_PREFIX = "xgb-hpo"

    # S3 locations
    DEFAULT_INPUT_DATA = "UNSET_PARAMETER_WARNING: need to set s3 location of input data"
    DEFAULT_OUTPUT_LOCATION = "UNSET_PARAMETER_WARNING: need to set s3 location for output data"

    # Optimization Objective
    OBJECTIVE_TYPE = "Maximize"
    #OBJECTIVE_METRIC = "valid-score"
    OBJECTIVE_METRIC = "valid-auc"
    # Data about how the training job should run
    INSTANCE_TYPE = "ml.c4.2xlarge"
    INSTANCE_COUNT = 1
    MAX_RUNTIME_IN_HOURS = 12
    VOLUME_SIZE_IN_GB = 10

    # Default XGBoost Static Hyper Parameters
    DEFAULT_XGB_STATIC_HYPER_PARAMS = {
        "eval_metric": "auc",
        "objective": "binary:logistic",
        "num_round": "100",
    }

    def get_ecr_image(self):
        # The location of your Docker image with your algorithm
        return self.REGION_TO_ECR_IMAGE_MAP[os.getenv("AWS_REGION")] if os.getenv("AWS_REGION") in self.REGION_TO_ECR_IMAGE_MAP else self.REGION_TO_ECR_IMAGE_MAP[self.DEFAULT_REGION]

    def get_metric_definitions(self):
        return [
            {
                "Name": "valid-auc",
                "Regex": "validation-[a-z]+:([0-9\\.]+)"
            },
            {
                "Name": "train-auc",
                "Regex": "train-[a-z]+:([0-9\\.]+)"
            }
        ]

    def get_input_data_config(self):
        return [
            {
                "ChannelName": "train",
                "CompressionType": "None",
                "ContentType": "csv",
                "DataSource": {
                    "S3DataSource": {
                        "S3Uri": self.opts.input_data_url + "train/",
                        "S3DataType": "S3Prefix",
                        "S3DataDistributionType": "FullyReplicated"
                    }
                },
            },
            {
                "ChannelName": "validation",
                "CompressionType": "None",
                "ContentType": "csv",
                "DataSource": {
                    "S3DataSource": {
                        "S3Uri": self.opts.input_data_url + "val/",
                        "S3DataType": "S3Prefix",
                        "S3DataDistributionType": "FullyReplicated"
                    }
                },
            }
        ]

    def get_static_hyperparameters(self):
        """
        :return: Static Parameters are first fetched from the `self.hyper_parameters` which can be overriden from notebook and
        if it is null then DEFAULT_XGB_STATIC_HYPER_PARAMS returned as default.

        """
        overriden_static_hps = super(XGBoostLauncher,self).get_static_hyperparameters()
        if overriden_static_hps is None:
            return self.DEFAULT_XGB_STATIC_HYPER_PARAMS
        return overriden_static_hps
