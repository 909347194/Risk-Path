#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/main_algorithm_performance.py
"""
Module: main_algorithm_performance
This module contains functions to evaluate the performance of different path planning algorithms
in emergency landing scenarios. It includes functions to run experiments in parallel with various
algorithm and scale combinations.

Functions:
    run_experiment(params): Runs a specific algorithm and scale combination in parallel.
"""

# import sources
import math
import time
import multiprocessing
import traceback
import os
import numpy as np
from Key_Elements import weight
from Air_Corridor_Design.Optimization.main_procedure import main_procedure
from Air_Corridor_Design.Optimization.path_planning import dijkstra_3d
from Air_Corridor_Design.Optimization.path_planning_greedy import greedy_best_first_3d
from Air_Corridor_Design.Optimization.path_planning_astar import a_star_3d


def run_experiment(params):
    """
    Function to run a specific algorithm and scale combination.
    This will be executed in parallel.
    """
    scale_coefficient, algorithm, main_procedure_params = params
    
    # Update parameters for this run
    main_procedure_params['Scale coefficient'] = scale_coefficient
    main_procedure_params['Algorithm'] = algorithm
    
    # Start time for this run
    time_start_algo = time.time()
    
    try:
        # Run the main procedure for the given parameters
        _, _, result_group = main_procedure(main_procedure_params)
        
        time_end_algo = time.time()
        # print(f"Algorithm: {algorithm.__name__}, Scale: {scale_coefficient}, Time: {time_end_algo - time_start_algo:.2f} s")
        
        return (algorithm.__name__, scale_coefficient, time_end_algo - time_start_algo, result_group)
    
    except Exception as e:
        print(f"Error in running {algorithm.__name__} at scale {scale_coefficient}: {str(e)}")
        return None
    

if __name__ == "__main__":
    time_start = time.time()
    
    layers = [0, 10, 20, 30]
    # ER_Weight_group = [round(1.0-0.05*i,2) for i in range(21)]
    # ER_Weight_group = [round(1.0-0.05*i,2) for i in range(6)]

    main_procedure_params = {
        # Configuration
        'Num of CPU': multiprocessing.cpu_count()-1, 

        # Data
        'city': 'Beijing', 
        'Index_of_csv': 1, 
        'WITH_BUILDING': False, 
        'root_path': '.\\Data\\Processed\\', 

        # Parameters
        'Trade-off weight': 0.9,  # Omega
        'Magnification coeff': 2.88e5, # gamma
        'mode': 1, 
        'Trade-off weight group': [0.9], 
        
        # Method
        'Algorithm': greedy_best_first_3d, 
        'Scale coefficient': 0.4, # To scale the map
    }

    # Optimize
    main_procedure_params['Fatality_weight'] = 0.7  # Initial fatality risk cost (will be overwritten)
    main_procedure_params['Property_weight'] = 0.2  # Initial property risk cost (will be overwritten)
    main_procedure_params['Noise_weight'] = 0.1     # Initial noise impact cost (will be overwritten)
    
    main_procedure_params['File name'] = main_procedure_params['root_path'] + main_procedure_params['city'] + '\\CsvNum_' + \
        main_procedure_params['Index_of_csv'] + '_WithBuilding_' + str(main_procedure_params['WITH_BUILDING']) + \
        '_Fatality_' + str(main_procedure_params['Fatality_weight']) + '_Property_' + str(main_procedure_params['Property_weight']) + \
        '_Noise_' + str(main_procedure_params['Noise_weight']) + '.pkl'


    scale_list = [0.0316, 0.1, 0.316, 1]
    algorithm_list = [greedy_best_first_3d, a_star_3d, dijkstra_3d]
    # Generate all combinations of scale and algorithm
    experiments = [(scale, algo, main_procedure_params.copy()) for scale in scale_list for algo in algorithm_list]

    # Parallel processing using Pool
    with multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1) as pool:
        results = pool.map(run_experiment, experiments)
    
    time_end = time.time()
    print(f'Total time cost for all experiments: {time_end - time_start:.2f} s')
    