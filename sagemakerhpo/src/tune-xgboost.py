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


"""Launcher script for XGBoost
"""

import os

from smhpolib.launcher import XGBoostLauncher
from smhpolib import util

class XGBLauncher(XGBoostLauncher):

    DEFAULT_HYPERPARAM_RANGES_FILE = "xgboost-ranges.json"
    AWS_ACCOUNT_ID = util.current_aws_account()

    # The role you created in your account which your SageMaker training jobs will assume to access your data & write your logs
    TRAINING_ROLE = "arn:aws:iam::%s:role/AWSSagemakerHPODataAccessRole" % AWS_ACCOUNT_ID
    DEFAULT_NAME_PREFIX = "xgb-hpo"
    ECR_IMAGE = "433757028032.dkr.ecr.us-west-2.amazonaws.com/xgboost:latest"

    # S3 locations
    DEFAULT_INPUT_DATA = "s3://public-test-hpo-datasets-pdx/kaggle/porto-seguro/xgb/"
    DEFAULT_OUTPUT_LOCATION = "s3://sagemaker-output-%s" % AWS_ACCOUNT_ID
    AWS_REGION='us-west-2'

    def get_ecr_image(self):
        return self.ECR_IMAGE



if __name__ == "__main__":
    os.environ["AWS_REGION"] = XGBLauncher.AWS_REGION
    launcher = XGBLauncher()
    launcher.main()
