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
Visualization library tools for training curve data
"""

import bokeh
import bokeh.io
import bokeh.plotting
from bokeh.models import HoverTool

class BokehPlotter(object):

    def __init__(self, training_curve_data):
        self._tcd = training_curve_data

    def multiline(self, metric_names, figure_opts=None, show=None):
        """Returns a bokeh plot for multiple figures
        """
        if figure_opts is None:
            figure_opts = {
                "plot_width": 900,
                "plot_height": 400,
                "x_axis_label": "Elapsed time (seconds)",
            }
        p = bokeh.plotting.figure(**figure_opts)
        for i, metric_name in enumerate(metric_names):
            print("plotting %s" % metric_name)
            xy = self._tcd.df_for_metric(metric_name)
            p.line(xy['timestamp'], xy['value'], legend=metric_name, **self._line_opts(i))
            if len(xy['timestamp']) < 20:
                p.circle(xy['timestamp'], xy['value'], legend=metric_name, **self._line_opts(i))
        #TODO: move the legend https://stackoverflow.com/questions/26254619/position-of-the-legend-in-a-bokeh-plot
        if show=='notebook':
            bokeh.io.output_notebook()
            bokeh.plotting.show(p)
        return p

    LINE_OPTS = [
        ["orange",3],
        ["blue",1],
        ["red",1],
        ["purple",1],
    ]
    def _line_opts(self, line_num):
        #TODO: use a pallette
        opts = self.LINE_OPTS[line_num] 
        return {
            "color": opts[0],
            "line_width": opts[1],
        }


class SmhpoHover():

    def __init__(self, tuning_job):
        self.tuning = tuning_job

    def hovertool(self):
        tooltips = [
            ("FinalObjectiveValue", "@FinalObjectiveValue"),
            ("TrainingJobName", "@TrainingJobName"),
        ]
        for k in self.tuning.hyperparam_ranges().keys():
            tooltips.append( (k, "@{%s}" % k) )

        ht = HoverTool(tooltips=tooltips)
        return ht

    def tools(self, standard_tools='pan,crosshair,wheel_zoom,zoom_in,zoom_out,undo,reset'):
        return [self.hovertool(), standard_tools]
   
