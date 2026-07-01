#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/dense_plot.py
"""
Module: dense_plot
This module contains functions for plotting density maps related to emergency landing scenarios.
It includes functions to create subplots of density maps with geographic outlines.

Functions:
    my_dense_geosubplot(MAP, city, layers): Creates subplots of density maps with geographic outlines.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from Key_Elements.point_params import A, x_ratio, y_ratio, dz
import pandas as pd
import geopandas as gpd
import time
import math
from Key_Elements.weight import *
import cartopy.crs as ccrs
from cnmaps import draw_map
from shapely.geometry import LineString, Point
from .base_functions import *


def my_dense_plot(MAP, path_group, index):
    """
    Creates subplots of density maps with geographic outlines.

    Parameters:
        MAP (np.array): The 3D array representing the map.
        city (str): The name of the city.
        layers (list): List of layers to plot.

    Returns:
        None
    """
    
    # index = 0, peodens; index = 1, vehdens
    if index == 0:
        data_max = 0.0
        for i in range(MAP.shape[0]):
            for j in range(MAP.shape[1]):
                data_max = max(data_max, 0.5*MAP[i][j][0].risk+0.5*MAP[i][j][0].noise)
        data_plt  =  np.array([[plt.cm.jet(0.9*(0.6*MAP[x][y][0].risk+0.4*MAP[x][y][0].noise)/data_max) \
                              for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    else:
        data_plt  =  np.array([[0.5*MAP[x][y][0].VehDens+0.5*MAP[x][y][0].PeoDens for y in range(MAP.shape[1])] \
                             for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
                data_plt[i][j][3] = 0.6

    # display path 
    flag = 0
    norm_group = []
    for path in path_group:
        z_max_color = 0.0
        z_min_color = float('inf')
        for node in path:
            z_max_color = max(z_max_color, node[2])
            # z_min_color = min(z_min_color, node[2])
        norm = mpl.colors.Normalize(vmin = 0.0, vmax = z_max_color)
        norm_group.append(norm)
        for node in path:
            if flag == 0:
                data_plt[node[0]][node[1]] = plt.cm.Oranges(node[2]/z_max_color)
            elif flag == 1:
                data_plt[node[0]][node[1]] = plt.cm.Greens(node[2]/z_max_color)
            elif flag == 2:
                data_plt[node[0]][node[1]] = plt.cm.Blues(node[2]/z_max_color)
            else:
                data_plt[node[0]][node[1]] = plt.cm.Purples(node[2]/z_max_color)
            data_plt[node[0]][node[1]][3] = 1.0
        flag += 1

    data_plt[path_group[0][0][0]][path_group[0][0][1]] = plt.cm.binary(1.0)
    data_plt[path_group[0][0][0]][path_group[0][0][1]] = plt.cm.binary(1.0)

    """ # set ticks
    x = np.array([i for i in range(data_plt.shape[0])])
    y = np.array([i for i in range(data_plt.shape[1])])
    _X, _Y = np.meshgrid(y, x)
    xticks = np.linspace(clat_max-int(Xborder_min/x_ratio*100)/(xmax-1)*(clat_max-clat_min), \
                       clat_max-int(Xborder_max/x_ratio*100)/(xmax-1)*(clat_max-clat_min), data_plt.shape[0])
    xticks = np.around(xticks, 5)
    xticks = xticks.tolist()
    yticks = np.linspace(clon_min+int(Yborder_min/y_ratio*100)/(ymax-1)*(clon_max-clon_min), \
                       clon_min+int(Yborder_max/y_ratio*100)/(ymax-1)*(clon_max-clon_min), data_plt.shape[1])
    yticks = np.around(yticks, 5)
    yticks = yticks.tolist()"""

    # plot heatmap
    alpha = 0.6
    fig =  plt.figure(figsize = [19.2*alpha, 10.8*alpha]) #inchs, 1 inch = 200 pixels
    # fig, ax = plt.subplots(1, 1, figsize = (19.2*alpha, 10.8*alpha))
    plt.imshow(data_plt)
    # plt.title("Average Cost Threshold: "+str(ACThred))
    plt.title("Optimal Path Planning", color = 'grey')
    plt.rcParams.update({"font.size":12})
    plt.xlabel("X ("+str(int(10*x_ratio))+"m)", color = 'grey')
    plt.ylabel("Y ("+str(int(10*y_ratio))+"m)", color = 'grey')

    """
        add colorbars 
    """
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = 1.1*data_max)
    cmap0 = mpl.cm.Oranges
    cmap1 = mpl.cm.Greens
    cmap2 = mpl.cm.Blues
    cmap3 = mpl.cm.Purples
    fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), orientation = 'horizontal', \
                 label = 'Weighted risk (0~1)')
    fig.colorbar(mpl.cm.ScalarMappable(norm_group[3], cmap = cmap3), orientation = 'vertical', \
                 label = 'Height (m): Overall cost')
    fig.colorbar(mpl.cm.ScalarMappable(norm_group[2], cmap = cmap2), orientation = 'vertical', \
                 label = 'Height (m): Average cost')
    fig.colorbar(mpl.cm.ScalarMappable(norm_group[1], cmap = cmap1), orientation = 'vertical', \
                 label = 'Height (m): Energy (Without threshold)')
    fig.colorbar(mpl.cm.ScalarMappable(norm_group[0], cmap = cmap0), orientation = 'vertical', \
                 label = 'Height (m): Energy (With threshold)')

    """ # plot 3d bar
    X, Y = _X.ravel(), _Y.ravel()
    top = data_plt.ravel()
    bottom = np.zeros_like(top)
    width = 1
    depth = 1
    tmax = 0
    for t in top:
        tmax = max(tmax, t)
    colors = [plt.cm.jet(t/tmax) for t in top]
    ax = fig.add_subplot(111, projection = '3d')
    ax.bar3d(X, Y, bottom, width, depth, top, shade = True, color = colors)
    # set labels
    plt.rcParams.update({"font.size":12})
    plt.tick_params(labelsize = 10)
    ax.set_xlabel('Latitude (\u2218)')
    ax.set_ylabel('Longitude (\u2218)')
    if index == 0:
        ax.set_zlabel('Risk (0~1)')
    else:
        ax.set_zlabel("Density")
    ax.set_title("Cost assessment of drone accident in Beijing")
    # ax.plot_surface(X, Y, data_plt, cmap = 'jet')
    # plt.colorbar()
    plt.show()"""

    plt.waitforbuttonpress()


def my_dense_geoplot(MAP, path = [], city = 'Beijing', with_bound = False, with_path = False, layer = 0):
    # outline
    urban_district, urban_districts, whole_city = get_outline(city)

    # risk data
    data_max = 0.0
    data_min = float('inf')
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            data_max = max(data_max, A*MAP[i][j][layer].risk+(1.0-A)*MAP[i][j][layer].noise)
            data_min = min(data_min, A*MAP[i][j][layer].risk+(1.0-A)*MAP[i][j][layer].noise)
    data_risk  =  [(math.log2(A*MAP[x][y][layer].risk+(1.0-A)*MAP[x][y][layer].noise)-math.log2(data_min)) / \
                 (math.log2(data_max)-math.log2(data_min)) \
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

    # path data
    if with_path == True:
        data_path = [path[i][3] for i in range(len(path))]
        path_geometry = [MAP[path[i][0]][path[i][1]][0].geometry for i in range(len(path))]
        df_path = pd.DataFrame(data = None, columns = ['height', 'geometry'])
        df_path['height'] = np.array(data_path)
        df_path['geometry'] = path_geometry
        path_gpd = gpd.GeoDataFrame(data = df_path, geometry = 'geometry')    
    
    # plot
    alpha = 1.0
    fig  =  plt.figure(figsize = (13.4*alpha, 10.8*alpha))
    ax  =  fig.add_subplot(111, projection = ccrs.PlateCarree())

    # urban_district = [urban_district]
    # df_outline = pd.DataFrame(data = None, columns = ['geometry_outline'])
    # df_outline['geometry_outline'] = urban_district
    # outline_gpd = gpd.GeoDataFrame(data = df_outline, geometry = 'geometry_outline')
    # # mixed_data = gpd.sjoin(data_gpd, outline_gpd, how = 'left', predicate = 'intersects')
    if with_bound == True:
        draw_map(whole_city, ax = ax, linewidth = 0.3, color = 'k', linestyle = '--')
    for i in range(len(urban_districts)):
        draw_map(urban_districts[i], ax = ax, linewidth = 0.3, color = 'w', linestyle = '--')

    data_base_gpd.plot(ax = ax, column = 'risk', cmap = 'jet', edgecolor = None, alpha = 0.3)
    data_gpd.plot(ax = ax, column = 'risk', cmap = 'jet', edgecolor = None, alpha = 0.55)
    if with_path == True:
        path_gpd.plot(ax = ax, column = 'height', cmap = 'RdPu', edgecolor = None, alpha = 1.0)
    ax.axis('off')

    fig.suptitle("Optimal Path Planning ("+city+')', fontsize = 20)
    plt.subplots_adjust(top = 0.9, bottom = 0.2)
    # fig.tight_layout(h_pad = 2)
    """
        add colorbars 
    """
    # for ax in axes.flat:
    #     ax.axis('off')
    plt.rcParams.update({"font.size":12})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = data_min, vmax = data_max)
    if with_path == True:
        cax_main = plt.axes((0.1, 0.1, 0.35, 0.02))
    else:
        cax_main = plt.axes((0.1, 0.1, 0.80, 0.02))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':12, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # plt.subplots_adjust(top = 0.85)
    
    if with_path == True:
        # norm_group = []
        # cmap_group = [mpl.cm.Oranges, mpl.cm.Greens, mpl.cm.Blues, mpl.cm.Purples]
        # title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
        h_max_color = 0.0
        for node in path:
            h_max_color = max(h_max_color, node[3])
        h_norm = mpl.colors.Normalize(vmin = 0.0, vmax = h_max_color)
        h_cmap = mpl.cm.RdPu
        cax_h = plt.axes((0.55, 0.1, 0.35, 0.02))
        h_cbar = fig.colorbar(mpl.cm.ScalarMappable(h_norm, cmap = h_cmap), cax = cax_h, orientation = 'horizontal')
        h_font_dict = {'size':12, "color":"grey"}
        h_cbar.set_label("Height (m)", fontdict = h_font_dict)
        h_cbar.solids.set_edgecolor('face')

    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = round(get_value('Enlarge_param'), 1)
    plt.savefig(f"./Benchmark3/{time_now}_{city}_2D_{(layer+0.5)*dz}m_{ER_Weight}_{Enlarge_param}.jpg", transparent = True)
    return


def my_dense_subplot(MAP, path_group, index):
    # index = 0, risk; index = 1, dense
    if index == 0:
        data_max = 0.0
        for i in range(MAP.shape[0]):
            for j in range(MAP.shape[1]):
                data_max = max(data_max, 0.6*MAP[i][j][0].risk+0.4*MAP[i][j][0].noise)
        data_plt  =  np.array([[plt.cm.jet((0.6*MAP[x][y][0].risk+0.4*MAP[x][y][0].noise)/data_max) \
                              for y in range(MAP.shape[1])] for x in range(MAP.shape[0])])
    else:
        data_plt  =  np.array([[0.5*MAP[x][y][0].VehDens+0.5*MAP[x][y][0].PeoDens for y in range(MAP.shape[1])] \
                             for x in range(MAP.shape[0])])
    for i in range(data_plt.shape[0]):
        for j in range(data_plt.shape[1]):
                data_plt[i][j][3] = 0.6

    # display path 
    alpha = 0.8
    fig, axes = plt.subplots(1, 3, figsize = (19.2*alpha, 6.4*alpha))
    fig.suptitle("Optimal Path Planning", fontsize = 20)
    plt.subplots_adjust(left = 0.1, right = 0.90, top = 0.9, bottom = 0.2, wspace = 0.2)
    # fig.tight_layout(h_pad = 2)
    """
        add colorbars 
    """
    # for ax in axes.flat:
    #     ax.axis('off')
    plt.rcParams.update({"font.size":12})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = 0.0, vmax = data_max)
    cax_main = plt.axes((0.1, 0.1, 0.35, 0.02))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'horizontal')
    main_font_dict = {'size':12, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # plt.subplots_adjust(top = 0.85)
    
    flag = 0
    # norm_group = []
    # cmap_group = [mpl.cm.Oranges, mpl.cm.Greens, mpl.cm.Blues, mpl.cm.Purples]
    title_group = ["Energy Cost Based", "Weighted Cost Based", "Risk Cost Based"]
    h_max_color = 0.0
    for path in path_group:
        for node in path:
            h_max_color = max(h_max_color, node[3])
    h_norm = mpl.colors.Normalize(vmin = 0.0, vmax = h_max_color)
    h_cmap = mpl.cm.cool
    cax_h = plt.axes((0.55, 0.1, 0.35, 0.02))
    h_cbar = fig.colorbar(mpl.cm.ScalarMappable(h_norm, cmap = h_cmap), cax = cax_h, orientation = 'horizontal')
    h_font_dict = {'size':12, "color":"grey"}
    h_cbar.set_label("Height (m)", fontdict = h_font_dict)
    h_cbar.solids.set_edgecolor('face')
    # norm_group.append(norm)
    
    for path in path_group:
        for node in path:
            if flag == 0:
                data_plt[node[0]][node[1]] = plt.cm.cool(node[3]/h_max_color)
            elif flag == 1:
                data_plt[node[0]][node[1]] = plt.cm.cool(node[3]/h_max_color)
            elif flag == 2:
                data_plt[node[0]][node[1]] = plt.cm.cool(node[3]/h_max_color)
            else:
                data_plt[node[0]][node[1]] = plt.cm.cool(node[3]/h_max_color)
            data_plt[node[0]][node[1]][3] = 1.0
        data_plt[path[0][0]][path[0][1]] = plt.cm.binary(1.0)
        data_plt[path[-1][0]][path[-1][1]] = plt.cm.binary(1.0)
        im = axes[flag].imshow(data_plt)
        # cax = add_right_cax(axes[int((flag-flag%2)/2)][flag%2], pad = 0.02, width = 0.02)
        # cbar = fig.colorbar(mpl.cm.ScalarMappable(norm_group[flag], cmap = cmap_group[flag]), cax = cax, orientation = 'vertical')
        # font_dict = {'size':10, "color":"grey"}
        # cbar.set_label("Height (m)", fontdict = font_dict)
        # cbar.solids.set_edgecolor('face')
        # cbar.ax.tick_params(axis = 'both', which = 'both', color = 'green')
        axes[flag].set_title(title_group[flag], color = "black")
        axes[flag].set_xlabel("X ("+str(int(10*x_ratio))+"m)", color = 'grey')
        axes[flag].set_ylabel("Y ("+str(int(10*y_ratio))+"m)", color = 'grey')
        axes[flag].spines['bottom'].set_color('grey')
        axes[flag].spines['left'].set_color('grey')
        axes[flag].spines['top'].set_color('grey')
        axes[flag].spines['right'].set_color('grey')
        axes[flag].tick_params(axis = 'x', colors = 'grey')
        axes[flag].tick_params(axis = 'y', colors = 'grey')

        for node in path:
            data_plt[node[0]][node[1]] = plt.cm.jet((0.6*MAP[node[0]][node[1]][0].risk + \
                                                   0.4*MAP[node[0]][node[1]][0].noise)/data_max)
            data_plt[node[0]][node[1]][3] = 0.6

        flag +=  1

    # plt.show()
    # plt.waitforbuttonpress()
    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    plt.savefig(f"./Benchmark1/{time_now}_2D_{ER_Weight}_{Enlarge_param}.jpg", transparent = True)
    return


def my_dense_geosubplot(MAP, city, layers):
    # outline
    urban_district, urban_districts, whole_city = get_outline(city)

    data_max = 0.0
    data_min = float('inf')
    for i in range(MAP.shape[0]):
        for j in range(MAP.shape[1]):
            for layer in layers:
                data_max = max(data_max, A*MAP[i][j][layer].risk+(1.0-A)*MAP[i][j][layer].noise)
                data_min = min(data_min, A*MAP[i][j][layer].risk+(1.0-A)*MAP[i][j][layer].noise)

    # plot
    alpha = 1.0
    fig  =  plt.figure(figsize = (24.0*alpha, 21.6*alpha))
    # fig.suptitle("Risk Map ("+city+')', fontsize = 20)
    plt.subplots_adjust(left = 0.04, right = 0.91, wspace = 0.05, hspace = 0.07)
    # fig.tight_layout(h_pad = 2)
    """
        add colorbars 
    """
    # for ax in axes.flat:
    #     ax.axis('off')
    plt.rcParams.update({"font.size":24})
    riskcmap = mpl.cm.jet
    risknorm = mpl.colors.Normalize(vmin = data_min, vmax = data_max)
    cax_main = plt.axes((0.94, 0.18, 0.015, 0.6))
    main_cbar = fig.colorbar(mpl.cm.ScalarMappable(risknorm, cmap = riskcmap), cax = cax_main, orientation = 'vertical')
    main_font_dict = {'size':24, "color":"grey"}
    main_cbar.set_label("Risk (0~1)", fontdict = main_font_dict)
    main_cbar.solids.set_edgecolor('face')
    # plt.subplots_adjust(top = 0.85)
    
    axes = []
    k = 0
    for layer in layers:
        ax  =  fig.add_subplot(2, 2, k+1, projection = ccrs.PlateCarree())
        axes.append(ax)
        k +=  1

    k = 0
    for layer in layers:
        # risk data
        data_risk  =  [(math.log2(A*MAP[x][y][layer].risk+(1.0-A)*MAP[x][y][layer].noise)-math.log2(data_min))\
                     (math.log2(data_max)-math.log2(data_min)) \
                            for y in range(MAP.shape[1]) for x in range(MAP.shape[0])]
        data_geometry = [MAP[x][y][0].geometry for y in range(MAP.shape[1]) for x in range(MAP.shape[0])]
        count = 0
        for i in range(len(data_risk)):
            if not urban_district.intersects(data_geometry[i]):
                data_risk[i] = np.nan
                count +=  1
        df = pd.DataFrame(data = None, columns = ['risk', 'geometry'])
        df['risk'] = np.array(data_risk)
        df['geometry'] = data_geometry
        data_gpd = gpd.GeoDataFrame(data = df, geometry = 'geometry') 
        for i in range(len(urban_districts)):
            draw_map(urban_districts[i], ax = axes[k], linewidth = 0.3, color = 'w', linestyle = '--')
        data_gpd.plot(ax = axes[k], column = 'risk', cmap = 'jet', edgecolor = None, alpha = 0.8)
        # axes[k].set_title('Height: '+str((layer+0.5)*dz)+'m', fontsize = 28, color = "black")
        axes[k].axis('off')

        k +=  1

    # plt.show()
    # plt.waitforbuttonpress()

    time_now = time.time()
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = round(get_value('Enlarge_param'), 1)
    plt.savefig(f"./Experiments/DensePlot/{time_now}_{city}Sub2D_{ER_Weight}_{Enlarge_param}.jpg", transparent = True)
    return