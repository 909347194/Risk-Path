#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Dara_Process/map_generation.py
"""
This module generates a 3-D map for emergency landing simulations.
It includes functions to calculate integrated cost, flatten nested lists,
and initialize the map with people and vehicle densities.
"""

import math
import random
import numpy as np
from Key_Elements.point_class import Point, get_peo_risk, get_noise

# Global params
CR_F_MAX = 1e-9
CR_P_D_MAX = 1e-9
CNOISE_MAX = 1


def int_cost(c_1=0, c_2=0, a_1=0.7, a_2=0.2):
    """Integrate the cost."""
    return a_1 * c_1 / CR_F_MAX + a_2 * c_2 / CR_P_D_MAX

def compute_distance(x_0, y_0, x_1, y_1):
    return math.sqrt((x_0 - x_1) ** 2 + (y_0 - y_1) ** 2)

def flatten(lst):
    """Flatten a nested list."""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def init_map(x_ratio, y_ratio, xyz_people_dense, xyz_building, lat_max, lon_min,
             with_building=True, alpha_f=0.7, alpha_b=0.2, alpha_n=0.1):
    """
    Generate a 3-D map.
    
    Parameters:
        x_ratio (float): The x scale factor to divide.
        y_ratio (float): The y scale factor to divide.
        xyz_people_dense (list): List of 7-element tuples with data of people density.
        xyz_building (list): List of 7-element tuples with data of buildings.
        lat_max (float): The max of latitude.
        lon_min (float): The min of longitude.
        with_building (bool): Whether to contain building data.
    
    Returns:
        np.array: 3-D array where each element is a Point object.
    """
    global CR_P_D_MAX
    x_max = max(tup[0] for tup in xyz_people_dense)
    y_max = max(tup[1] for tup in xyz_people_dense)

    if with_building:
        x_max = max(x_max, max(tup[0] for tup in xyz_building))
        y_max = max(y_max, max(tup[1] for tup in xyz_building))

    xmax = math.ceil(x_max / x_ratio) + 1
    ymax = math.ceil(y_max / y_ratio) + 1
    zmax = 50

    # Create map
    map_3d = np.array([[[Point(x, y, z, alpha_n) for z in range(zmax)] for y in range(ymax)] for x in range(xmax)])

    for tup in xyz_people_dense:
        peo_dens = map_3d[int(tup[0] / x_ratio)][int(tup[1] / y_ratio)][int(tup[2])].PeoDens + tup[3]
        map_3d[int(tup[0] / x_ratio)][int(tup[1] / y_ratio)][int(tup[2])].set_PeoDens(peo_dens)
        veh_dens = map_3d[int(tup[0] / x_ratio)][int(tup[1] / y_ratio)][int(tup[2])].VehDens + tup[4]
        map_3d[int(tup[0] / x_ratio)][int(tup[1] / y_ratio)][int(tup[2])].set_VehDens(veh_dens)

    if with_building:
        for tup in xyz_building:
            map_3d[int(tup[0] / x_ratio)][int(tup[1] / y_ratio)][0].Building.append((tup[3], tup[4]))

        sum_area = np.sum(np.array([tup[0] for tup in xyz_building]))
        height_ln = np.array([math.log(tup[1]) for tup in xyz_building])
        weights = np.array([float(tup[0] / sum_area) for tup in xyz_building])
        miu = np.average(height_ln, weights=weights)
        sigma = np.sqrt(np.average((height_ln - miu) ** 2, weights=weights))

    print("Map created!")

    # Assess risk & noise of points
    for i in range(xmax):
        for j in range(ymax):
            for k in range(zmax):
                if map_3d[i][j][k].z != 0:
                    map_3d[i][j][k].set_PeoDens(map_3d[i][j][0].PeoDens)
                    map_3d[i][j][k].set_VehDens(map_3d[i][j][0].VehDens)

                cr_f = get_peo_risk(map_3d[i][j][k], x_ratio, y_ratio)
                cnoise = get_noise(map_3d[i][j][k])
                map_3d[i][j][k].set_Cr_f(cr_f)
                map_3d[i][j][k].set_noise(cnoise)

                global CR_F_MAX
                CR_F_MAX = max(CR_F_MAX, cr_f)
                global CNOISE_MAX
                CNOISE_MAX = max(CNOISE_MAX, cnoise)

    if with_building:
        # Assess building risk
        for i in range(xmax):
            for j in range(ymax):
                if not map_3d[i][j][0].Building:
                    for k in range(zmax):
                        map_3d[i][j][k].Cr_p_d = 0.0
                else:
                    for k in range(zmax):
                        building_selected = [tup for tup in map_3d[i][j][0].Building if tup[1] >= map_3d[i][j][k].h]
                        if math.log(map_3d[i][j][k].h) <= miu:
                            map_3d[i][j][k].Cr_p_d = np.sum(np.array([tup[0] * 1.0 / (np.exp(miu) * sigma *
                                                    np.sqrt(2.0 * np.pi)) for tup in building_selected]))
                        else:
                            map_3d[i][j][k].Cr_p_d = np.sum(np.array([tup[0] * 1.0 / (map_3d[i][j][k].h * sigma *
                                np.sqrt(2.0 * np.pi)) * np.exp(-(math.log(map_3d[i][j][k].h) - miu) ** 2 /
                                (2.0 * sigma ** 2)) for tup in building_selected]))
                        CR_P_D_MAX = max(CR_P_D_MAX, map_3d[i][j][k].Cr_p_d)

    emergency_landing_stations = [
        (int(0.1 * xmax), int(0.1 * ymax), 0),
        (int(0.9 * xmax), int(0.1 * ymax), 0),
    ]
    global CR_R_MAX
    CR_R_MAX = 0.0
    # Compute rescue cost
    for i in range(xmax):
        for j in range(ymax):
            for k in range(zmax):
                Cr_r = min([compute_distance(i, j, tup[0], tup[1]) for tup in emergency_landing_stations])
                map_3d[i][j][k].set_Cr_r(Cr_r)
                CR_R_MAX = max(CR_R_MAX, Cr_r)

    # Integrated risk
    for i in range(xmax):
        for j in range(ymax):
            for k in range(zmax):
                map_3d[i][j][k].set_risk(int_cost(map_3d[i][j][k].Cr_f, map_3d[i][j][k].Cr_p_d, alpha_f, alpha_b))
                map_3d[i][j][k].set_noise(map_3d[i][j][k].noise / CNOISE_MAX)
                map_3d[i][j][k].set_Cr_r(map_3d[i][j][k].Cr_r / CR_R_MAX)
    print("Risk & noise assessment completed!")

    # Geometry
    for i in range(xmax):
        for j in range(ymax):
            map_3d[i][j][0].set_geometry(lat_max, lon_min)

    return map_3d


