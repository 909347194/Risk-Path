#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/main_sensitivity_tradeoffweight.py
"""
Module: main_sensitivity_tradeoffweight
This module contains functions to run sensitivity analysis for trade-off weights in emergency landing scenarios.
It includes functions to execute the main procedure with different trade-off weights in parallel using multiprocessing.

Functions:
    process_weight(w, main_procedure_params): Executes the main procedure with a specific trade-off weight.
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
from Air_Corridor_Design.Plot.network_plot import my_network_geoplot
from Air_Corridor_Design.Plot.outline_plot import my_outline
from Air_Corridor_Design.Plot.sensitivity_plot import sensitivity_dense_plot, sensitivity_line
from Air_Corridor_Design.Optimization.path_planning import dijkstra_3d
from Air_Corridor_Design.Optimization.path_planning_greedy import greedy_best_first_3d
from Air_Corridor_Design.Optimization.path_planning_astar import a_star_3d

# Function to encapsulate work for each weight
def process_weight(w, main_procedure_params):
    weight._init()
    try:
        # Set weight for this run
        main_procedure_params['Trade-off weight'] = w
        main_procedure_params['Trade-off weight group'] = [w]

        # Run the main procedure for the given weight
        field, path_group, result_group = main_procedure(main_procedure_params)

        # Return the results along with the weight
        return w, path_group[0], result_group[0], field
    except Exception as e:
        print(f"Error processing weight {w}: {e}")
        traceback.print_exc()
        return w, None, None, None  # Return None in case of an error


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
        'Index_of_csv': 'all', 
        'WITH_BUILDING': True, 
        'root_path': '.\\Data\\Processed\\', 

        # Parameters
        'Trade-off weight': 0.9,  # Omega
        'Magnification coeff': 2.88e5, # gamma
        'mode': 1, 
        'Trade-off weight group': [0.9], 
        
        # Method
        'Algorithm': dijkstra_3d, 
        'Scale coefficient': 1.0, # To scale the map
    }

    # Optimize
    main_procedure_params['Fatality_weight'] = 0.7  # Initial fatality risk cost (will be overwritten)
    main_procedure_params['Property_weight'] = 0.2  # Initial property risk cost (will be overwritten)
    main_procedure_params['Noise_weight'] = 0.1     # Initial noise impact cost (will be overwritten)
    
    main_procedure_params['File name'] = main_procedure_params['root_path'] + main_procedure_params['city'] + '\\CsvNum_' + \
        main_procedure_params['Index_of_csv'] + '_WithBuilding_' + str(main_procedure_params['WITH_BUILDING']) + \
        '_Fatality_' + str(main_procedure_params['Fatality_weight']) + '_Property_' + str(main_procedure_params['Property_weight']) + \
        '_Noise_' + str(main_procedure_params['Noise_weight']) + '.pkl'


    # Create a list of weights to iterate over
    division = 20
    weight_list = [abs(round(0.995 + 0.005/division * i, 5)) for i in range(division + 1)]
    # weight_list = [abs(round(0.9 + 0.1/division * i, 3)) for i in range(division + 1)]  # Generate 21 weights between 0 and 1
    # weight_list = [abs(round(1/division * i, 2)) for i in range(division + 1)]  # Generate 21 weights between 0 and 1

    # Use multiprocessing to parallelize the processing of weights
    pool = multiprocessing.Pool(processes=main_procedure_params['Num of CPU'])

    # Process all weights in parallel
    results = pool.starmap(process_weight, [(w, main_procedure_params.copy()) for w in weight_list])

    # Close the pool and wait for all processes to complete
    pool.close()
    pool.join()

    # Collect the results into dictionaries
    path_dict = {}
    result_dict = {}
    field = None
    for w, path_group, result_group, field_tmp in results:
        if path_group is not None and result_group is not None:
            path_dict[w] = path_group
            result_dict[w] = result_group
            field = field_tmp  # Save the field (assumed to be the same for all weights)

    # Sort the results by weights
    sorted_path_dict = dict(sorted(path_dict.items()))
    sorted_result_dict = dict(sorted(result_dict.items()))

    # Convert dictionaries into lists for plotting
    path_group_list = [sorted_path_dict[key] for key in sorted_path_dict]
    result_group_list = [sorted_result_dict[key] for key in sorted_result_dict]


    weight._init()
    weight.set_value('Enlarge_param', main_procedure_params['Magnification coeff'])

    # Plot the results
    if field is not None:
        sensitivity_dense_plot(field, path_group_list, weight_list, 0)
        sensitivity_line(result_group_list, weight_list)
    


    # # network plot
    # my_network_geoplot(field, path_group, main_procedure_params['city'])
    # my_outline(main_procedure_params['city'])

    # field,path_group,result_group=main(city,er_weight=0.1,enlarge_param=math.sqrt(10)*1e3,\
    #                                    mode=3,er_w_group=ER_Weight_group,with_building=False)
    
    # """plot """
    # # # voxel plot
    # my_voxel_geosubplot(field,path_group,city,with_base=True)

    # # # dense plot
    # my_path_geosubplot(field,path_group,city)
    # my_dense_geosubplot(field,city,layers=layers)
    # my_dense_geoplot(field,[],city)

    # # # table plot
    # plot_table(result_group)

    # # # line fig plot
    # plot_line_respectively(path_group)

    time_end = time.time()
    print('Total time cost: ' + str(time_end - time_start) + 's')