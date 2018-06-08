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


"""Example of a launcher script.
Copy this to your own file, and change the constants to use
"""

import os

from smhpolib.launcher import BaseLauncher

class CustomLauncher(BaseLauncher):

    # The role you created in your account which your SageMaker training jobs will assume to access your data & write your logs
    TRAINING_ROLE = "arn:aws:iam::123456789012:role/sm-training-role"

    # The location of your Docker image with your algorithm
    ECR_IMAGE = "123456789012.dkr.ecr.us-west-2.amazonaws.com/trainingalgo"

    # Short string name for automatically generating names of TuningJobs
    DEFAULT_NAME_PREFIX = "algo"

    # S3 locations
    DEFAULT_INPUT_DATA = "s3://your-bucket/data/test/"
    DEFAULT_OUTPUT_LOCATION = "s3://your-bucket/ml/train-output/"

    # Optimization Objective
    OBJECTIVE_TYPE = "Maximize"
    OBJECTIVE_METRIC = "valid-precision"

    # Data about how the training job should run
    INSTANCE_TYPE = "ml.c4.xlarge"
    MAX_RUNTIME_IN_HOURS = 5
    VOLUME_SIZE_IN_GB = 10

    #AWS region you are working in
    AWS_REGION = 'your-region'

    def get_metric_definitions(self):
        return [
            {
                "Name": "loss",
                "Regex": "loss = ([0-9\\.]+)"
            },
            {
                "Name": "valid-precision",
                "Regex": "Validation-Precision: ([0-9\\.]+)"
            },
            {
                "Name": "epoch",
                "Regex": "Epoch ([0-9\\.]+)"
            }
        ]

    def get_ecr_image(self):
        return self.ECR_IMAGE

if __name__ == "__main__":
    os.environ["AWS_REGION"] = CustomLauncher.AWS_REGION
    launcher = CustomLauncher()
    launcher.main()
