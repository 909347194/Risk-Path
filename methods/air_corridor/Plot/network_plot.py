#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/network_plot.py
"""
Module: network_plot
This module contains functions for plotting 2D networks related to emergency landing scenarios.
It includes functions to plot networks based on synthesized data.

Functions:
    my_network_plot(MAP, path_group, index): Plots a 2D network using synthesized data.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from Key_Elements.point_params import x_ratio, y_ratio, A
import pandas as pd
import geopandas as gpd
import time
import math
from Key_Elements.weight import  * 
import cartopy.crs as ccrs
from cnmaps import draw_map
from shapely.geometry import LineString, Point
from .base_functions import  * 


def my_network_plot(MAP, path_group, index):
    """
    Plots a 2D network using synthesized data.

    Parameters:
        MAP (np.array): The 3D array representing the map.
        path_group (list): List of paths, where each path is a list of nodes.
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
                data_max = max(data_max, 0.6 * MAP[i][j][0].risk + 0.4 * MAP[i][j][0].noise)
        data_plt  =  np.array([[plt.cm.jet(0.9 * (0.6 * MAP[x][y][0].risk + 0.4 * MAP[x][y][0].noise) / data_max) \
                              for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    else:
        data_plt  =  np.array([[0.5 * MAP[x][y][0].VehDens + 0.5 * MAP[x][y][0].PeoDens for y in range(MAP.shape[1])] \
                             for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
                data_plt[i][j][3] = 0.6
    
    # display path
    title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    alpha = 1.0
    fig, ax = plt.subplots(figsize = (14.4 * alpha, 10.8 * alpha))
    ax.set_title("Flight Network (" + str(title_group[1]) + ')', fontsize = 20)

    """
        add colorbars 
    """
    plt.rcParams.update({"font.size":16})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = 1.1 * data_max)
    cax_main = plt.axes((0.05, 0.115, 0.02, 0.76))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'vertical')
    main_font_dict = {'size':15, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    
    # norm_group = []
    # cmap_group = [mpl.cm.Oranges, mpl.cm.Greens, mpl.cm.Blues, mpl.cm.Purples]

    h_max_color = 0.0
    for path in path_group:
        for node in path:
            h_max_color = max(h_max_color, node[3])
    h_norm = mpl.colors.Normalize(vmin = 0.0, vmax = h_max_color)
    h_cmap = mpl.cm.cool
    cax_h = plt.axes((0.88, 0.115, 0.02, 0.76))
    h_cbar = fig.colorbar(mpl.cm.ScalarMappable(h_norm, cmap = h_cmap), cax = cax_h, orientation = 'vertical')
    h_font_dict = {'size':16, "color":"grey"}
    h_cbar.set_label("Height (m)", fontdict = h_font_dict)
    h_cbar.solids.set_edgecolor('face')

    for path in path_group:
        for node in path:
            data_plt[node[0]][node[1]] = plt.cm.cool(node[3] / h_max_color)
            data_plt[node[0]][node[1]][3] = 1.0
            # ax.arrow(node[0], node[1], 1, 1, width = 0.5, overhang = 0.2, \
            #      fc = 'b', ec = None)
        data_plt[path[0][0]][path[0][1]] = plt.cm.binary(1.0)
        data_plt[path[ - 1][0]][path[ - 1][1]] = plt.cm.binary(1.0)
        # ax.arrow(path[6][0], path[6][1], path[7][0] - path[6][0], path[7][1] - path[6][1], width = 0.5, overhang = 0.2, \
        #          fc = 'b', ec = None)
    im = ax.imshow(data_plt)
    ax.set_xlabel("X (" + str(int(10 * x_ratio)) + "m)", color = 'grey', )
    ax.set_ylabel("Y (" + str(int(10 * y_ratio)) + "m)", color = 'grey')
    ax.spines['bottom'].set_color('grey')
    ax.spines['left'].set_color('grey')
    ax.spines['top'].set_color('grey')
    ax.spines['right'].set_color('grey')
    ax.tick_params(axis = 'x', colors = 'grey')
    ax.tick_params(axis = 'y', colors = 'grey')

    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    # plt.savefig('. / Benchmark1 / ' + str(time_now) + '_Network_' + str(ER_Weight) + '_' + str(Enlarge_param) + '.jpg', transparent = True)
    return

def my_network_plot_3d(MAP, path_group):
    '''
    This function is to plot 3D networks. With synthesized data as well.
    '''

    data_max  =  0.0
    map_alpha  =  0.17
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            for k in range(MAP.shape[2]):
                data_max  =  max(data_max, 0.6 * MAP[i][j][k].risk + 0.4 * MAP[i][j][k].noise)
    data_plt  =  np.array([[[plt.cm.jet(0.9 * (0.6 * MAP[x][y][z].risk + 0.4 * MAP[x][y][z].noise) / data_max) \
                           for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
            for k in range(data_plt.shape[2]):
                data_plt[i][j][k][3]  =  map_alpha

    # x1, y1, z1  =  np.where(data_plt > =  10e - 5)
    x1, y1, z1 = np.indices((data_plt.shape[0] + 1, data_plt.shape[1] + 1, data_plt.shape[2] + 1))
    
    gap = 7
    isfilled = np.array([[[z%gap == 0 for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] \
                       for x in range(MAP.shape[0])]) 
    edge_colors = np.array([[[None for z in range(MAP.shape[2])] for y in range(MAP.shape[1])] \
                          for x in range(MAP.shape[0])])

    title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    # plot 3d
    alpha = 1.0
    fig = plt.figure(figsize = (10.8 * alpha, 10.8 * alpha))
    ax = fig.add_subplot(1, 1, 1, projection = '3d')
    ax.set_title("Flight Network 3D (" + str(title_group[1]) + ')', fontsize = 20)
    plt.rcParams.update({"font.size":16})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = 1.1 * data_max)
    cax_main = plt.axes((0.1, 0.1, 0.8, 0.02))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':16, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')

    for path in path_group:
        for node in path:
            data_plt[node[0]][node[1]][node[2]] = [100.0 / 255, 100.0 / 255, 100.0 / 255, 0.8]
            isfilled[node[0]][node[1]][node[2]] = True
            # edge_colors[node[0]][node[1]][node[2]] = 'black'
        data_plt[path[0][0]][path[0][1]][path[0][2]] = [0.0, 0.0, 0.0, 0.8]
        data_plt[path[ - 1][0]][path[ - 1][1]][path[ - 1][2]] = [0.0, 0.0, 0.0, 0.8]

    ax.voxels(x1, y1, z1, isfilled, facecolors = data_plt, edgecolors = None)
    ax.set_title(title_group[1], color = "black")
    ax.set_xlabel("X (" + str(int(10 * x_ratio)) + "m)", color = 'grey')
    ax.set_ylabel("Y (" + str(int(10 * y_ratio)) + "m)", color = 'grey')
    ax.set_zlabel("Z (3m)", color = 'grey')
    ax.view_init(azim = 45)

    # plt.colorbar()
    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    # plt.savefig('. / Benchmark1 / ' + str(time_now) + '_Network3D_' + str(ER_Weight) + '_' + str(Enlarge_param) + '.jpg', transparent = True)
    return

def my_network_geoplot(MAP, path_group, city):
    '''
    This function is to plot 3D networks, while with real - world data and city outlines.
    '''

    # outline
    urban_district, urban_districts, whole_city = get_outline(city)

    # risk data
    data_max = 0.0
    data_min = float('inf')
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            data_max = max(data_max, A * MAP[i][j][0].risk + (1.0 - A) * MAP[i][j][0].noise)
            data_min = min(data_min, A * MAP[i][j][0].risk + (1.0 - A) * MAP[i][j][0].noise)
    data_risk  =  [(math.log2(A * MAP[x][y][0].risk + (1.0 - A) * MAP[x][y][0].noise) - math.log2(data_min))  /  \
                 (math.log2(data_max) - math.log2(data_min)) \
                          for y in range(MAP.shape[1]) for x in range(MAP.shape[0])]
    data_geometry = [MAP[x][y][0].geometry for y in range(MAP.shape[1]) for x in range(MAP.shape[0])]
    
    df_base = pd.DataFrame(data = None, columns = ['risk', 'geometry'])
    df_base['risk'] = np.array(data_risk)
    df_base['geometry'] = data_geometry
    data_base_gpd = gpd.GeoDataFrame(data = df_base, geometry = 'geometry')   
    for i in range(len(data_risk)):
        if not urban_district.intersects(data_geometry[i]):
            data_risk[i] = np.nan
    df = pd.DataFrame(data = None, columns = ['risk', 'geometry'])
    df['risk'] = np.array(data_risk)
    df['geometry'] = data_geometry
    data_gpd = gpd.GeoDataFrame(data = df, geometry = 'geometry') 
    
    # plot
    alpha = 1.0
    fig  =  plt.figure(figsize = (26.8 * alpha, 21.6 * alpha))
    ax = fig.add_subplot(111, projection = ccrs.PlateCarree())
    # fig.suptitle("Risk Map (" + city + ')', fontsize = 20)
    # plt.subplots_adjust(left = 0.06, right = 0.92, wspace = 0.02)
    # fig.tight_layout(h_pad = 2)
    """
        add colorbars 
    """
    # for ax in axes.flat:
    #     ax.axis('off')
    plt.rcParams.update({"font.size":24})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = data_min, vmax = data_max)
    cax_main = plt.axes((0.91, 0.25, 0.015, 0.5))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'vertical')
    main_font_dict = {'size':30, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # plt.subplots_adjust(top = 0.85)
    

    h_max_color = 0.0
    for path in path_group:
        for node in path:
            h_max_color = max(h_max_color, node[3])
    h_norm = mpl.colors.Normalize(vmin = 0.0, vmax = h_max_color)
    h_cmap = mpl.cm.cool
    cax_h = plt.axes((0.07, 0.25, 0.015, 0.5))
    h_cbar = fig.colorbar(mpl.cm.ScalarMappable(h_norm, cmap = h_cmap), cax = cax_h, orientation = 'vertical')
    h_font_dict = {'size':30, "color":"grey"}
    h_cbar.set_label("Height (m)", fontdict = h_font_dict)
    h_cbar.solids.set_edgecolor('face')

    data_base_gpd.plot(ax = ax, column = 'risk', cmap = 'jet', edgecolor = None, alpha = 0.3)
    data_gpd.plot(ax = ax, column = 'risk', cmap = 'jet', edgecolor = None, alpha = 0.55)
    for i in range(len(urban_districts)):
        draw_map(urban_districts[i], ax = ax, linewidth = 1.0, color = 'w', linestyle = '--')
    for path in path_group:
        # path data
        data_path = [path[i][3] for i in range(len(path) - 1)]
        # data_path.append(path[ - 1][3])
        # path_geometry = [MAP[path[0][0]][path[0][1]][0].geometry]
        path_geometry = []
        lines = [LineString([(0.5 * (MAP[path[i][0]][path[i][1]][0].geometry.bounds[0] + \
                                 MAP[path[i][0]][path[i][1]][0].geometry.bounds[2]), \
                        0.5 * (MAP[path[i][0]][path[i][1]][0].geometry.bounds[1] + \
                             MAP[path[i][0]][path[i][1]][0].geometry.bounds[3])), \
                            (0.5 * (MAP[path[i + 1][0]][path[i + 1][1]][0].geometry.bounds[0] + \
                                  MAP[path[i + 1][0]][path[i + 1][1]][0].geometry.bounds[2]), \
                        0.5 * (MAP[path[i + 1][0]][path[i + 1][1]][0].geometry.bounds[1] + \
                             MAP[path[i + 1][0]][path[i + 1][1]][0].geometry.bounds[3]))]) for i in range(len(path) - 1)]
        path_geometry = path_geometry + lines
        # path_geometry.append(MAP[path[ - 1][0]][path[ - 1][1]][0].geometry)
        df_path = pd.DataFrame(data = None, columns = ['height', 'geometry'])
        df_path['height'] = np.array(data_path)
        df_path['geometry'] = path_geometry
        path_gpd = gpd.GeoDataFrame(data = df_path, geometry = 'geometry')   
        path_gpd.plot(ax = ax, column = 'height', cmap = 'cool', edgecolor = None, linewidth = 4.0, alpha = 1.0)

        od_path = [1, 1, 0]
        clon_o = 0.5 * (MAP[path[0][0]][path[0][1]][0].geometry.bounds[0] + MAP[path[0][0]][path[0][1]][0].geometry.bounds[2])
        clat_o = 0.5 * (MAP[path[0][0]][path[0][1]][0].geometry.bounds[1] + MAP[path[0][0]][path[0][1]][0].geometry.bounds[3])
        clon_d = 0.5 * (MAP[path[ - 1][0]][path[ - 1][1]][0].geometry.bounds[0] + MAP[path[ - 1][0]][path[ - 1][1]][0].geometry.bounds[2])
        clat_d = 0.5 * (MAP[path[ - 1][0]][path[ - 1][1]][0].geometry.bounds[1] + MAP[path[ - 1][0]][path[ - 1][1]][0].geometry.bounds[3])
        radius = abs(clon_o - MAP[path[0][0]][path[0][1]][0].geometry.bounds[0]) * 3.0
        od_geometry = [Point(clon_o, clat_o).buffer(radius), Point(clon_d, clat_d).buffer(radius), \
                     Point(clon_d, clat_d).buffer(0.000001)]
        df_od = pd.DataFrame(data = None, columns = ['height', 'geometry'])
        df_od['height'] = np.array(od_path)
        df_od['geometry'] = od_geometry
        od_gpd = gpd.GeoDataFrame(df_od, geometry = 'geometry')
        od_gpd.plot(ax = ax, column = 'height', cmap = 'binary', edgecolor = None, alpha = 1.0)

        # o = (MAP[path[int(0.25 * len(path))][0]][path[int(0.25 * len(path))][1]][0].geometry.bounds[0], \
        #    MAP[path[int(0.25 * len(path))][0]][path[int(0.25 * len(path))][1]][0].geometry.bounds[1])
        # d = (MAP[path[int(0.25 * len(path)) + 1][0]][path[int(0.25 * len(path)) + 1][1]][0].geometry.bounds[0], \
        #    MAP[path[int(0.25 * len(path)) + 1][0]][path[int(0.25 * len(path)) + 1][1]][0].geometry.bounds[1])
        # ax.quiver(o[0], d[0], o[1], d[1], color = (1.0, 0.65, 0.0, 0.8), linewidth = 4.0)
    
    
    ax.axis('off')


    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    # ER_Weight = get_value('ER_Weight')
    # Enlarge_param = get_value('Enlarge_param')

    # plt.savefig('. / Benchmark3 / ' + str(time_now) + '_Network_' + city + '.jpg', transparent = True)

    return