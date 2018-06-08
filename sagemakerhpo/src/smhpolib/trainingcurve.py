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
Library for aggregating, processing, storing and displaying
training curves for SageMaker training jobs.
"""
from __future__ import absolute_import

import boto3
import collections
import pandas as pd

from .analysis import TrainingJobMetricsFetcher

class TrainingCurveData(object):
    """Encapsulates storage & basic processing of
    metric data coming from a SageMaker TrainingJob
    for the purpose of rendering a training curve chart
    or similar analysis
    """

    def __init__(self):
        self._callbacks = []
        self._data = collections.defaultdict(list)
        self._df = None

    def register_callback(self, callback):
        """Register a callback function to be executed
        whenever this object receives updated data
        """
        self._callbacks.append(callback)

    def fire_callbacks(self):
        for cb in self._callbacks:
            cb(self)

    def _set_dirty(self):
        self._df = None
        
    def add_metric(self, timestamp, metric_name, value, **kwargs):
        self._data['timestamp'].append(timestamp)
        self._data['metric_name'].append(metric_name)
        self._data['value'].append(value)
        for k,v in kwargs.items():
            self._data[k].append(v)
        self._set_dirty()
        self.fire_callbacks()

    @property
    def df(self):
        if self._df is None:
            self._df = pd.DataFrame(self._data)
        return self._df

    def df_for_metric(self, metric_name, minimal_columns=True):
        rows = self.df.loc[self.df['metric_name'] == metric_name]
        if minimal_columns:
            return rows.filter(['timestamp','value'])
        else:
            return rows

    def save_csv(self, filename):
        self.df.to_csv(filename)

    def __len__(self):
        return len(self.df)

    @classmethod
    def load_csv(cls, filename):
        raise NotImplementedException("TODO")

    def single_metric(self, metric_name):
        raise NotImplementedException("TODO: return a pair of timeseries for plotting, for just 1 metric")
        # Maybe filter the DF?


class CloudWatchMetricFetcher(object):
    """Fetches metrics for a TrainingJob from CloudWatch Metrics,
    and saves them into a data repo.
    """

    CLOUDWATCH_NAMESPACE = 'SageMakerHPO'

    def __init__(self, cloudwatch_client=None):
        self._data = TrainingCurveData()
        if cloudwatch_client is None:
            cloudwatch_client = boto3.client('cloudwatch')
        self.cloudwatch = cloudwatch_client

    def fetch_metric(self, training_job_name, metric_name):
        """Fetches all the values of a named metric for a training job
        """
        #TODO: unwind this dependency
        fetcher = TrainingJobMetricsFetcher(training_job_name)
        #TODO: add absolute timestamp back in
        xy = fetcher.fetch_metric(metric_name)
        if len(xy[0]) == 0:
            print("Warning: No metrics called %s found" % metric_name)
        for elapsed_seconds, value in zip(xy[0],xy[1]): #TODO: get rid of this loop
            self._data.add_metric(elapsed_seconds, metric_name, value, 
                    training_job_name=training_job_name)

    def training_curve_data(self):
        """Returns a TrainingCurveData object
        """
        return self._data

