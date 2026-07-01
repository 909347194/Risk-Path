#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Dara_Process/preprocess.py
"""
Module: preprocess.py
This module contains functions for preprocessing data related to grid coordinates.
It includes functions to add detailed grid coordinates to a dataframe and to calculate
the Haversine distance between two points on Earth.

Functions:
    get_coordinate(df): Adds detailed grid coordinates to a dataframe.
    get_clatclon(grid_id): Returns the center latitude and longitude of a grid.
    haversine_distance(lat1, lon1, lat2, lon2): Calculates the distance between two points on Earth.
"""

import math

def get_coordinate(df):
    '''
    @Info: this is a function to add detailed grid coordinates to a 
        dataframe containing only the grid id information
    @Para: df, a pandas dataframe containing the col named 'grid_id',
        which is the id of grids with a side length of approximately
        10 m, and starting from (18.163240 N, 73.451 E).
    @Return: df, modified input
    @NOTE: the input WILL be modified, if you do not wish to modify 
        your input, send in a copy.
    '''
    df['lat_min'] = df['grid_id'] // 614258 * 0.0001 + 18.163240
    df['lat_max'] = df['lat_min'] + 0.0001
    df['lon_min'] = df['grid_id'] % 614258 * 0.0001 + 73.451000
    df['lon_max'] = df['lon_min'] + 0.0001
    df['clat'] = df['lat_min'] + 0.00005
    df['clon'] = df['lon_min'] + 0.00005
    return df

def get_clatclon(grid_id):
    ''' Get the center latitude and longitude of a grid. '''
    lat_min = grid_id // 614258 * 0.0001 + 18.163240
    lon_min = grid_id % 614258 * 0.0001 + 73.451000
    clat = lat_min + 0.00005
    clon = lon_min + 0.00005
    return (clat,clon)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth specified in
    latitude and longitude using the Haversine formula.

    Parameters:
    lat1 (float): Latitude of the first point in degrees.
    lon1 (float): Longitude of the first point in degrees.
    lat2 (float): Latitude of the second point in degrees.
    lon2 (float): Longitude of the second point in degrees.

    Returns:
    float: Distance between the two points in kilometers.
    """
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Radius of the Earth in kilometers
    radius = 6371.0

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Calculate the distance
    distance = radius * c
    return distance
