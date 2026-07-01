#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/main_sensitivity_analysis.py
"""
Module: main_sensitivity_analysis
This module contains functions to run sensitivity analysis for risk weights in emergency landing scenarios.
It includes functions to execute the main procedure with different risk weight combinations in parallel using multiprocessing.

Functions:
    run_main_procedure(key, main_procedure_params): Executes the main procedure with different risk weight combinations.
"""

# import sources
import math
import time
import multiprocessing
from Key_Elements import weight
from Air_Corridor_Design.Optimization.main_procedure import main_procedure
from Air_Corridor_Design.Plot.sensitivity_plot import sensitivity_risk_weight
import multiprocessing
from Air_Corridor_Design.Optimization.path_planning import dijkstra_3d
from Air_Corridor_Design.Optimization.path_planning_greedy import greedy_best_first_3d
from Air_Corridor_Design.Optimization.path_planning_astar import a_star_3d

# Define a function to encapsulate the work
def run_main_procedure(key, main_procedure_params):
    weight._init()

    # Calculate weights
    fatality_weight = key[0]
    property_weight = key[1]
    noise_weight = round(abs(1.0 - fatality_weight - property_weight), 1)

    # Skip invalid combinations
    if noise_weight < 0:
        print(f"Invalid weight combination: Fatality={fatality_weight}, Property={property_weight}, Noise={noise_weight}")
        return key, None

    # Update parameters
    main_procedure_params['Fatality_weight'] = fatality_weight
    main_procedure_params['Property_weight'] = property_weight
    main_procedure_params['Noise_weight'] = noise_weight

    # Generate the file name
    main_procedure_params['File name'] = main_procedure_params['root_path'] + main_procedure_params['city'] + \
        '\\CsvNum_' + main_procedure_params['Index_of_csv'] + '_WithBuilding_' + str(main_procedure_params['WITH_BUILDING']) + \
        '_Fatality_' + str(fatality_weight) + '_Property_' + str(property_weight) + '_Noise_' + str(noise_weight) + '.pkl'
    
    # Time the execution
    time_start = time.time()
    
    # Execute the main procedure
    _, _, result_group = main_procedure(main_procedure_params)
    
    time_end = time.time()
    print(f"Time cost for weights {key}: {time_end - time_start:.2f}s")

    # Return the result along with the key
    return key, (float(result_group[0][1]), float(result_group[0][2]))


if __name__ == "__main__":    
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
        'Trade-off weight': 0.9, # omega
        'Magnification coeff': 2.88e5, # gamma
        'mode': 1, 
        'Trade-off weight group': [0.9], 

        # Method
        'Algorithm': dijkstra_3d, 
        'Scale coefficient': 1.0, # To scale the map
    }

    # Weight.set_value('ER_Weight', main_procedure_params['Trade-off weight'])
    # Weight.set_value('Enlarge_param', main_procedure_params['Magnification coeff'])

    # Create a list of all combinations of fatality and property weights
    fatality_weights = [round(0.1 * i, 1) for i in range(11)]
    # fatality_weights = [0.1]
    all_weight_combinations = []

    # Collect weight combinations
    for fw in fatality_weights:
        property_weights = [round(0.1 * j, 1) for j in range(11 - int(fw * 10))]
        # property_weights = [abs(round(1.0-fw, 1))]
        for pw in property_weights:
            all_weight_combinations.append((fw, pw))


    # Optimize
    result_dict = {}

    # Number of processes to run in parallel
    num_workers = multiprocessing.cpu_count() - 1  # Use all available CPU cores except one

    # Initialize the pool
    with multiprocessing.Pool(processes=num_workers) as pool:
        # Prepare the arguments for each process
        # Using a tuple of (key, copy of main_procedure_params) to send to the worker function
        args = [(key, main_procedure_params.copy()) for key in all_weight_combinations]
        
        # Map the function to the arguments in parallel using Pool
        results = pool.starmap(run_main_procedure, args)
        
        # Collect results
        for key, result in results:
            if result is not None:  # Skip invalid combinations
                result_dict[key] = result


    # Now result_dict contains the parallelized results

    # plot
    sensitivity_risk_weight(result_dict)
    