#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Optimization/main_procedure.py
"""
Module: main_procedure
This module contains the main function for running experiments related to emergency landing scenarios.
It initializes necessary parameters and calls various functions to process data, generate maps, and
perform path planning.

Functions:
    main_procedure(params): Main function for experiments.
"""

# import sources
import numpy as np
import sys
import copy
from Key_Elements.point_class import Point
from Data_Process.preprocess import *
from Data_Process.map_generation import *
from .path_planning import *
from .path_planning_greedy import greedy_best_first_3d
from .path_planning_astar import a_star_3d
from Key_Elements import weight
from Data_Process.prepare_map import load_map


def main_procedure(params):
    '''
    This function is the main function for experiments.
    @Parameters:
        city            string                      Which city
        er_weight       float                       The parameter for trade-off, omega
        enlarge_param   float                       The parameter to reduce the effect of magnification
        mode            int                         0: one shot, only consider one circumstance
                                                    1: Multiple analysis, only one trajectory, but varying er_weight
                                                    2: Generate network of cities
        er_w_group      1-D list of er_weight s     To serve circumstance when mode == 1

    @Output:
        field           3D array of Point object        Clipped map
        path_group      list of list of 5-element lists [x, y, z, h, statevector]
        result_group    list of 6-element lists         [label, distance, overall risk, weighted, average risk, negotiation prob.]        
    '''

    weight._init()

    # params
    city = params['city']
    er_weight_distance = params['Trade-off weight_distance']
    er_weight_rescue = params['Trade-off weight_rescue']
    enlarge_param_tpr = params['Magnification coeff_tpr']
    enlarge_param_rescue = params['Magnification coeff_rescue']
    mode = params['mode']
    er_w_group_distance = params['Trade-off weight group_distance']
    er_w_group_rescue = params['Trade-off weight group_rescue']

    # Method
    path_planning_algorithm = params['Algorithm']


    ## Load map
    file_name = params['File name']
    field = load_map(file_name)


    """Trajectory planning
    (Xborder_min, Xborder_max, Yborder_min, Yborder_max)
    index = 0: energy cost based
    index = 1: weighted energy and risk cost 
    index = 2: risk cost based
    """

    ## one OD
    # To contain path groups
    path_group=[]
    # To contain objectives
    result_group=[]

    # Clip the field
    clip_coef = params['Scale coefficient']
    field = [[[field[x][y][z] for z in range(field.shape[2])] \
              for y in range(int(field.shape[1]*0.5*(1-clip_coef)), int(field.shape[1]*0.5*(1+clip_coef)), 1)]\
              for x in range(int(field.shape[0]*0.5*(1-clip_coef)), int(field.shape[0]*0.5*(1+clip_coef)), 1)]
    field = np.array(field)

    # Set the origin and the destination manually
    START = (int(0.75 * field.shape[0]), int(0.30 * field.shape[1]), 40)
    END = (int(0.4 * field.shape[0]), int(0.75 * field.shape[1]), 5)
    # START = (int(1.0*field.shape[0]-1), int(0.0*field.shape[1]), int(1.0*field.shape[2]-1))
    # END = (int(0.0*field.shape[0]), int(1.0*field.shape[1]-1), int(0.0*field.shape[1]))

    # one shot, only consider one circumstance
    if mode == 0: 
        # 
        weight.set_value('ER_Weight_Distance', er_weight_distance)
        weight.set_value('ER_Weight_Rescue', er_weight_rescue)
        # 
        weight.set_value('Enlarge_param_TPR', enlarge_param_tpr)
        weight.set_value('Enlarge_param_Rescue', enlarge_param_rescue)

        for i in range(3):
            # Conduct optimization (Search for a feasible trajectory)
            path, result = path_planning_algorithm(field, START, END, i)
            if path == None:
                print(f"Path planning failed when index = {i}")
                sys.exit(0)
            path_copy = copy.deepcopy(path)
            path_group.append(path_copy)
            result_group.append(result)
        # result_group=np.array(result_group)

    # Multiple analysis, only one trajectory, but varying er_weight
    elif mode == 1:
        for weight_idx, weight_distance in enumerate(er_w_group_distance):
            weight.set_value('ER_Weight_Distance', weight_distance) # omega
            weight.set_value('ER_Weight_Rescue', er_w_group_rescue[weight_idx]) # omega
            weight.set_value('Enlarge_param_TPR', enlarge_param_tpr) # gamma
            weight.set_value('Enlarge_param_Rescue', enlarge_param_rescue) # gamma

            pp_index = 0
            if weight_distance == 1.0:    # Distance cost based
                pp_index = 0 
            elif weight_distance + er_w_group_rescue[weight_idx] == 0.0:  # TPR cost based
                pp_index = 2
            else:           # Trade-off
                pp_index = 1

            # Conduct optimization (Search for a feasible trajectory)
            path, result = path_planning_algorithm(field, START, END, pp_index)
            if path == None:
                print(f"Path planning failed when index = {i}")
                sys.exit(0)
            path_copy = copy.deepcopy(path)
            path_group.append(path_copy)
            result_group.append(result)
        result_group = np.array(result_group)

    # Generate network of cities
    elif mode == 2:
        weight.set_value('ER_Weight_Distance', er_weight_distance) # omega
        weight.set_value('ER_Weight_Rescue', er_weight_rescue) # omega
        weight.set_value('Enlarge_param_TPR', enlarge_param_tpr) # gamma
        weight.set_value('Enlarge_param_Rescue', enlarge_param_rescue) # gamma
        # Set borders and OD pairs
        # Side depots
        depots_side_dict = {
            'Beijing': [(0.75, 0.30), 
                        (0.70, 0.65),
                        (0.40, 0.75),
                        (0.35, 0.45)],
            'Shanghai': [(0.396, 0.507),
                         (0.418, 0.333),
                         (0.597, 0.237), 
                         (0.702, 0.353), 
                         (0.707, 0.520), 
                         (0.573, 0.692)],
            'Chongqing': [(0.208, 0.402), 
                          (0.420, 0.133), 
                          (0.659, 0.409), 
                          (0.687, 0.540), 
                          (0.592, 0.714), 
                          (0.248, 0.666), 
                          (0.205, 0.409)], 
            'Shenzhen': [(0.377, 0.125), 
                         (0.534, 0.147), 
                         (0.706, 0.246), 
                         (0.691, 0.373), 
                         (0.549, 0.455), 
                         (0.517, 0.344)],
            'Guangzhou': [(0.3246, 0.4226), 
                          (0.4855, 0.360), 
                          (0.694, 0.5185), 
                          (0.423, 0.6785)],
        }

        # center depots
        depots_center_dict = {
            'Beijing': (0.53, 0.53),
            'Shanghai': (0.549, 0.520),
            'Chongqing': (0.473, 0.504), 
            'Shenzhen': None,
            'Guangzhou': (0.4855, 0.495),
        }

        # island depots
        island_center_dict = {
            'Beijing': [],
            'Shanghai': [(0.177, 0.473), 
                         (0.402, 0.781)],
            'Chongqing': [], 
            'Shenzhen': [(0.419, 0.559), 
                         (0.595, 0.832)],
            'Guangzhou': [],
        }

        # island depots with side depots
        island_depot_pairs = {
            'Beijing': [],
            'Shanghai': [(0, 0), 
                         (-1, -1)],
            'Chongqing': [], 
            'Shenzhen': [(4, 0), 
                         (3, -1)],
            'Guangzhou': [],
        }


        depots_side = [(int(dsd[0]*field.shape[0]), int(dsd[1]*field.shape[1])) \
                       for dsd in depots_side_dict[city]]
        depots_side_len = len(depots_side)
        if depots_center_dict[city]:
            depots_center = (int(depots_center_dict[city][0] * field.shape[0]), \
                             int(depots_center_dict[city][1] * field.shape[1]))
        OD_group=[]
        for i in range(depots_side_len):
            # Each other
            start = (depots_side[i][0], depots_side[i][1], 40)
            end = (depots_side[(i+1) % depots_side_len][0], depots_side[(i+1) % depots_side_len][1], 5)
            OD_group.append((start,end))

            start = (depots_side[(i+1) % depots_side_len][0], depots_side[(i+1) % depots_side_len][1], 40)
            end = (depots_side[i][0], depots_side[i][1], 5)
            OD_group.append((start, end))


            # With center
            if depots_center_dict[city]:
                start = (depots_side[i][0], depots_side[i][1], 40)
                end = (depots_center[0], depots_center[1], 5)
                OD_group.append((start, end))

                start = (depots_center[0], depots_center[1], 40)
                end = (depots_side[i][0], depots_side[i][1], 5)
                OD_group.append((start, end))
        
        # Island
        if island_center_dict[city]:
            island_center = [(int(icd[0]*field.shape[0]), int(icd[1]*field.shape[1])) \
                             for icd in island_center_dict[city]]
            island_side_len = len(island_center)

            # island with each other
            for i in range(island_side_len):
                start = (island_center[i][0], island_center[i][1], 40)
                end = (island_center[(i+1)%island_side_len][0], island_center[(i+1)%island_side_len][1], 5)
                OD_group.append((start, end))

                start=(island_center[(i+1)%island_side_len][0], island_center[(i+1)%island_side_len][1], 40)
                end=(island_center[i][0], island_center[i][1], 5)
                OD_group.append((start, end))


            # island with depots_side
            if island_depot_pairs[city]:
                for idp in island_depot_pairs[city]:
                    start = (depots_side[idp[0]][0], depots_side[idp[0]][1], 40)
                    end = (island_center[idp[1]][0], island_center[idp[1]][1], 5)
                    OD_group.append((start, end))

                    start = (island_center[idp[1]][0], island_center[idp[1]][1], 40)
                    end = (depots_side[idp[0]][0], depots_side[idp[0]][1], 5)
                    OD_group.append((start, end))


        # generate the network
        for OD in OD_group:
            path, result = path_planning_algorithm(field, OD[0], OD[1], 1)
            if path == None:
                print("Path planning failed.")
                sys.exit(0)
            path_copy = copy.deepcopy(path)
            path_group.append(path_copy)
            result_group.append(result)

    else:
        weight.set_value('ER_Weight_Distance',er_weight_distance)
        weight.set_value('ER_Weight_Rescue',er_weight_rescue)
        weight.set_value('Enlarge_param_TPR',enlarge_param_tpr)
        weight.set_value('Enlarge_param_Rescue',enlarge_param_rescue)
        return


    return field, path_group, result_group