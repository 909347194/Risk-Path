#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Optimization/path_planning.py
"""
Module: path_planning
This module contains various path planning algorithms for 3D path planning in emergency landing scenarios.
It includes implementations of Dijkstra's algorithm, A* algorithm, and Greedy Best-First Search algorithm.

Functions:
    round_with_zero(num, decimal_places, index): Rounds a number to a specified number of decimal places.
    dijkstra_3d(field, START, END, index): Dijkstra's algorithm for 3D path planning.
"""

import queue
import numpy as np
import copy
from Key_Elements.point_class import sv_lt, Point
from Key_Elements.weight import *
import time

# Average Cost Threshold
ACThred = 0.0004

def round_with_zero(num,decimal_places,index=0):
    """
    Rounds a number to a specified number of decimal places.

    Parameters:
        num (float): The number to round.
        decimal_places (int): The number of decimal places to round to.
        index (int): Format index (0 for fixed-point, 1 for scientific).

    Returns:
        float: The rounded number.
    """

    rounded_num=round(num,decimal_places)
    if index==0:
        format_string="{:."+str(decimal_places)+'f}'
    else:
        format_string="{:."+str(decimal_places)+'e}'
    formatted_num=format_string.format(rounded_num)
    final_result=float(formatted_num)
    return final_result


# dijkstra_3d
def dijkstra_3d(field, START, END, index):
    '''
    This function is the key function to find a feasible solution.
    @Parameters: 
        field   3-D array           The clipped map
        START   3-element tuple     The origin
        END     3-element tuple     The destination
        index   int                 index=0: energy cost based
                                    index=1: weighted energy and risk cost 
                                    index=2: risk cost based

    @Output:
        path    list of 5-element lists     [x, y, z, h, statevector]
        result  6-element list             label, distance, overall risk, weighted, average risk, negotiation prob.
    '''
    start_time = time.time()

    label_group = ["Distance Cost Based","Weighted Cost Based","Risk Cost Based"]


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

    start = field[START[0]][START[1]][START[2]]
    end = field[END[0]][END[1]][END[2]]

    """Initialize distances to all nodes to infinity
    state_vector = [Cost_all_i, Si, Acumulative Rnoise, j=0->i(1-pj)]"""
    init_distance = np.array([0.0,0.0,start.noise,1.0])
    start.set_statevector(init_distance)

    """Use a priority queue to keep track of the nodes to visit"""
    q = queue.PriorityQueue()
    q.put(start)

    # Loop for solving the problem
    while not q.empty():
        # Get the node with the shortest distance
        current_p = q.get()

        # If we have reached the end node, return the distance
        if current_p.x == end.x and current_p.y==end.y and current_p.z==end.z:
            break

        if field[current_p.x][current_p.y][current_p.z].isread == True:
            continue

        # Otherwise, update the distances to the neighboring nodes
        for neighbor in get_neighbors(current_p, field):
            if field[neighbor.x][neighbor.y][neighbor.z].isread == True:
                continue

            # distance is statevector
            distance = neighbor.get_statevector(current_p)
            if sv_lt(distance,neighbor.StateVector,index):
                neighbor.set_statevector(distance)
                neighbor.father=current_p
                q.put(neighbor)
        
        field[current_p.x][current_p.y][current_p.z].isread = True
        # print(q.qsize())

    path = []
    ER_Weight = get_value('ER_Weight')
    Enlarge_param = get_value('Enlarge_param')

    if end.father==None:
        print("No solution!!!")

        end_time = time.time()
        print(f'Time cost: {int(end_time - start_time)}s.')
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
        print(f'Dijkstra    : [Objective] {Objective:<10}       [Time] {time_all:<6} s      '
              f'[Number of units] {NumUnit:<10}')

        return path,result


# bellman_ford
def network(field, index):
    """
        index=0 or 1: one side
        index=2: both sides
    """

    # stations=[]
    # stations=[(int(field.shape[0]/2),0),\
    #           (int(field.shape[0]/2),int(field.shape[1]-1))]
    stations=[(int(field.shape[0]/2), 0),\
              (int(field.shape[0]/2), int(field.shape[1]-1)),\
              (0, int(field.shape[1]/2)),\
              (int(field.shape[0])-1, int(field.shape[1]/2))]
    od_group=[]

    for i in range(len(stations)):
        for j in range(len(stations)):
            if index == 0 or index == 1:
                if j<=i:
                    continue
                else:
                    if index == 0:
                        start = (stations[i][0], stations[i][1], 30)
                        end = (stations[j][0], stations[j][1], 0)
                    else:
                        start = (stations[j][0], stations[j][1], 30)
                        end = (stations[i][0], stations[i][1], 0)
                    od_group.append((start, end))
            else:
                if j == i:
                    continue
                else:
                    start = (stations[i][0], stations[i][1], 30)
                    end = (stations[j][0], stations[j][1], 0)
                    od_group.append((start, end))

    path_group = []
    result_group = []

    for od in od_group:
        path, result = dijkstra_3d(field, od[0], od[1], 1)
        path_copy = copy.deepcopy(path)
        path_group.append(path_copy)
        result_group.append(result)
    
    return path_group,result_group


def get_neighbors(p, field):
    """
    Get the neighbors of the current point in the field.

    Parameters:
        current (tuple): The current point (x, y, z).
        field (3D array): The field array.

    Returns:
        list: List of neighbor points.
    """
    
    neighbors = []
    for i in [-1, 0, 1]:
        for j in [-1, 0, 1]:
            for k in [-1, 0, 1]:
                if not (i == 0 and j == 0 and k == 0):
                    if p.x + i >= field.shape[0] or p.x + i < 0 or \
                    p.y + j >= field.shape[1] or p.y + j < 0 or \
                    p.z + k >= field.shape[2] or p.z + k < 0:
                        continue
                    else:
                        neighbors.append(field[p.x + i][p.y + j][p.z + k])
    return neighbors

"""def sv_lt(array1,array2):
    if array1[0]>array2[0]:
        return False
    elif array1[0]==array2[0]:
        if array1[1]/(array1[0]+0.00001)>array2[1]/(array2[0]+0.00001):
            return False
        elif array1[1]/(array1[0]+0.00001)==array2[1]/(array2[0]+0.00001):
            if array1[3]>array2[3]:
                return False
            elif array1[3]==array2[3]:
                if array1[2]>array2[2]:
                    return False
                else:
                    return True
            else:
                return True
        else:
            return True
    else:
        return True"""

