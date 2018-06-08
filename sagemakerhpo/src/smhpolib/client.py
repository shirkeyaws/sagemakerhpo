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


import boto3
import os

from . import util

class SmhpoClient():
    """Helper class to set up boto3 client to call SageMakerHPO.
    Figures out endpoint smartly.
    Sets AwsAccountId for you.
    """

    # Defaults
    _DEFAULT_REGION = "us-west-2"

    _ENDPOINTS_MAP = {
        'us-west-2':'https://zj0jmkp64g.execute-api.us-west-2.amazonaws.com/Prod',
        'us-east-1':'https://86b5tsckyb.execute-api.us-east-1.amazonaws.com/Prod'
    }

    @classmethod
    def get_smhpo_client(cls, region=None, endpoint_url=None):
        """Returns a boto client for calling SageMaker-HPO.
        :param region: the AWS region
        :param endpoint_url: the service endpoint
        """
        if not region:
            region=os.getenv("AWS_REGION")
            if not region:
                region=cls._DEFAULT_REGION
        return SmhpoClient(region, cls._pick_endpoint(explicit_endpoint=endpoint_url,region=region))

    @classmethod
    def _pick_endpoint(cls, explicit_endpoint,region):
        if explicit_endpoint:
            return explicit_endpoint
        env_endpoint = os.getenv('SMHPO_ENDPOINT_URL')
        if env_endpoint:
            print("Using SMHPO_ENDPOINT_URL from environment: %s" % env_endpoint)
            return env_endpoint
        if region in cls._ENDPOINTS_MAP:
            print("Using SMHPO_ENDPOINT_URL: %s" % cls._ENDPOINTS_MAP[region])
            return cls._ENDPOINTS_MAP[region]
        else:
            raise ValueError("given aws region not in endpoints map")

    def __init__(self, region, endpoint_url):
        self._boto_client = boto3.client('sagemakerhpo',
            region_name=region,
            endpoint_url=endpoint_url,
        )
        self._aws_account_id = util.current_aws_account()

    def describe_tuning_job(self, *args, **kwargs):
        return self._boto_client.describe_tuning_job(AwsAccountId=self._aws_account_id, *args, **kwargs)

    def create_tuning_job(self, *args, **kwargs):
        return self._boto_client.create_tuning_job(AwsAccountId=self._aws_account_id, *args, **kwargs)

    def list_training_jobs_for_tuning_job(self, *args, **kwargs):
        return self._boto_client.list_training_jobs_for_tuning_job(AwsAccountId=self._aws_account_id, *args, **kwargs)

    def stop_tuning_job(self, *args, **kwargs):
        return self._boto_client.stop_tuning_job(AwsAccountId=self._aws_account_id, *args, **kwargs)


def get_smhpo_client(*args, **kwargs):
    return SmhpoClient.get_smhpo_client(*args, **kwargs)
