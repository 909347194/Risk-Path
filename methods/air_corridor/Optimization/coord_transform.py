#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Optimization/coord_transform.py
"""
Module: coord_transform
This module contains functions to transform geographic coordinates (longitude, latitude, height)
to Cartesian coordinates (x, y, z). It includes functions to handle data related to pedestrian
densities and building information.

Functions:
    grid_to_xy_pd(df_ll, clon_min, clat_max): Transforms (lon, lat, height) to (x, y, z) coordinates
        for pedestrian density data.
    grid_to_xy_bd(df, clon_min, clat_max): Transforms (lon, lat, height) to (x, y, z) coordinates
        for building data.
"""

def grid_to_xy_pd(df_ll, clon_min, clat_max):
    '''
    Transform (lon, lat, height) to (x, y, z) coordinates.
    Contain data of dense of people.
    7-element tuple: (x, y, z, user_counts_walk, user_counts_drive, clat, clon)

    Parameters:
        df_ll (DataFrame): DataFrame containing longitude, latitude, and user counts.
        clon_min (float): Minimum longitude for the transformation.
        clat_max (float): Maximum latitude for the transformation.

    Returns:
        list: List of tuples containing transformed coordinates and user counts.
    '''

    xyz_pd=[]
    for i in range(len(df_ll)):
        if df_ll.loc[i]['mode'] == 'pt_drive':
            tup = (df_ll.loc[i]['clat'], df_ll.loc[i]['clon'], 0, df_ll.loc[i]['user_counts'])
        else:
            tup = (df_ll.loc[i]['clat'], df_ll.loc[i]['clon'], df_ll.loc[i]['user_counts'], 0)
        x = int(abs(tup[0] - clat_max) / 1.0e-4)
        y = int(abs(tup[1] - clon_min) / 1.0e-4)
        xyz_tup = (x, y, 0, tup[2], tup[3], tup[0], tup[1])
        xyz_pd.append(xyz_tup)
    return xyz_pd


def grid_to_xy_bd(df, clon_min, clat_max):
    '''
    Transform (lon, lat, height) to (x, y, z) coordinates.
    Contain data of buildings.
    7-element tuple: (x, y, z, surface of area, height, clat, clon)

    Parameters:
        df (DataFrame): DataFrame containing building geometry data.
        clon_min (float): Minimum longitude for the transformation.
        clat_max (float): Maximum latitude for the transformation.

    Returns:
        list: List of tuples containing transformed coordinates and building data.
    '''
    xyz_bd = []
    for i in range(len(df)):
        clon = 0.5 * (df.loc[i]['geometry'].bounds[0] + df.loc[i]['geometry'].bounds[2])
        clat = 0.5 * (df.loc[i]['geometry'].bounds[1] + df.loc[i]['geometry'].bounds[3])
        area = float(df.loc[i]['geometry'].area * (3.1416 / 180.0 * 6371.0 * 1e3) ** 2)
        height = df.loc[i]['height']
        x = int(abs(clat - clat_max) / 1.0e-4)
        y = int(abs(clon - clon_min) / 1.0e-4)
        xyz_tup = (x, y, height, area, height, clat, clon)
        xyz_bd.append(xyz_tup)
    return xyz_bd