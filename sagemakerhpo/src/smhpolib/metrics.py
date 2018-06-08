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
Metrics processing.
"""
import boto3
import datetime

cloudwatch = boto3.client('cloudwatch')

def kw_get_metrics(job_name, metric_name, **time_interval):
    """Returns the **kwargs needed to call CloudWatch Metrics
    get_metric_statistics to retrieve metrics for a training job.
    :param time_interval is a dict.  Can either be single value like {"Hours": 3}
        or a pair like {"start_time": datetime, "end_time": datetime}
    """
    if len(time_interval) == 2:
        start_time = time_interval['start_time']
        end_time = time_interval['end_time']
    else:
        if len(time_interval) == 0:
            graph_interval = datetime.timedelta(hours=1)
        if len(time_interval) == 1:
            graph_interval = datetime.timedelta(**time_interval)
        end_time = datetime.datetime.utcnow()
        start_time = end_time - graph_interval

    return {
        'Namespace': 'SageMakerHPO',
        'MetricName': metric_name,
        'Dimensions': [ 
            { 
                'Name': 'JobName', 
                'Value': job_name
            }
        ],
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 60,
        'Statistics': ['Average'],
    }

class UTC(datetime.tzinfo):
    """Because py2.7 has no built in UTC implementation
    """
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    
    def tzname(self, dt):
        return "UTC"
    
    def dst(self, dt):
        return datetime.timedelta(0)

def plottable_from_cwm(raw_data):
    out = []
    base_time = min(raw_data, key = lambda pt: pt['Timestamp'])['Timestamp']
    for pt in raw_data:
        y = pt['Average']
        x = (pt['Timestamp'] - base_time).total_seconds()
        out.append([x,y])
    out = sorted(out, key=lambda x: x[0])
    all_x = [xy[0] for xy in out]
    all_y = [xy[1] for xy in out]
    return all_x, all_y

def plottable_for_job(job_name, metric_name, **time_interval):
    """Fetches metrics from CloudWatch.
    Returns a pair (x,y) of lists for plotting.
    x is a list of times in seconds, from the first metric in the job.
    y is a list of metric values
    time_interval can be "hours=3" or "minutes=15" or any other
    valid constructor arguments to datetime.timedelta().
    """
    raw_data = cloudwatch.get_metric_statistics(
        ** kw_get_metrics(job_name, metric_name, **time_interval)
    )['Datapoints']
    if( len(raw_data) == 0 ):
        return [],[]
    x,y = plottable_from_cwm(raw_data)
    return x,y
