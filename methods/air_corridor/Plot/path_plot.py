#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/path_plot.py
"""
Module: path_plot
This module contains functions for plotting paths related to emergency landing scenarios.
It includes functions to plot heatmaps and paths with real-world data and city outlines.

Functions:
    my_path_geosubplot(MAP, path_group, city): Plots the heatmap and paths with real-world data and city outlines.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from Key_Elements.point_params import A
import pandas as pd
import geopandas as gpd
import time
import math
from Key_Elements.weight import *
import cartopy.crs as ccrs
from cnmaps import draw_map
from shapely.geometry import LineString, Point
from .base_functions import *


def my_path_geosubplot(MAP, path_group, city, emergency_stations=None):
    """
    Plots the heatmap and paths with real-world data and city outlines.

    Parameters:
        MAP (np.array): The 3D array representing the map.
        path_group (list): List of paths, where each path is a list of nodes.
        city (str): The name of the city.

    Returns:
        None
    """

    # outline
    urban_district, urban_districts, whole_city = get_outline(city)

    # risk data
    data_max = 0.0
    data_min = float('inf')
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            data_max = max(data_max, A*MAP[i][j][0].risk+(1.0-A)*MAP[i][j][0].noise)
            data_min = min(data_min, A*MAP[i][j][0].risk+(1.0-A)*MAP[i][j][0].noise)
    data_risk = [(math.log2(A*MAP[x][y][0].risk+(1.0-A)*MAP[x][y][0].noise)-math.log2(data_min)) / \
                 (math.log2(data_max)-math.log2(data_min)) \
                          for y in range(MAP.shape[1]) for x in range(MAP.shape[0])]
    data_geometry = [MAP[x][y][0].geometry for y in range(MAP.shape[1]) for x in range(MAP.shape[0])]
    count = 0
    for i in range(len(data_risk)):
        if not urban_district.intersects(data_geometry[i]):
            data_risk[i] = np.nan
            count += 1
    df = pd.DataFrame(data = None, columns = ['risk', 'geometry'])
    df['risk'] = np.array(data_risk)
    df['geometry'] = data_geometry
    data_gpd = gpd.GeoDataFrame(data = df, geometry = 'geometry') 
    
    # plot
    alpha = 1.0
    fig = plt.figure(figsize = (38.4*alpha, 11.0*alpha))
    # fig.suptitle("Risk Map ("+city+')', fontsize = 20)
    plt.subplots_adjust(left = 0.06, right = 0.92, wspace = 0.02)
    # fig.tight_layout(h_pad = 2)
    """
        add colorbars 
    """
    # for ax in axes.flat:
    #     ax.axis('off')
    plt.rcParams.update({"font.size":24})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = data_min, vmax = data_max)
    cax_main = plt.axes((0.94, 0.18, 0.015, 0.64))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'vertical')
    main_font_dict = {'size':24, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # plt.subplots_adjust(top = 0.85)
    
    # norm_group = []
    # cmap_group = [mpl.cm.Oranges, mpl.cm.Greens, mpl.cm.Blues, mpl.cm.Purples]
    # title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    h_max_color = 0.0
    for path in path_group:
        for node in path:
            h_max_color = max(h_max_color, node[3])
    h_norm = mpl.colors.Normalize(vmin = 0.0, vmax = h_max_color)
    h_cmap = mpl.cm.cool
    cax_h = plt.axes((0.01, 0.18, 0.015, 0.64))
    h_cbar = fig.colorbar(mpl.cm.ScalarMappable(h_norm, cmap = h_cmap), cax = cax_h, orientation = 'vertical')
    h_font_dict = {'size':24, "color":"grey"}
    h_cbar.set_label("Height (m)", fontdict = h_font_dict)
    h_cbar.solids.set_edgecolor('face')



    axes = []
    k = 0
    title_group = ["Distance Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    for path in path_group:
        ax = fig.add_subplot(1, 3, k+1, projection = ccrs.PlateCarree())
        axes.append(ax)
        k += 1

    k = 0
    for path in path_group:
        # # plot arrow
        # o = (MAP[path[int(0.25*len(path))][0]][path[int(0.25*len(path))][1]][0].geometry.bounds[0], \
        #    MAP[path[int(0.25*len(path))][0]][path[int(0.25*len(path))][1]][0].geometry.bounds[1])
        # d = (MAP[path[int(0.25*len(path))+2][0]][path[int(0.25*len(path))+2][1]][0].geometry.bounds[0], \
        #    MAP[path[int(0.25*len(path))+2][0]][path[int(0.25*len(path))+2][1]][0].geometry.bounds[1])
        # x = np.array([o[0], d[0]])
        # y = np.array([o[1], d[1]])
        # x2d, y2d = np.meshgrid(x, y)
        # u = x2d
        # v = y2d
        # crs = ccrs.RotatedPole(pole_longitude = o[0], pole_latitude = o[1])
        # axes[k].quiver(x2d, y2d, u, v, color = (1.0, 0.65, 0.0, 0.8), linewidth = 4.0, transform = crs)

        # path data
        data_path = [path[i][3] for i in range(len(path)-1)]
        # data_path.append(path[-1][3])
        # path_geometry = [MAP[path[0][0]][path[0][1]][0].geometry]
        path_geometry = []
        lines = [LineString([(0.5*(MAP[path[i][0]][path[i][1]][0].geometry.bounds[0] + \
                                   MAP[path[i][0]][path[i][1]][0].geometry.bounds[2]), \
                        0.5*(MAP[path[i][0]][path[i][1]][0].geometry.bounds[1] + \
                             MAP[path[i][0]][path[i][1]][0].geometry.bounds[3])), \
                            (0.5*(MAP[path[i+1][0]][path[i+1][1]][0].geometry.bounds[0] + \
                                  MAP[path[i+1][0]][path[i+1][1]][0].geometry.bounds[2]), \
                        0.5*(MAP[path[i+1][0]][path[i+1][1]][0].geometry.bounds[1] + \
                             MAP[path[i+1][0]][path[i+1][1]][0].geometry.bounds[3]))]) for i in range(len(path)-1)]
        path_geometry = path_geometry+lines
        # path_geometry.append(MAP[path[-1][0]][path[-1][1]][0].geometry)
        df_path = pd.DataFrame(data = None, columns = ['height', 'geometry'])
        df_path['height'] = np.array(data_path)
        df_path['geometry'] = path_geometry
        path_gpd = gpd.GeoDataFrame(data = df_path, geometry = 'geometry')   
        for i in range(len(urban_districts)):
            draw_map(urban_districts[i], ax = axes[k], linewidth = 0.5, color = 'w', linestyle = '--')
        data_gpd.plot(ax = axes[k], column = 'risk', cmap = 'jet', edgecolor = None, alpha = 0.55)
        path_gpd.plot(ax = axes[k], column = 'height', cmap = 'cool', edgecolor = None, linewidth = 4.0, alpha = 1.0)

        # plot OD
        od_path = [1, 1, 0]
        clon_o = 0.5*(MAP[path[0][0]][path[0][1]][0].geometry.bounds[0] + \
                      MAP[path[0][0]][path[0][1]][0].geometry.bounds[2])
        clat_o = 0.5*(MAP[path[0][0]][path[0][1]][0].geometry.bounds[1] + \
                      MAP[path[0][0]][path[0][1]][0].geometry.bounds[3])
        clon_d = 0.5*(MAP[path[-1][0]][path[-1][1]][0].geometry.bounds[0] + \
                      MAP[path[-1][0]][path[-1][1]][0].geometry.bounds[2])
        clat_d = 0.5*(MAP[path[-1][0]][path[-1][1]][0].geometry.bounds[1] + \
                      MAP[path[-1][0]][path[-1][1]][0].geometry.bounds[3])
        radius = abs(clon_o-MAP[path[0][0]][path[0][1]][0].geometry.bounds[0])*3.0
        od_geometry = [Point(clon_o, clat_o).buffer(radius), Point(clon_d, clat_d).buffer(radius), \
                       Point(clon_d, clat_d).buffer(0.000001)]
        df_od = pd.DataFrame(data = None, columns = ['height', 'geometry'])
        df_od['height'] = np.array(od_path)
        df_od['geometry'] = od_geometry
        od_gpd = gpd.GeoDataFrame(df_od, geometry = 'geometry')
        od_gpd.plot(ax = axes[k], column = 'height', cmap = 'binary', edgecolor = None, alpha = 1.0)

        # axes[k].set_title(title_group[k], color = "black")
        axes[k].axis('off')

        k += 1

    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    er_weight_distance = get_value('ER_Weight_Distance')
    er_weight_rescue = get_value('ER_Weight_Rescue')
    enlarge_param_tpr = get_value('Enlarge_param_TPR')
    enlarge_param_rescue = get_value('Enlarge_param_Rescue')
    plt.savefig(f"./Experiments/PathPlot/{time_now}_{city}_PathSub2D_{er_weight_distance}_{er_weight_rescue}.jpg", \
                transparent = True)
    return
