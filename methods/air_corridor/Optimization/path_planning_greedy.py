#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Optimization/path_planning_greedy.py
"""
Module: path_planning_greedy
This module contains the implementation of the Greedy Best-First Search algorithm for 3D path planning
in emergency landing scenarios.

Functions:
    greedy_best_first_3d(field, START, END, index): Greedy Best-First Search algorithm for 3D path planning.
"""

import queue
import time
from .path_planning import get_neighbors
import numpy as np
import copy
from Key_Elements.point_class import sv_lt, Point
from Key_Elements.weight import *

# greedy
def greedy_best_first_3d(field, START, END, index):
    '''
    Greedy Best-First Search Algorithm
    @Parameters:
        field   3-D array          The clipped map
        START   3-element tuple    The origin (x, y, z)
        END     3-element tuple    The destination (x, y, z)
        index   int                index=0: energy cost based
                                   index=1: weighted energy and risk cost 
                                   index=2: risk cost based

    @Output:
        path    list of 5-element lists     [x, y, z, h, statevector]
        result  6-element list             label, distance, overall risk, weighted, average risk, negotiation prob.
    '''
    start_time = time.time()
    
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')
    label_group=["Distance Cost Based","Weighted Cost Based","Risk Cost Based"]

    '''
    Initialization
    '''
    for i in range(field.shape[0]):
        for j in range(field.shape[1]):
            for k in range(field.shape[2]):
                field[i][j][k].x = i
                field[i][j][k].y = j
                field[i][j][k].z = k
                field[i][j][k].index = index
                field[i][j][k].father = None
                field[i][j][k].isread = False
                if index == 0:
                    array = np.array([float('inf'), 0.0, 0.0, 0.0])
                elif index == 1:
                    array = np.array([float('inf'), float('inf'), 0.0, 0.0])
                else:
                    array = np.array([0.0, float('inf'), 0.0, 0.0])
                field[i][j][k].set_statevector(array)

    # Initialize priority queue
    start = field[START[0]][START[1]][START[2]]
    end = field[END[0]][END[1]][END[2]]

    """Initialize distances to all nodes to infinity
    state_vector = [Cost_all_i, Si, Acumulative Rnoise, j=0->i(1-pj)]"""
    init_distance = np.array([0.0, 0.0, start.noise, 1.0])
    start.set_statevector(init_distance)
    

    # Heuristic function (straight-line distance to the goal)
    def heuristic(node, end):
        return ER_Weight*((node.x - end.x) ** 2 + (node.y - end.y) ** 2 + (node.z - end.z) ** 2) ** 0.5

    # Initialize priority queue
    q = queue.PriorityQueue()
    # Initialize start node
    start_g_cost = 0.0
    start_h_cost = heuristic(start, end)
    start_f_cost = start_g_cost + start_h_cost
    q.put((start_h_cost, start))
    
    while not q.empty():
        current_p = q.get()[1]

        # If the destination is reached
        if current_p.x == end.x and current_p.y == end.y and current_p.z == end.z:
            break

        if field[current_p.x][current_p.y][current_p.z].isread:
            continue

        for neighbor in get_neighbors(current_p, field):
            if field[neighbor.x][neighbor.y][neighbor.z].isread:
                continue

            distance = neighbor.get_statevector(current_p)
            if sv_lt(distance,neighbor.StateVector,index):
                neighbor.set_statevector(distance)
                neighbor_g_cost = ER_Weight * neighbor.StateVector[0] + \
                    Enlarge_param * (1 - ER_Weight) * neighbor.StateVector[1]
                neighbor_h_cost = heuristic(neighbor, end)
                neighbor_f_cost = neighbor_g_cost + neighbor_h_cost
                neighbor.father = current_p
                q.put((neighbor_h_cost, neighbor))

        field[current_p.x][current_p.y][current_p.z].isread = True


    path = []

    if end.father==None:
        print("No solution!!!")

        end_time = time.time()
        print('Time cost: ' + str(int(end_time - start_time)) + ' s.')
        return
    else:
        """backtrack"""
        temp = end
        path.append([end.x, end.y, end.z, end.h, end.StateVector])
        while temp.father != None:
            path.append([temp.father.x, temp.father.y, temp.father.z, temp.father.h, temp.father.StateVector])
            temp = temp.father
        path.reverse()
        # print('Path planning completed! ' + str(index))
        '''
        label, distance, overall risk, weighted, average risk, negotiation prob.
        '''
        # result=[label_group[index],round(float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[0]),1),\
        #         round(float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[1]),4),\
        #         round(float(ER_Weight*field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[0]+\
        #               Enlarge_param*(1-ER_Weight)*field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[1]),1),\
        #         round(float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[1]/(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[0]+0.00001)),5),\
        #         round(float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[3]),4)]
        result = (label_group[index],\
                float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[0]),\
                float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[1]),\
                float(ER_Weight*field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[0]+\
                      Enlarge_param*(1-ER_Weight)*field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[1]),\
                float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[1]/(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[0]+0.00001)),\
                float(field[path[-1][0]][path[-1][1]][path[-1][2]].StateVector[3]))
        
        end_time = time.time()
        
        Objective = round(ER_Weight*result[1] + Enlarge_param*(1-ER_Weight)*result[2], 3)
        NumUnit = field.shape[0] * field.shape[1] * field.shape[2]
        time_all = round(end_time-start_time, 3)
        print(f'BFS         : [Objective] {Objective:<10}       [Time] {time_all:<6} s      '
              f'[Number of units] {NumUnit:<10}')
        
        return path, result