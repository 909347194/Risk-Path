#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/voxel_plot.py
"""
Module: voxel_plot
This module contains functions for plotting 3D voxel maps related to emergency landing scenarios.
It includes functions to plot 3D versions of maps and paths with synthesized data.

Functions:
    my_voxel_plot(MAP, path): Plots 3D version of maps and paths with synthesized data.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from Key_Elements.point_class import x_ratio, y_ratio, A
import time
import math
from Key_Elements.weight import *
from .base_functions import *

def my_voxel_plot(MAP, path):
    """
    Plots 3D version of maps and paths with synthesized data.

    Parameters:
        MAP (np.array): The 3D array representing the map.
        path (list): List of coordinates representing the path.

    Returns:
        None
    """

    data_max = 0.0    
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            for k in range(MAP.shape[2]):
                data_max = max(data_max, 0.6*MAP[i][j][k].risk+0.4*MAP[i][j][k].noise)
    data_plt  =  np.array([[[plt.cm.jet(0.9*(0.6*MAP[x][y][z].risk+0.4*MAP[x][y][z].noise)/data_max) \
                           for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
            for k in range(data_plt.shape[2]):
                data_plt[i][j][k][3] = 0.17

    for coord in path:
        data_plt[coord[0]][coord[1]][coord[2]] = [100.0/255, 100.0/255, 100.0/255, 0.8]
    data_plt[path[0][0]][path[0][1]][path[0][2]] = [0.0, 0.0, 0.0, 0.8]
    data_plt[path[-1][0]][path[-1][1]][path[-1][2]] = [0.0, 0.0, 0.0, 0.8]

    # filt minimal data 
    # x1, y1, z1  =  np.where(data_plt > =  10e-5)
    x1, y1, z1 = np.indices((data_plt.shape[0]+1, data_plt.shape[1]+1, data_plt.shape[2]+1))

    gap = 7
    isfilled = np.array([[[z%gap == 0 for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] \
                       for x in range(MAP.shape[0])]) 
    edge_colors = np.array([[[None for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] \
                          for x in range(MAP.shape[0])]) 

    # for coord in path:
    #     move = [-1, 0, 1]
    #     candidates = np.array([[[[i, j, k] for k in move] for j in move] for i in move])
    #     for i in range(candidates.shape[0]):
    #         for j in range(candidates.shape[1]):
    #             for k in range(candidates.shape[2]):
    #                 if inmap(candidates[i][j][k][0]+coord[0], candidates[i][j][k][1]+coord[1], candidates[i][j][k][2]+coord[2], data_plt):
    #                     isfilled[coord[0]+candidates[i][j][k][0]][coord[1]+candidates[i][j][k][1]][coord[2]+candidates[i][j][k][2]] = False
    for coord in path:
        isfilled[coord[0]][coord[1]][coord[2]] = True
        edge_colors[coord[0]][coord[1]][coord[2]] = 'black'

    # plot 3d
    alpha = 0.8
    fig  =  plt.figure(figsize = [alpha*14.4, alpha*10.8]) #inchs, 1 inch = 200 pixels
    ax  =  fig.add_subplot(111, projection = '3d')
    plt.rcParams.update({"font.size":12})
    ax.set_title("3D Route Display of Path Planning", fontsize = 20)
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = 1.1*data_max)
    ax_main = np.array([0.2, 0.02, 0.8, 1])
    cax_main = add_down_cax(ax_main, pad = 0.04, width = 0.02)
    cax_main = fig.add_axes(cax_main)
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':10, "color":"grey"}
    main_cbar.set_label("Weighted risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # ax.voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = [230.0/255, 230.0/255, 230.0/255, 0.01])
    ax.voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)

    # 显示图形
    # plt.colorbar()
    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    plt.savefig('./Experiments/VoxelPlot/3D-Route_'+str(time_now)+'.jpg', transparent = True)
    return


def my_voxel_subplot(MAP, path_group):
    '''
    Subplot.
    This function is to plot 3D version of maps and paths. With synthesized data.
    '''

    data_max = 0.0
    map_alpha = 0.17
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            for k in range(MAP.shape[2]):
                data_max = max(data_max, 0.6*MAP[i][j][k].risk+0.4*MAP[i][j][k].noise)
    data_plt  =  np.array([[[plt.cm.jet(0.9*(0.6*MAP[x][y][z].risk+0.4*MAP[x][y][z].noise)/data_max) \
                           for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
            for k in range(data_plt.shape[2]):
                data_plt[i][j][k][3] = map_alpha

    # x1, y1, z1  =  np.where(data_plt > =  10e-5)
    x1, y1, z1 = np.indices((data_plt.shape[0]+1, data_plt.shape[1]+1, data_plt.shape[2]+1))
    
    gap = 7
    isfilled = np.array([[[z%gap == 0 for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] \
                       for x in range(MAP.shape[0])]) 
    edge_colors = np.array([[[None for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] \
                          for x in range(MAP.shape[0])])

    # plot 3d
    alpha = 0.8
    fig = plt.figure(figsize = (19.2*alpha, 7.0*alpha), )
    axes = []
    k = 0
    for path in path_group:
        ax = fig.add_subplot(1, 3, k+1, projection = '3d')
        axes.append(ax)
        k += 1
    fig.suptitle("3D Display of Path Planning", fontsize = 20)
    plt.subplots_adjust(left = 0.12, right = 0.93, top = 0.9, bottom = 0.15, wspace = 0.35, hspace = 0.3)
    plt.rcParams.update({"font.size":12})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = 1.1*data_max)
    ax_main = np.array([0.1, 0.1, 0.92, 1])
    cax_main = add_down_cax(ax_main, pad = 0.04, width = 0.02)
    cax_main = fig.add_axes(cax_main)
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':12, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontsize = 12, fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')

    flag = 0
    title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    for path in path_group:
        for node in path:
            data_plt[node[0]][node[1]][node[2]] = [100.0/255, 100.0/255, 100.0/255, 0.8]
            isfilled[node[0]][node[1]][node[2]] = True
            # edge_colors[node[0]][node[1]][node[2]] = 'black'
        data_plt[path[0][0]][path[0][1]][path[0][2]] = [0.0, 0.0, 0.0, 0.8]
        data_plt[path[-1][0]][path[-1][1]][path[-1][2]] = [0.0, 0.0, 0.0, 0.8]

        axes[flag].voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)
        axes[flag].set_title(title_group[flag], color = "black")
        axes[flag].set_xlabel("X ("+str(int(10*x_ratio))+"m)", color = 'grey')
        axes[flag].set_ylabel("Y ("+str(int(10*y_ratio))+"m)", color = 'grey')
        axes[flag].set_zlabel("Z (3m)", color = 'grey')
        axes[flag].view_init(azim = 45)
        # axes[int((flag-flag%2)/2)][flag%2].spines['bottom'].set_color('grey')
        # axes[int((flag-flag%2)/2)][flag%2].spines['left'].set_color('grey')
        # axes[int((flag-flag%2)/2)][flag%2].spines['top'].set_color('grey')
        # axes[int((flag-flag%2)/2)][flag%2].spines['right'].set_color('grey')
        # axes[int((flag-flag%2)/2)][flag%2].tick_params(axis = 'x', colors = 'grey')
        # axes[int((flag-flag%2)/2)][flag%2].tick_params(axis = 'y', colors = 'grey')

        for node in path:
            data_plt[node[0]][node[1]][node[2]] = plt.cm.jet(0.9*(0.6*MAP[node[0]][node[1]][node[2]].risk + \
                                                            0.4*MAP[node[0]][node[1]][node[2]].noise)/data_max)
            isfilled[node[0]][node[1]][node[2]] = False
            data_plt[node[0]][node[1]][node[2]] = map_alpha

        flag += 1

    # 显示图形
    # plt.colorbar()
    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    plt.savefig(f"./Experiments/VoxelPlot/{time_now}_3D_{ER_Weight}_{Enlarge_param}.jpg", transparent = True)
    return


def my_voxel_geoplot(MAP, path, city, with_base = True):
    '''
    One plot.
    This function is to plot 3D version of maps and paths. With real-world data and city outlines.
    '''

    # outline
    urban_district, urban_districts, whole_city = get_outline(city)
    data_max = 0.0
    data_min = float('inf')
    map_alpha = 0.2
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            for k in range(MAP.shape[2]):
                data_max = max(data_max, A*MAP[i][j][k].risk+(1-A)*MAP[i][j][k].noise)
                data_min = min(data_min, A*MAP[i][j][k].risk+(1-A)*MAP[i][j][k].noise)
    data_plt  =  np.array([[[plt.cm.jet((math.log2(A*MAP[x][y][z].risk+(1.0-A)*MAP[x][y][z].noise) - \
                                       math.log2(data_min))/(math.log2(data_max)-math.log2(data_min)))\
                            for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
            for k in range(data_plt.shape[2]):
                data_plt[i][j][k][3] = map_alpha

    # x1, y1, z1  =  np.where(data_plt > =  10e-5)
    x1, y1, z1 = np.indices((data_plt.shape[0]+1, data_plt.shape[1]+1, data_plt.shape[2]+1))
    
    gap = 16
    if with_base == True:
        isfilled = np.array([[[(z-1)%gap == 0 and urban_district.intersects(MAP[x][y][0].geometry) \
                             for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])]) 
    else:
        isfilled = np.array([[[False for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])]) 
    edge_colors = np.array([[[None for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])

    path_alpha = 0.8
    for coord in path:
        data_plt[coord[0]][coord[1]][coord[2]] = [128.0/255, 0.0/255, 128.0/255, path_alpha]
    data_plt[path[0][0]][path[0][1]][path[0][2]] = [0.0, 0.0, 0.0, path_alpha]
    data_plt[path[-1][0]][path[-1][1]][path[-1][2]] = [0.0, 0.0, 0.0, path_alpha]

    for coord in path:
        isfilled[coord[0]][coord[1]][coord[2]] = True
        edge_colors[coord[0]][coord[1]][coord[2]] = 'black'

    # plot 3d
    alpha = 1.0
    fig  =  plt.figure(figsize = [alpha*38.4, alpha*21.6]) #inchs, 1 inch = 200 pixels
    ax  =  fig.add_subplot(111, projection = '3d')
    plt.rcParams.update({"font.size":24})
    # ax.set_title("3D Route Display of Path Planning", fontsize = 20)
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = data_min, vmax = data_max)
    ax_main = np.array([0.2, 0.02, 0.8, 1])
    cax_main = add_down_cax(ax_main, pad = 0.04, width = 0.02)
    cax_main = fig.add_axes(cax_main)
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':20, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # ax.voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = [230.0/255, 230.0/255, 230.0/255, 0.01])
    ax.voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)
    ax.view_init(elev = 13, azim = 20)
    ax.axis('off')

    # 显示图形
    # plt.colorbar()
    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    plt.savefig('./Experiments/VoxelPlot/3D-Route_'+str(time_now)+'.jpg', transparent = True)
    return


def my_voxel_geosubplot(MAP, path_group, city, with_base = True):
    '''
    Subplot.
    This function is to plot 3D version of maps and paths. With real-world data and city outlines.
    '''

    # outline
    urban_district, urban_districts, whole_city = get_outline(city)
    data_max = 0.0
    data_min = float('inf')
    map_alpha = 0.2
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            for k in range(MAP.shape[2]):
                data_max = max(data_max, A*MAP[i][j][k].risk+(1-A)*MAP[i][j][k].noise)
                data_min = min(data_min, A*MAP[i][j][k].risk+(1-A)*MAP[i][j][k].noise)
    data_plt  =  np.array([[[plt.cm.jet((math.log2(A*MAP[x][y][z].risk+(1.0-A)*MAP[x][y][z].noise) - \
                                       math.log2(data_min))/(math.log2(data_max)-math.log2(data_min)))\
                            for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
            for k in range(data_plt.shape[2]):
                data_plt[i][j][k][3] = map_alpha

    # x1, y1, z1  =  np.where(data_plt > =  10e-5)
    x1, y1, z1 = np.indices((data_plt.shape[0]+1, data_plt.shape[1]+1, data_plt.shape[2]+1))
    
    gap = 16
    if with_base == True:
        isfilled = np.array([[[(z-1)%gap == 0 and urban_district.intersects(MAP[x][y][0].geometry) \
                             for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])]) 
    else:
        isfilled = np.array([[[False for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])]) 
    edge_colors = np.array([[[None for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])

    # plot 3d
    alpha = 1.0
    fig  =  plt.figure(figsize = (30.0*alpha, 14.4*alpha)) #inchs, 1 inch = 200 pixels
    axes = []
    k = 0
    for path in path_group:
        ax = fig.add_subplot(1, 3, k+1, projection = '3d')
        axes.append(ax)
        k += 1
    plt.subplots_adjust(left = 0.02, right = 0.90, wspace = 0.0)
    plt.rcParams.update({"font.size":24})
    # ax.set_title("3D Route Display of Path Planning", fontsize = 20)
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = data_min, vmax = data_max)
    cax_main = plt.axes((0.92, 0.3, 0.015, 0.4))
    cax_main = fig.add_axes(cax_main)
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'vertical')
    main_font_dict = {'size':20, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # ax.voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)
    # ax.view_init(elev = 15, azim = 20)
    # ax.axis('off')

    flag = 0
    path_alpha = 0.8
    # title_group = ["Distance Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    for path in path_group:
        for coord in path:
            data_plt[coord[0]][coord[1]][coord[2]] = [128.0/255, 0.0/255, 128.0/255, path_alpha]
        data_plt[path[0][0]][path[0][1]][path[0][2]] = [0.0, 0.0, 0.0, path_alpha]
        data_plt[path[-1][0]][path[-1][1]][path[-1][2]] = [0.0, 0.0, 0.0, path_alpha]
        for coord in path:
            isfilled[coord[0]][coord[1]][coord[2]] = True
            edge_colors[coord[0]][coord[1]][coord[2]] = 'black'

        axes[flag].voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)
        # axes[flag].set_title(title_group[flag], color = "black")
        axes[flag].voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)
        axes[flag].view_init(elev = 13, azim = 20)
        axes[flag].axis('off')

        for node in path:
            data_plt[node[0]][node[1]][node[2]] = plt.cm.jet((math.log2(A*MAP[node[0]][node[1]][node[2]].risk + \
                (1.0-A)*MAP[node[0]][node[1]][node[2]].noise) - math.log2(data_min))/(math.log2(data_max)-math.log2(data_min)))
            isfilled[node[0]][node[1]][node[2]] = (node[2]-1)%gap == 0
            data_plt[node[0]][node[1]][node[2]][3] = map_alpha

        flag += 1

    time_now = time.time()
    plt.savefig(f"./Experiments/VoxelPlot/{time_now}_PathSub3D.jpg", transparent = True)
    return