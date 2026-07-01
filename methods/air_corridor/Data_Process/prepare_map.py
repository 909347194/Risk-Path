#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Dara_Process/prepare_map.py
"""
This module prepares the map for emergency landing simulations.
It includes functions to save and load the map, and preprocess the data.
"""

# import sources
import os
import sys
import multiprocessing
import threading
import pickle
import pandas as pd
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .preprocess import get_coordinate
from .map_generation import init_map
from Optimization.initialization import init_bd_data, init_peo_data
from Optimization.coord_transform import grid_to_xy_bd, grid_to_xy_pd
from Key_Elements.point_params import x_ratio, y_ratio

def save_map(map_3d, filename):
    """Save the map to a file."""
    with open(filename, 'wb') as file:
        pickle.dump(map_3d, file)

def load_map(filename):
    """Load the map from a file."""
    with open(filename, 'rb') as file:
        map_3d = pickle.load(file)
    return map_3d


def prepare_map(params):
    """
    Preprocess the data to save following running time.
    
    Parameters:
        n_cpu (int): Number of processing CPUs.
        city (str): Which city.
        with_building (bool): Whether to contain building data.
    """

    # params
    n_cpu = params['Num of CPU']
    city = params['city']
    with_building = params['WITH_BUILDING']

    """Initialization"""
    # Comprehensive data sources
    comp_source = init_peo_data(city, n_cpu, params['Index_of_csv'])

    # Whether to add building data
    if with_building == True:
        building_source = init_bd_data(city)

    print("Init completed!")


    """get lon and lat for every grid"""
    # to store the process data of comp_source
    ll_source = [[] for i in range(len(comp_source))]

    if multiprocessing.current_process().daemon:
        # Use threading for parallelism
        threads = []
        for i in range(len(comp_source)):
            t = threading.Thread(target=lambda idx: ll_source.__setitem__(idx, \
                                get_coordinate(comp_source[idx])), args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    else:
        result1 = []
        pool1 = multiprocessing.Pool(processes=n_cpu)
        for i in range(len(comp_source)):
            # compute latitude and longitude
            result1.append(pool1.apply_async(get_coordinate, (comp_source[i], )))
        pool1.close()
        pool1.join()
        for i in range(len(comp_source)):
            ll_source[i] = result1[i].get()


    # to concat all the data frames together
    df_ll = pd.DataFrame(data = None, columns = ll_source[0].columns)
    for df in ll_source:
        df_ll = pd.concat([df_ll,df], ignore_index = True)
    df_ll = df_ll.reset_index()
    print("Preprocess completed!")


    """grid to (x,y,z)"""
    # the bounds of latitude and longitude
    clat_max = df_ll['clat'].max()
    clon_min = df_ll['clon'].min()

    # xyz_people_dense=[]
    # xyz_pd=[[] for i in range(n_cpu)]
    # result2=[]
    # pool2=multiprocessing.Pool(processes=n_cpu)
    # for i in range(n_cpu):
    #     result2.append(pool2.apply_async(grid_to_xy,(ll_source[i],xyz_pd[i],clon_min,clat_max,)))
    # pool2.close()
    # pool2.join()
    # for r in result2:
    #     xyz_people_dense=xyz_people_dense+r.get()

    # Transform (lon, lat, height) to (x, y, z) coordinates.
    # Contain data of dense of people.
    # 7-element tuple: (x, y, z, user_counts_walk, user_counts_drive, clat, clon)
    xyz_people_dense = grid_to_xy_pd(df_ll, clon_min, clat_max)

    # Contain data of buildings.
    if with_building == True:
        # 7-element tuple: (x, y, z, surface of area, height, clat, clon)
        xyz_building = grid_to_xy_bd(building_source, clon_min, clat_max)
    else:
        xyz_building = []
    print('Grid_id to (x,y,z) completed')

    """
    assess risk & noise & buildings of (x,y,z)
    10 * xratio m * 10 * yratio m
    """
    # map_3d,xmax,ymax,zmax=init_map(x_ratio,y_ratio,xyz_people_dense)
    # map_3d, map_3d[x][y][z]   3-D array: Each element is a Point object.
    map_3d = init_map(x_ratio, y_ratio, xyz_people_dense, xyz_building, clat_max, clon_min, with_building,
            alpha_f=params['Fatality_weight'], alpha_b=params['Property_weight'], alpha_n=params['Noise_weight'])
    print("Map ready!")


    # Select domain
    # Set borders
    # Revise!!!!
    city_borders = {
        'Beijing':  (0.55, 0.82, 0.28, 0.60),
        'Shanghai': (0.0, 1.0, 0.0, 1.0), 
        'Chongqing': (0.578, 0.731, 0.189, 0.3116), 
        'Guangzhou': (0.383, 0.504, 0.450, 0.525), 
        'Shenzhen': (0.49, 0.59, 0.542, 0.669), 
    }
    if city_borders[city]:
        border = city_borders[city]
    else:
        border = (0.0, 1.0, 0.0, 1.0)

    # Clip map_3d (Place of Interest)
    # field, field[x][y][z]   3-D array: Each element is a Point object.
    field = [[[map_3d[x][y][z] for z in range(map_3d.shape[2])] for y in range(int(map_3d.shape[1]*border[2]), \
        int(map_3d.shape[1]*border[3]),1)] for x in range(int(map_3d.shape[0]*border[0]), int(map_3d.shape[0]*border[1]),1)]
    field = np.array(field)


    root_path = params['root_path']
    save_map(field, root_path + f"{params['city']}\\CsvNum_{params['Index_of_csv']}_WithBuilding_{params['WITH_BUILDING']}"
        + f"_Fatality_{params['Fatality_weight']}_Property_{params['Property_weight']}_Noise_{params['Noise_weight']}.pkl")

    return
