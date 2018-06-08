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
Helper class for analyzing tuning jobs results
"""
from __future__ import absolute_import

import boto3
from collections import defaultdict
import datetime
import logging
import os
import sys
import traceback

import numpy as np

from . import metrics

try:
    import pandas as pd
except:
    traceback.print_exc()
    logging.warning("Can't load pandas library.  Dataframe functionality will not work")

class TuningJob():

    def __init__(self, tuning_job_name, smhpo_client=None, max_training_jobs=None):
        if smhpo_client:
            self.smhpo_client = smhpo_client
        else:
            self.smhpo_client = boto3.client('sagemaker')
            
        self.tuning_job_name = tuning_job_name
        self._tuning_job_describe_result = None
        self._training_job_summaries = None
        self._training_job_summary_dict = None
        self._metric_names = None
        self._extra_metrics = defaultdict(dict)  # {tj_name:{metric:val}}
        self._cached_timeseries = defaultdict(dict)  # {tj_name:{metric:[(x,x,x),(y,y,y)]}}
        if max_training_jobs is None:
            self._max_training_jobs = 9999999
        else:
            self._max_training_jobs = max_training_jobs

    def describe(self):
        """Response to DescribeTuningJob
        """
        if not self._tuning_job_describe_result:
            self._tuning_job_describe_result = self.smhpo_client.describe_hyper_parameter_tuning_job(
                    HyperParameterTuningJobName=self.tuning_job_name)
        return self._tuning_job_describe_result

    def hyperparam_ranges(self):
        description = self.describe()
        out = {}
        for _, ranges in description['HyperParameterTuningJobConfig']['ParameterRanges'].items():
            for param in ranges:
                out[param['Name']] = param
        return out

    def metric_names(self):
        if self._metric_names is None:
            self._metric_names = [md['Name'] for md in self.describe()['TrainingJobDefinition']['AlgorithmSpecification'][u'MetricDefinitions']]
        return self._metric_names

    def training_job_summaries(self):
        """Everything (paginated) from ListTrainingJobsForTuningJob
        """
        self._ensure_tj_summaries()
        return self._training_job_summaries

    def summary_for(self, training_job_name):
        """One specific record pulled from list of 
        ListTrainingJobsForTuningJob
        """
        self._ensure_tj_summaries()
        return self._training_job_summary_dict[training_job_name]

    def training_job_names(self):
        self._ensure_tj_summaries()
        return [j['TrainingJobName'] for j in self._training_job_summaries]

    def _ensure_tj_summaries(self):
        if self._training_job_summaries is not None:
            return
        logging.info("Fetching all TrainingJob summaries for %s" % self.tuning_job_name)
        output = []
        next_args = {}
        for cnt in range(100):
            logging.debug("Calling list_training_jobs_for_tuning_job %d" % cnt)
            raw_result = self.smhpo_client.list_training_jobs_for_hyper_parameter_tuning_job(HyperParameterTuningJobName=self.tuning_job_name,
                MaxResults=100, **next_args)
            new_output = raw_result['TrainingJobSummaries']
            output.extend(new_output)
            logging.debug("Got %d more TrainingJobs. Total so far: %d" % (len(new_output), len(output)))
            if ('NextToken' in raw_result) and (len(new_output) > 0):
                next_args['NextToken'] = raw_result['NextToken']
            else:
                break
            if len(output) >= self._max_training_jobs:
                break
        output = output[:self._max_training_jobs]
        self._training_job_summaries = output
        self._training_job_summary_dict = {s['TrainingJobName']: s for s in output}


    def hyperparam_dataframe(self, include_times=True):
        """If include_times is set, it will fetch the start/end times from SageMaker DescribeTrainingJob.
        This is needed to get the metrics from CWM
        """
        import pandas as pd
        summaries = self.training_job_summaries()
        def reshape(training_summary):
            training_job_name = '??unknown??'
            out = {}

            training_job_name = training_summary['TrainingJobName']
            
            training_job_description = TrainingJobStatusFetcher.fetch(training_job_name)
            for k,v in training_job_description['HyperParameters'].items():
                # Something (bokeh?) gets confused with ints so convert to float
                try:
                    v = float(v)
                except:
                    pass
                out[k]=v
            
            out['TrainingJobName'] = training_job_name
            out['TrainingJobStatus'] = training_summary['TrainingJobStatus']
            out['FinalObjectiveValue'] = training_summary.get('FinalHyperParameterTuningJobObjectiveMetric',{}).get('Value')
            if (include_times and  training_summary['TrainingJobStatus'] == 'Completed'): 
                out['TrainingEndTime'] = None
                out['TrainingCreationTime'] = None
                try:
                    description = TrainingJobStatusFetcher.fetch(training_job_name)
                    end_time = description['TrainingEndTime']
                    start_time = description['CreationTime']
                    out['TrainingEndTime'] = end_time
                    out['TrainingCreationTime'] = start_time
                    if start_time and end_time:
                        out['TrainingElapsedTimeSeconds'] = (end_time - start_time).total_seconds()
                except:
                    logging.warning("Problem converting training_job %s: %s" % (training_job_name,traceback.format_exc()))
            out.update(self._extra_metrics[training_job_name])
            return out
        df = pd.DataFrame([reshape(tj) for tj in summaries])
        return df


    def metric_timeseries(self, metric_name, training_job_name):
        """Fetches an additional metric timeseries from cloudwatch.
        """
        if not self._cached_timeseries[training_job_name].get(metric_name):
            logging.debug("Fetching %s for %s" % (metric_name, training_job_name))
            fetcher = TrainingJobMetricsFetcher(training_job_name)
            xy = fetcher.fetch_metric(metric_name)
            self._cached_timeseries[training_job_name][metric_name] = xy
        return self._cached_timeseries[training_job_name][metric_name] 

    def add_metric(self, metric_name, aggregate="final"):
        """Adds an additional metric to the dataframe for each training_job
        """
        cnt = 0
        recorded_metric_name= "%s_%s" % (aggregate, metric_name)
        for training_job_name in self.training_job_names():
            xy = self.metric_timeseries(metric_name, training_job_name)
            val = self._pick_aggregate(xy, aggregate)
            self._extra_metrics[training_job_name][recorded_metric_name] = val
            if val is not None:
                cnt += 1
        print("Recorded non-blank %s for %d training jobs" % (recorded_metric_name,cnt))


    def _pick_aggregate(self, xy, aggregate):
        y = xy[1]
        if len(y) == 0:
            logging.warning("Can't aggregate empty metric")
            return None
        if aggregate=="final":
            return y[-1]
        if aggregate=="initial":
            return y[0]
        elif aggregate=="mean":
            return np.mean(y)
        else:
            return n
            raise ValueError("Unknown aggregate type %s" % aggregate)


class TrainingJobStatusFetcher():
    """Utility class to call describe-training-job in SageMaker and cache results
    """
    _DEFAULT_REGION="us-west-2"
    cache = {}

    @classmethod
    def fetch(cls, training_job_name):

        region= boto3.Session().region_name
        if not region:
            region=cls._DEFAULT_REGION
        sm = boto3.client('sagemaker', region_name=region)

        if training_job_name in cls.cache:
            return cls.cache[training_job_name]

        result = sm.describe_training_job(TrainingJobName=training_job_name)
        cls.cache[training_job_name] = result
        return result
    


class TrainingJobMetricsFetcher():
    """
    """

    cloudwatch = boto3.client('cloudwatch')

    def __init__(self, training_job_name):
        self.training_job_name = training_job_name

    def determine_timeinterval(self):
        """Returns a dict with two datetime objects, start_time and end_time
        covering the interval of the training job
        """
        description = TrainingJobStatusFetcher.fetch(self.training_job_name)
        start_time = description[u'TrainingStartTime']  # datetime object
        end_time = description.get(u'TrainingEndTime', datetime.datetime.utcnow())
        return {
            'start_time': start_time,
            'end_time': end_time,
        }

    def fetch_metric(self, metric_name):
        """returns two lists as a tuple.  
        First list is relative time, 
        second list is value.
        """
        logging.debug("Fetching metric %s for TrainingJob: %s" % (metric_name, self.training_job_name))
        timeinterval = self.determine_timeinterval()
        xy = metrics.plottable_for_job(self.training_job_name, metric_name, **timeinterval)
        return xy

    
