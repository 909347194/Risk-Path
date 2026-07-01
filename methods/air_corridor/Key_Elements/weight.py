#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Key_Elements/weight.py

# -*- coding: utf-8 -*-

def _init():  # initialize the global variable
    global _global_dict
    _global_dict = {}

def set_value(key, value):
    # define a global variable
    _global_dict[key] = value

def get_value(key):
    # get a global variable, if it does not exist, print an error message
    try:
        return _global_dict[key]
    except:
        print('Read '+key+' failed\r\n')
