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
import datetime
import os
import sys

def serialize_helper(obj):
    """Serializes datetime objects with json.dumps
    """
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Object of type '%s' is still not JSON serializable" % type(obj))

def current_aws_account():
    """Returns the 12-digit account id for the current boto client
    """
    return boto3.client('sts').get_caller_identity()['Account']

