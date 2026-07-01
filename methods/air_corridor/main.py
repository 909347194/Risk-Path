#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/main.py
"""
Module: main
This module contains the main function to run various tasks for emergency landing scenarios.
It initializes the necessary parameters and executes different tasks such as path planning, plotting, and sensitivity analysis.

Functions:
    main(): Initializes parameters and runs various tasks for emergency landing scenarios.
"""

# import sources
import math
import time
import multiprocessing
from Key_Elements import weight
from Optimization.main_procedure import main_procedure
from Plot.sensitivity_plot import sensitivity_risk_weight
import multiprocessing
from Optimization.path_planning import dijkstra_3d
from Optimization.path_planning_greedy import greedy_best_first_3d
from Optimization.path_planning_astar import a_star_3d
from Plot.path_plot import my_path_geosubplot
from Plot.curve_plot import plot_line_respectively
from Plot.voxel_plot import my_voxel_geosubplot
from Plot.table_plot import plot_table
from Plot.dense_plot import my_dense_geosubplot



if __name__ == "__main__":    
    layers = [0, 10, 20, 30]

    main_procedure_params = {
        # Configuration
        'Num of CPU': multiprocessing.cpu_count()-1, 

        # Data
        'city': 'Beijing', 
        'Index_of_csv': 'all', 
        'WITH_BUILDING': True, 
        'root_path': '.\\Data\\Processed\\', 

        # Parameters
        'Fatality_weight': 0.7, 
        'Property_weight': 0.2, 
        'Noise_weight': 0.1, 

        'Trade-off weight_distance': 0.1, # omega
        'Trade-off weight_rescue': 0.3, # omega
        'Magnification coeff_tpr': 2.88e5, # gamma
        'Magnification coeff_rescue': 5e-4, #
        'mode': 0, 
        'Trade-off weight group_distance': [0.5],
        'Trade-off weight group_rescue': [0.3], 

        # Method
        'Algorithm': a_star_3d, 
        'Scale coefficient': 1.0, # To scale the map
    }


    # Generate the file name
    main_procedure_params['File name'] = main_procedure_params['root_path'] + main_procedure_params['city'] + \
        '\\CsvNum_' + str(main_procedure_params['Index_of_csv']) + '_WithBuilding_' + str(main_procedure_params['WITH_BUILDING']) + \
        '_Fatality_' + str(main_procedure_params['Fatality_weight']) + '_Property_' + str(main_procedure_params['Property_weight']) +\
        '_Noise_' + str(main_procedure_params['Noise_weight']) + '.pkl'
    
    # Time the execution
    time_start = time.time()
    
    # Execute the main procedure
    field, path_group, result_group = main_procedure(main_procedure_params)

    weight.set_value('ER_Weight_Distance', main_procedure_params['Trade-off weight_distance']) # omega
    weight.set_value('ER_Weight_Rescue', main_procedure_params['Trade-off weight_rescue']) # omega
    weight.set_value('Enlarge_param_TPR', main_procedure_params['Magnification coeff_tpr']) # gamma
    weight.set_value('Enlarge_param_Rescue', main_procedure_params['Magnification coeff_rescue']) # gamma

    # plot
    # my_dense_geosubplot(field, main_procedure_params['city'], layers)

    my_path_geosubplot(field, path_group, main_procedure_params['city'])

    # plot_line_respectively(path_group)

    # my_voxel_geosubplot(field, path_group, main_procedure_params['city'], True)

    # plot_table(result_group)
    
    time_end = time.time()
    print(f"Time cost: {time_end - time_start:.2f}s")


    