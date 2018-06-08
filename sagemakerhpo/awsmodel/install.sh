#!/bin/bash 

MODELDIR=`dirname $0`

set -e  # Fail on error
set -x  # Echo what we're doing.

aws configure add-model --service-model file://${MODELDIR}/service-2.json --service-name sagemaker

aws sagemaker help | head -10

echo "SageMaker is now installed to use from boto3 and AWS CLI"
