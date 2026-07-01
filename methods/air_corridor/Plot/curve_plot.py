#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/curve_plot.py
"""
Module: curve_plot
This module contains functions for plotting curves related to emergency landing scenarios.
It includes functions to plot lines based on path planning results.

Functions:
    plot_line(path_group): Plots lines for different cost metrics based on path planning results.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import math
from Key_Elements.weight import *
from .base_functions import *


def plot_line(path_group):
    """
    Plots lines for different cost metrics based on path planning results.

    Parameters:
        path_group (list): List of paths, where each path is a list of nodes.
    """

    # Plot line together
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    cols = ['Energy Cost', 'Risk Cost', 'Weighted Cost', 'Average Risk Cost', 'Negotiation Prob.']
    colors = ['blue', 'gold', 'darkorange']
    markers = ['o', '^', 'D']
    df_group = []
    for path in path_group:
        data_dis = [node[4][0] for node in path]
        data_oc = [node[4][1] for node in path]
        data_wc = [ER_Weight*node[4][0]+Enlarge_param*(1-ER_Weight)*node[4][1] for node in path]
        data_ac = [node[4][1]/(node[4][0]+0.00001) for node in path]
        data_np = [math.log(node[4][3]) for node in path]
        duration = [round(flag/(len(path)-1), 3) for flag in range(len(path))]
        data_one = np.array([data_dis, data_oc, data_wc, data_ac, data_np, duration])
        data_one = data_one.T
        data = pd.DataFrame(data_one, columns = ['Energy Cost', 'Risk Cost', 'Weighted Cost', \
                                            'Average Risk Cost', 'Negotiation Prob.', 'Duration'])
        
        # time_now = time.time()
        # data.to_csv('./Benchmark/'+str(time_now)+'_Benchmark_data'+'.csv')
        df_group.append(data)
    
    alpha = 1.0
    fig = plt.figure(figsize = (9.6*alpha, 10.8*alpha))
    fig.suptitle("Performance Comparison of Algorithms", fontsize = 20)
    plt.subplots_adjust(left = 0.15, right = 0.9, top = 0.9, bottom = 0.05, wspace = 0.4, hspace = 0.3)
    plt.rcParams.update({"font.size":12})
    
    axes = []
    for k in range(len(cols)):
        ax = fig.add_subplot(3, 2, k+1)
        axes.append(ax)

    for k in range(5):
        for i in range(3):
            axes[k].plot(df_group[i]['Duration'], df_group[i][cols[k]], \
                        color = colors[i], linestyle = '-', label = title_group[i])
        axes[k].set_title(cols[k], color = "black")
        axes[k].legend(title_group, frameon = False, labelcolor = 'grey', fontsize = 10)
        axes[k].set_xlabel('Duration', color = 'grey')
        if k == 4:
            axes[k].set_ylabel('ln (Negotiation Prob.)', color = 'grey')
        else:
            axes[k].set_ylabel(cols[k], color = "grey")
        axes[k].spines['bottom'].set_color('grey')
        axes[k].spines['left'].set_color('grey')
        axes[k].spines['top'].set_color('grey')
        axes[k].spines['right'].set_color('grey')
        axes[k].tick_params(axis = 'x', colors = 'grey')
        axes[k].tick_params(axis = 'y', colors = 'grey')

    # plt.delaxes(ax = axes[5])

    time_now = time.time()
    plt.savefig(f'./Experiments/CurvePlot/{time_now}_line_{ER_Weight}_{Enlarge_param}.jpg', transparent = True)
    return


def plot_line_respectively(path_group):
    '''
    This function is to plot the curves respectively.
    '''

    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    title_group = ["Distance Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    cols = ['Distance Cost', 'Risk Cost', 'Weighted Cost', 'Average Risk Cost', 'Negotiation Prob.']
    colors = ['blue', 'gold', 'darkorange']
    markers = ['o', '^', 'D']
    df_group = []
    for path in path_group:
        data_dis = [node[4][0] for node in path]
        data_oc = [node[4][1] for node in path]
        data_wc = [ER_Weight*node[4][0]+Enlarge_param*(1-ER_Weight)*node[4][1] for node in path]
        data_ac = [node[4][1]/(node[4][0]+0.00001) for node in path]
        data_np = [math.log2(node[4][3]) for node in path]
        duration = [round(flag/(len(path)-1), 3) for flag in range(len(path))]
        data_one = np.array([data_dis, data_oc, data_wc, data_ac, data_np, duration])
        data_one = data_one.T
        data = pd.DataFrame(data_one, columns = ['Distance Cost', 'Risk Cost', 'Weighted Cost', \
                                            'Average Risk Cost', 'Negotiation Prob.', 'Duration'])
        
        # time_now = time.time()
        # data.to_csv('./Benchmark/'+str(time_now)+'_Benchmark_data'+'.csv')
        df_group.append(data)
    
    alpha = 0.8
    figs = []    
    axes = []
    for k in range(len(cols)):
        fig = plt.figure(figsize = (16.0*alpha, 10.8*alpha))
        ax = fig.add_subplot(1, 1, 1)
        fig.subplots_adjust(left = 0.25, right = 0.90)
        figs.append(fig)
        axes.append(ax)

    for k in range(5):
        for i in range(3):
            axes[k].plot(df_group[i]['Duration'], df_group[i][cols[k]], \
                                           color = colors[i], linestyle = '-', label = title_group[i])
        # axes[k+1].set_title(cols[k], color = "black")
        axes[k].legend(title_group, frameon = False, labelcolor = 'grey', fontsize = 20)
        axes[k].set_xlabel('Duration', color = 'grey')
        if k == 4:
            axes[k].set_ylabel('log2 (Negotiation Prob.)', color = 'grey', fontsize = 20)
        else:
            axes[k].set_ylabel(cols[k], color = "grey", fontsize = 20)
        axes[k].spines['bottom'].set_color('grey')
        axes[k].spines['left'].set_color('grey')
        axes[k].spines['top'].set_color('grey')
        axes[k].spines['right'].set_color('grey')
        axes[k].tick_params(axis = 'x', colors = 'grey', labelsize = 20)
        axes[k].tick_params(axis = 'y', colors = 'grey', labelsize = 20)
        axes[k].grid(True)
        time_now = time.time()
        figs[k].savefig(f"./Experiments/CurvePlot/{time_now}_{cols[k]}_{ER_Weight}_{Enlarge_param}.jpg", transparent = True)
    
    return