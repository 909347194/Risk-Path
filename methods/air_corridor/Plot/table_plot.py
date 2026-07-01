#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/table_plot.py
"""
Module: table_plot
This module contains functions for plotting tables to compare the performance of different methods
related to emergency landing scenarios.

Functions:
    plot_table(result_group): Plots tables to compare the performance of different methods.
"""

import matplotlib.pyplot as plt
from plottable import Table, ColDef
import pandas as pd
import time
from Key_Elements.weight import *
from .base_functions import *


def plot_table(result_group):
    """
    Plots tables to compare the performance of different methods.

    Parameters:
        result_group (list): List of results, where each result is a list containing performance metrics.

    Returns:
        None
    """

    df = pd.DataFrame(data = result_group, columns = ['Algorithm', 'Distance Cost', 'Risk Cost', \
                                               'Weighted Cost', 'Average Risk Cost', 'Negotiation Prob.'])
    # df = df.round({'Distance':1, 'Overall Cost':4, 'Average Cost':6, 'Negotiation Prob.':4})

    alpha = 0.8
    fig, ax = plt.subplots(figsize = (19.2*alpha, 10.8*alpha))
    Table(
        df, 
        textprops = {
            'fontsize':18, 
            "fontname":'Times New Roman'
        }, 
        column_definitions = [
            ColDef(name = "Algorithm", width = 5.5, textprops = {'ha':'left'}), 
            ColDef(name = 'Distance Cost', width = 2, textprops = {'ha':'right'}, formatter = '{:.1f}'), 
            ColDef(name = "Risk Cost", width = 3.0, textprops = {'ha':'right'}, formatter = '{:.4f}'), 
            ColDef(name = "Weighted Cost", width = 3.5, textprops = {'ha':'right'}, formatter = '{:.1f}'), 
            ColDef(name = 'Average Risk Cost', width = 4.0, textprops = {'ha':'right'}, formatter = '{:.3e}'), 
            ColDef(name = "Negotiation Prob.", width = 4.0, textprops = {'ha':'right'}, formatter = '{:.3%}')
            # text_cmap = mpl.cm.Greens, 
        ]
    )

    # plt.show()
    # plt.waitforbuttonpress()
    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    plt.savefig(f"./Experiments/TablePlot/{time_now}_Table_{ER_Weight}_{Enlarge_param}.jpg", transparent = True)
    return