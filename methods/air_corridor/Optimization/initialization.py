#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Optimization/initialization.py
"""
Module: initialization
This module contains functions to initialize data for pedestrian and building density analysis.
It includes functions to load and preprocess data from CSV files.

Functions:
    init_peo_data(city, n_cpu, csv_index): Initializes pedestrian density data for a given city.
"""

import pandas as pd
import geopandas as gpd
import math

def init_peo_data(city, n_cpu, csv_index):
    """
    Initializes pedestrian density data for a given city.

    Parameters:
        city (str): The name of the city.
        n_cpu (int): Number of CPUs for parallel processing.
        csv_index (int): Index of the CSV file to load.

    Returns:
        list: A list of DataFrames, each containing a chunk of the original data.
    """

    root_path = '.\\Data\\Interim\\Travel\\'
    city_concise = {
        'Beijing': 'bj', 
        'Shanghai': 'sh', 
        'Shenzhen': 'sz', 
        'Chongqing': 'cq', 
        'Guangzhou': 'gz', 
    }
    if city_concise[city]:
        original_source=pd.read_csv(root_path + city + \
            f"\\{city_concise[city]}_user_counts_risk_analysis_20201022_{csv_index}.csv")
    else:
        return
    Len = len(original_source)
    # Len = 1000
    # sum=0
    # for i in range(len(original_source)):
    #     sum+=original_source.loc[i]['user_counts']
    # print(sum)
    chunk_size = int(math.ceil(Len/n_cpu))
    comp_source = [[] for _ in range(n_cpu)]
    for i in range(n_cpu):
        start = chunk_size * i
        end = min(chunk_size*(i+1), Len - 1)
        comp_source[i] = original_source.loc[start:end]
    return comp_source
    # return []


def init_bd_data(city):
    """
    Initializes building data for a given city.

    Parameters:
        city (str): The name of the city.

    Returns:
        list: A DataFrame
    """

    root_path = '.\\Data\\Interim\\Building\\'
    city_concise = {
        'Beijing': 'bj', 
        'Shanghai': 'sh', 
        'Shenzhen': 'sz', 
        'Chongqing': 'cq', 
        'Guangzhou': 'gz', 
    }

    if city_concise[city]:
        buildings_wgs = gpd.read_file(root_path + city + f"_WGS84\\{city}_WGS84.shp")
    else:
        return
    # beijing_buildings=beijing_buildings_wgs[['Elevation','geometry']].loc[320000:340000]
    # beijing_buildings=beijing_buildings.reset_index()
    return buildings_wgs