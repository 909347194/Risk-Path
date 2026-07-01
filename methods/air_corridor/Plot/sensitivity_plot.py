#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/sensitivity_plot.py
"""
Module: sensitivity_plot
This module contains functions for plotting sensitivity analysis related to emergency landing scenarios.
It includes functions to create 2D dense plots with paths for sensitivity analysis of the trade-off weight omega.

Functions:
    sensitivity_dense_plot(MAP, path_group, weight_group, index): Subplot, 2D dense plot with paths.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from Key_Elements.point_params import x_ratio, y_ratio, A
import time
import math
from Key_Elements.weight import *


def sensitivity_dense_plot(MAP, path_group, weight_group, index):
    """
    Subplot, 2D dense plot with paths.
    Sensitivity analysis of the trade-off weight omega. Synthesized data.

    Parameters:
        MAP (np.array): The 3D array representing the map.
        path_group (list): List of paths, where each path is a list of nodes.
        weight_group (list): List of trade-off weights for sensitivity analysis.
        index (int): 
            0: Plot based on risk and noise.
            1: Plot based on vehicle and pedestrian density.

    Returns:
        None
    """

    # index = 0, risk; index = 1, dense
    if index == 0:
        data_max = 0.0
        for i in range(MAP.shape[0]):
            for j in range(MAP.shape[1]):
                data_max = max(data_max, 0.6*MAP[i][j][0].risk+0.4*MAP[i][j][0].noise)
        data_plt  =  np.array([[plt.cm.jet(0.9*(0.6*MAP[x][y][0].risk+0.4*MAP[x][y][0].noise)/data_max) \
                              for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
                
        # data_max = 0.0
        # data_min = float('inf')
        # for i in range(MAP.shape[0]):
        #     for j in range(MAP.shape[1]):
        #         data_max = max(data_max, A*MAP[i][j][0].risk+(1.0-A)*MAP[i][j][0].noise)
        #         data_min = min(data_min, A*MAP[i][j][0].risk+(1.0-A)*MAP[i][j][0].noise)
        # data_plt  =  np.array([[plt.cm.jet((math.log2(A*MAP[x][y][0].risk+(1.0-A)*MAP[x][y][0].noise)-math.log2(data_min))/(math.log2(data_max)-math.log2(data_min))) 
        #                       for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])

    else:
        data_plt  =  np.array([[0.5*MAP[x][y][0].VehDens+0.5*MAP[x][y][0].PeoDens \
                              for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
                data_plt[i][j][3] = 0.45 # transparency of the background

    # display path 
    alpha = 1.0
    fig, axes = plt.subplots(3, 7, figsize = (19.2*alpha, 10.0*alpha))
    fig.suptitle("Sensitivity Analysis of the Trade-off Weight", fontsize = 20)
    plt.subplots_adjust(left = 0.05, right = 0.95, top = 0.9, bottom = 0.2, wspace = 0.3, hspace = 0.3)
    # fig.tight_layout(h_pad = 2)
    """
        add colorbars 
    """
    # for ax in axes.flat:
    #     ax.axis('off')
    plt.rcParams.update({"font.size":12})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = 1.1*data_max)
    cax_main = plt.axes((0.05, 0.1, 0.4, 0.02))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':12, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # plt.subplots_adjust(top = 0.85)
    
    flag = 0
    # norm_group = []
    # cmap_group = [mpl.cm.Oranges, mpl.cm.Greens, mpl.cm.Blues, mpl.cm.Purples]
    title_group = ['Weight  =  '+str(w) for w in weight_group]
    h_max_color = 0.0
    for path in path_group:
        for node in path:
            h_max_color = max(h_max_color, node[3])
    h_norm = mpl.colors.Normalize(vmin = 0.0, vmax = h_max_color)
    h_cmap = mpl.cm.cool
    cax_h = plt.axes((0.55, 0.1, 0.4, 0.02))
    h_cbar = fig.colorbar(mpl.cm.ScalarMappable(h_norm, cmap = h_cmap), cax = cax_h, orientation = 'horizontal')
    h_font_dict = {'size':12, "color":"grey"}
    h_cbar.set_label("Height (m)", fontdict = h_font_dict)
    h_cbar.solids.set_edgecolor('face')
    # norm_group.append(norm)
    
    flag = 0
    for path in path_group:
        for node in path:
            data_plt[node[0]][node[1]] = plt.cm.cool(node[3]/h_max_color)
            data_plt[node[0]][node[1]][3] = 1.0
        data_plt[path[0][0]][path[0][1]] = plt.cm.binary(1.0)
        data_plt[path[-1][0]][path[-1][1]] = plt.cm.binary(1.0)
        im = axes[int((flag-flag%7)/7)][flag%7].imshow(data_plt)
        # cax = add_right_cax(axes[int((flag-flag%2)/2)][flag%2], pad = 0.02, width = 0.02)
        # cbar = fig.colorbar(mpl.cm.ScalarMappable(norm_group[flag], cmap = cmap_group[flag]), cax = cax, orientation = 'vertical')
        # font_dict = {'size':10, "color":"grey"}
        # cbar.set_label("Height (m)", fontdict = font_dict)
        # cbar.solids.set_edgecolor('face')
        # cbar.ax.tick_params(axis = 'both', which = 'both', color = 'green')
        axes[int((flag-flag%7)/7)][flag%7].set_title(title_group[flag], color = "black")
        axes[int((flag-flag%7)/7)][flag%7].set_xlabel("X ("+str(int(10*x_ratio))+"m)", color = 'grey')
        axes[int((flag-flag%7)/7)][flag%7].set_ylabel("Y ("+str(int(10*y_ratio))+"m)", color = 'grey')
        axes[int((flag-flag%7)/7)][flag%7].spines['bottom'].set_color('grey')
        axes[int((flag-flag%7)/7)][flag%7].spines['left'].set_color('grey')
        axes[int((flag-flag%7)/7)][flag%7].spines['top'].set_color('grey')
        axes[int((flag-flag%7)/7)][flag%7].spines['right'].set_color('grey')
        axes[int((flag-flag%7)/7)][flag%7].tick_params(axis = 'x', colors = 'grey')
        axes[int((flag-flag%7)/7)][flag%7].tick_params(axis = 'y', colors = 'grey')

        for node in path:
            data_plt[node[0]][node[1]] = plt.cm.jet(0.9*(0.6*MAP[node[0]][node[1]][0].risk + \
                                                       0.4*MAP[node[0]][node[1]][0].noise)/data_max)
            data_plt[node[0]][node[1]][3] = 0.6

        flag += 1

    # plt.show()
    # plt.waitforbuttonpress()
    time_now = time.time()
    plt.savefig('./Experiments/Sensitivity_analysis/Sensitivity2D_tradeoff_weight_4.png', transparent = True)
    return  


def sensitivity_line(result_group, weight_group):
    '''
    Subplot, curve plot.
    Sensitivity analysis of the trade-off weight omega. Synthesized data.
    '''

    # df = pd.DataFrame(data = result_group, columns = ['Algorithm', 'Energy Cost', 'Risk Cost', 'Weighted Cost', 'Average Risk Cost', 'Negotiation Prob.'])
    # df['Weight'] = weight_group
    # for i in range(df.shape[0]):
    #     df.loc[i]['Negotiation Prob.'] = math.log(float(df.loc[i]['Negotiation Prob.']))
    # # df = df.round({'Distance':1, 'Overall Cost':4, 'Average Cost':6, 'Negotiation Prob.':4})
    # df = df.round({'Energy Cost':1, 'Risk Cost':4, 'Weighted Cost':1, 'Average Risk Cost':5, 'Negotiation Prob.':4})

    data_ec = np.array([float(result_group[i][1]) for i in range(len(result_group))])
    data_rc = np.array([float(result_group[i][2]) for i in range(len(result_group))])
    # data_wc = np.array([float(result_group[i][3]) for i in range(len(result_group))])
    data_np = np.array([float(result_group[i][5]) for i in range(len(result_group))])

    data_w = weight_group
    data_group = [data_ec, data_rc, data_np]

    label_group = ["Distance Cost Based", "Weighted Cost Based", "TPR Cost Based"]
    # label_group = ["Weighted Cost Based"]
    cols = ['Distance Cost', 'TPR Cost', 'Negotiation Probability']
    colors = ['blue', 'gold', 'darkorange']
    markers = ['o', '^', 'D']

    alpha = 1.0
    fig = plt.figure(figsize = (24.0*alpha, 5.4*alpha))
    # fig.suptitle("Sensitivity Analysis of the Trade-off Weight", fontsize = 20)
    plt.subplots_adjust(left = 0.15, right = 0.9, top = 0.9, bottom = 0.05, wspace = 0.30, hspace = 0.3)
    plt.rcParams.update({"font.size":16})
    
    axes = []
    # ytick_form = ['%.1f', '%.4f', '%.1f', '%.2e', '%.3f']
    # ytick_form = ['{:.1f}', '{:.4f}', '{:.1f}', '{:.3e}', '{:.3f}']
    ytick = [1, 4, 1, 3, 3]
    for k in range(len(cols)):
        ax = fig.add_subplot(1, 3, k+1)
        axes.append(ax)

    Enlarge_param = get_value('Enlarge_param')
    
    for k in range(len(cols)):
        y_0 = np.array([data_group[k][0] for _ in range(len(result_group))])
        y_1 = np.array([data_group[k][-1] for _ in range(len(result_group))])
        axes[k].plot(data_w, y_1, color = colors[0], linestyle = '--')
        axes[k].plot(data_w, data_group[k], color = colors[1], marker = 'D', markersize = 3, linestyle = '-')
        axes[k].plot(data_w, y_0, color = colors[2], linestyle = '-.')
        axes[k].set_title(cols[k], color = "black", fontsize = 18)
        axes[k].legend(label_group, frameon = False, labelcolor = 'grey', fontsize = 16)
        axes[k].set_xlabel('Weight', color = 'grey', fontsize = 16)
        axes[k].set_ylabel(cols[k], color = "grey", fontsize = 16)
        axes[k].spines['bottom'].set_color('grey')
        axes[k].spines['left'].set_color('grey')
        axes[k].spines['top'].set_color('grey')
        axes[k].spines['right'].set_color('grey')
        axes[k].tick_params(axis = 'x', colors = 'grey', labelsize = 16)
        axes[k].tick_params(axis = 'y', colors = 'grey', labelsize = 16)
        axes[k].grid(True)
        # if k == 3:
        #     y_formatter  =  ScalarFormatter(useMathText = True)
        #     y_formatter.set_powerlimits((-2, 2))
        # else:
        #     y_formatter = FormatStrFormatter(ytick_form[k])
        # axes[k].yaxis.set_major_formatter(y_formatter)

    # plt.show()
    # plt.waitforbuttonpress()
    time_now = time.time()
    plt.savefig('./Experiments/Sensitivity_analysis/Sensitivity_line_tradeoff_weight_4.png', transparent = True)
    return


def sensitivity_risk_weight(result_data):
    '''
    This function is to plot the grid plots of sensitivity analysis
    '''
    
    result_dict  =  {}
    fatality_weights  =  [round(0.1 * i, 1) for i in range(11)]
    for fw in fatality_weights:
            property_weights  =  [round(0.1 * j, 1) for j in range(11)]
            for pw in property_weights:
                result_dict[(fw, pw)]  =  (np.nan, np.nan)

    for key in result_data:
        result_dict[key]  =  result_data[key]

    # Extract data for plotting
    fatality_weights  =  np.array([key[0] for key in result_dict.keys()])
    property_weights  =  np.array([key[1] for key in result_dict.keys()])

    # Prepare grid data
    unique_fatality_weights  =  sorted(set(fatality_weights))
    unique_property_weights  =  sorted(set(property_weights))

    # Prepare a grid for both distance cost and TPR cost
    distance_grid  =  np.zeros((len(unique_property_weights), len(unique_fatality_weights)))
    tpr_grid  =  np.zeros((len(unique_property_weights), len(unique_fatality_weights)))

    # Populate the grid with data from result_dict
    for key, value in result_dict.items():
        f_idx  =  unique_fatality_weights.index(key[0])
        p_idx  =  unique_property_weights.index(key[1])
        distance_grid[p_idx, f_idx]  =  value[0]  # Distance cost
        tpr_grid[p_idx, f_idx]  =  value[1]       # TPR cost


    # plot
    fig, (ax1, ax2)  =  plt.subplots(1, 2, figsize = (14, 6))

    # Grey color settings for text and borders
    text_color  =  'grey'

    # Plot Distance Cost grid
    cax1  =  ax1.imshow(distance_grid, cmap = 'viridis', origin = 'lower')
    ax1.set_title('Distance Cost Grid', fontsize = 14)
    ax1.set_xlabel('Fatality Risk Cost Weight', fontsize = 14, color = text_color)
    ax1.set_ylabel('Property Risk Cost Weight', fontsize = 14, color = text_color)
    ax1.set_xticks(np.arange(len(unique_fatality_weights)))
    ax1.set_yticks(np.arange(len(unique_property_weights)))
    ax1.set_xticklabels(unique_fatality_weights, fontsize = 14, color = text_color)
    ax1.set_yticklabels(unique_property_weights, fontsize = 14, color = text_color)

    # Adjust the colorbar with scientific notation
    cbar1  =  fig.colorbar(cax1, ax = ax1, label = 'Distance Cost', shrink = 0.8)
    cbar1.set_label('Distance Cost', fontsize = 14, color = text_color)
    cbar1.ax.yaxis.set_tick_params(color = text_color)
    plt.setp(plt.getp(cbar1.ax, 'yticklabels'), color = text_color)

    # Plot TPR Cost grid
    cax2  =  ax2.imshow(tpr_grid, cmap = 'plasma', origin = 'lower')
    ax2.set_title('TPR Cost Grid', fontsize = 14)
    ax2.set_xlabel('Fatality Risk Cost Weight', fontsize = 14, color = text_color)
    ax2.set_ylabel('Property Risk Cost Weight', fontsize = 14, color = text_color)
    ax2.set_xticks(np.arange(len(unique_fatality_weights)))
    ax2.set_yticks(np.arange(len(unique_property_weights)))
    ax2.set_xticklabels(unique_fatality_weights, fontsize = 14, color = text_color)
    ax2.set_yticklabels(unique_property_weights, fontsize = 14, color = text_color)

    # Adjust the colorbar with scientific notation
    cbar2  =  fig.colorbar(cax2, ax = ax2, label = 'TPR Cost', shrink = 0.8, format = '%.2e')
    cbar2.set_label('TPR Cost', fontsize = 14, color = text_color)
    cbar2.ax.yaxis.set_tick_params(color = text_color)
    plt.setp(plt.getp(cbar2.ax, 'yticklabels'), color = text_color)

    # Set all axes borders to grey
    for ax in [ax1, ax2]:
        ax.spines['top'].set_color(text_color)
        ax.spines['right'].set_color(text_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)

    # Display the updated grid plots
    plt.tight_layout()
    # plt.show()

    plt.savefig('./Experiments/Sensitivity_analysis/Risk_weights_1.png')
