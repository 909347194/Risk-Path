#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/in_map.py

def inmap(x,y,z,data):
    '''
    This function is to judge whether (x, y, z) is within data map.
    '''

    return ((x>=0 and x<data.shape[0] and y>=0 and y<data.shape[1] and z>=0 and z<data.shape[2]) and not (x==0 and y==0 and z==0))