def random_map(x_ratio, y_ratio, xyz_people_dense):
    """
    Generate a random 3-D map.
    
    Parameters:
        x_ratio (float): The x scale factor to divide.
        y_ratio (float): The y scale factor to divide.
        xyz_people_dense (list): List of 7-element tuples with data of people density.
    
    Returns:
        tuple: 3-D array where each element is a Point object, xmax, ymax, zmax.
    """
    x_max = max(tup[0] for tup in xyz_people_dense)
    y_max = max(tup[1] for tup in xyz_people_dense)

    xmax = math.ceil(x_max / x_ratio)
    ymax = math.ceil(y_max / y_ratio)
    zmax = 50

    # Create map
    map_3d = np.array([[[Point(x, y, z) for z in range(zmax)] for y in range(ymax)] for x in range(xmax)])

    for i in range(xmax):
        for j in range(ymax):
            peo_dens = np.random.randint(2, 5)
            map_3d[i][j][0].set_PeoDens(peo_dens)
            veh_dens = np.random.randint(2, 5)
            map_3d[i][j][0].set_VehDens(veh_dens)

    # Number of high risk area
    num_hra = np.random.randint(100, 120)
    for _ in range(num_hra):
        alpha = random.randint(0, 10) / 40.0
        x_center = np.random.randint(0 + alpha * xmax, xmax - alpha * xmax)
        y_center = np.random.randint(0 + alpha * ymax, ymax - alpha * ymax)
        flag = np.random.randint(0, 3)
        if flag == 0:
            peo_dens = np.random.randint(25, 35)
            veh_dens = np.random.randint(5, 15)
        else:
            peo_dens = np.random.randint(15, 25)
            veh_dens = np.random.randint(5, 10)
        radius = np.random.randint(int(min(xmax, ymax) / 5 * (peo_dens + veh_dens) / 50.0),
                                   int(min(xmax, ymax) / 3 * (peo_dens + veh_dens) / 50.0))
        map_3d[x_center][y_center][0].set_PeoDens(peo_dens)
        map_3d[x_center][y_center][0].set_VehDens(veh_dens)
        for dx in range(-radius, radius + 1, 1):
            for dy in range(-radius, radius + 1, 1):
                if dx ** 2 + dy ** 2 > radius ** 2:
                    continue
                neighbor = np.array([x_center + dx, y_center + dy, 0, np.exp(-2.0 * (dx ** 2 + dy ** 2) / radius ** 2)])
                if 0 <= neighbor[0] < xmax and 0 <= neighbor[1] < ymax:
                    map_3d[int(neighbor[0])][int(neighbor[1])][0].set_PeoDens(
                        max(math.ceil(map_3d[x_center][y_center][0].PeoDens * neighbor[3]),
                            map_3d[int(neighbor[0])][int(neighbor[1])][0].PeoDens))
                    map_3d[int(neighbor[0])][int(neighbor[1])][0].set_VehDens(
                        max(math.ceil(map_3d[x_center][y_center][0].VehDens * neighbor[3]),
                            map_3d[int(neighbor[0])][int(neighbor[1])][0].VehDens))
    print("Map created!")

    # Assess risk & noise of points
    for i in range(xmax):
        for j in range(ymax):
            for k in range(zmax):
                if map_3d[i][j][k].z != 0:
                    map_3d[i][j][k].set_PeoDens(map_3d[i][j][0].PeoDens)
                    map_3d[i][j][k].set_VehDens(map_3d[i][j][0].VehDens)
                cr_f, cr_p_d = get_peo_risk(map_3d[i][j][k], x_ratio, y_ratio)
                cnoise = get_noise(map_3d[i][j][k])
                map_3d[i][j][k].set_Cr(cr_f, cr_p_d)
                map_3d[i][j][k].set_noise(cnoise)
    for i in range(xmax):
        for j in range(ymax):
            for k in range(zmax):
                map_3d[i][j][k].set_risk(int_cost(map_3d[i][j][k].Cr_f, map_3d[i][j][k].Cr_p_d))
                map_3d[i][j][k].set_noise(map_3d[i][j][k].noise / CNOISE_MAX)
    print("Risk & noise assessment completed!")
    return map_3d, xmax, ymax, zmax
