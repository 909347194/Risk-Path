#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/main_preparemap.py
"""
Module: main_preparemap
This module contains the main function to run the PrepareMap task for emergency landing scenarios.
It initializes the necessary parameters and executes the PrepareMap task for different cities.

Functions:
    main(): Initializes parameters and runs the PrepareMap task for different cities.
"""

# import sources
import math
import time
import multiprocessing
from Key_Elements import weight
from Data_Process.prepare_map import load_map, prepare_map


if __name__ == "__main__":
    weight._init()

    main_procedure_params = {
        # Configuration
        'Num of CPU': multiprocessing.cpu_count()-1, 

        # Data
        'city': 'Beijing', 
        'Index_of_csv': 'all', 
        'WITH_BUILDING': True, 
        'root_path': '.\\Data\\Processed\\', 

        # Parameters
        'Trade-off weight': 0.1, 
        'Fatality_weight': 0.7,  # fatality risk cost
        'Property_weight': 0.2,  # property risk cost
        'Noise_weight': 0.1,     # noise impact cost
        'Magnification coeff': math.sqrt(10) * 1e3, 
        'mode': 1, 
        'Trade-off weight group': [0.0, 0.5, 1.0], 
    }

    # cities = ['Beijing', 'Guangzhou', 'Chongqing', 'Shenzhen', 'Shanghai']
    cities = ['Beijing']

    for c in cities:
        time_start = time.time()

        main_procedure_params['city'] = c

        prepare_map(main_procedure_params)
        
        # file_name = main_procedure_params['root_path'] + main_procedure_params['city'] + '\\CsvNum_' + \
        #     main_procedure_params['Index_of_csv'] + '_WithBuilding_' + str(main_procedure_params['WITH_BUILDING']) + '.pkl'
        # field = load_map(file_name)

        time_end = time.time()
        print(f"{c}, Time: {time_end - time_start:.2f} s.")