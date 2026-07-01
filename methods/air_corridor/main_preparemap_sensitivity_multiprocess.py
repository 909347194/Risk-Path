#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/main_preparemap_sensitivity_multiprocess.py
"""
Module: main_preparemap_sensitivity_multiprocess
This module contains functions to run sensitivity analysis for the prepare_map task in emergency landing scenarios.
It includes functions to execute the prepare_map task with different weights in parallel using multiprocessing.

Functions:
    run_simulation(fw, pw, main_procedure_params): Executes the prepare_map task with different weights.
"""

# import sources
import math
import time
import multiprocessing
from Key_Elements import weight
from Air_Corridor_Design.Data_Process.prepare_map import load_map, prepare_map

# Function to execute the prepare_map task with different weights
def run_simulation(fw, pw, main_procedure_params):
    nw = round(1.0 - fw - pw,1)  # Calculate Noise weight
    main_procedure_params['Fatality_weight'] = fw
    main_procedure_params['Property_weight'] = pw
    main_procedure_params['Noise_weight'] = nw

    time_start = time.time()
    prepare_map(main_procedure_params)
    time_end = time.time()

    # Return the weights and the time it took
    return (fw, pw, nw, time_end - time_start)

if __name__ == "__main__":
    # Initialize weights
    weight._init()

    # Main parameters
    main_procedure_params = {
        'Num of CPU': 1,  # Use all but one CPU core
        'city': 'Beijing',
        'Index_of_csv': 'all',
        'WITH_BUILDING': True,
        'root_path': '.\\Data\\Processed\\',
        'Trade-off weight': 0.1,
        'Fatality_weight': 0.7,  # Initial fatality risk cost (will be overwritten)
        'Property_weight': 0.2,  # Initial property risk cost (will be overwritten)
        'Noise_weight': 0.1,     # Initial noise impact cost (will be overwritten)
        'Magnification coeff': math.sqrt(10) * 1e3,
        'mode': 1,
        'Trade-off weight group': [0.0, 0.5, 1.0],
    }

    # Create a list of all combinations of fatality and property weights
    fatality_weights = [round(0.1 * i, 1) for i in range(11)]
    all_weight_combinations = []

    # Collect weight combinations
    for fw in fatality_weights:
        property_weights = [round(0.1 * j,1) for j in range(11 - int(fw * 10))]
        for pw in property_weights:
            all_weight_combinations.append((fw, pw))

    # Create a pool of workers
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()-2) as pool:
        # Run the simulations in parallel, passing the function and parameters
        results = pool.starmap(run_simulation, [(fw, pw, main_procedure_params) for fw, pw in all_weight_combinations])

    # Print the results after completion
    for fw, pw, nw, duration in results:
        print(f"Fatality Weight: {fw}, Property Weight: {pw}, Noise Weight: {nw} - Time: {duration:.2f}s")
