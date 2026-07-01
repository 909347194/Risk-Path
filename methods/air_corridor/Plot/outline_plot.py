#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/outline_plot.py
"""
Module: outline_plot
This module contains functions for plotting the outline of districts in a city related to emergency landing scenarios.
It includes functions to plot the geographic outlines of selected districts in a city.

Functions:
    my_outline(city): Plots the outline of the districts that we selected in a city.
"""

import matplotlib.pyplot as plt
import time
from Key_Elements.weight import get_value
import cartopy.crs as ccrs
from cnmaps import draw_map
from .base_functions import get_outline

def my_outline(city):
    """
    Plots the outline of the districts that we selected in a city.

    Parameters:
        city (str): The name of the city.

    Returns:
        None
    """
    _, urban_districts, whole_city = get_outline(city)
    alpha = 1.0
    fig = plt.figure(figsize=(21.6 * alpha, 21.6 * alpha))
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())

    draw_map(whole_city, ax=ax, linewidth=1.0, color='k', linestyle='--')
    for i in range(len(urban_districts)):
        draw_map(urban_districts[i], ax=ax, linewidth=1.0, color='k', linestyle='-')
        ax.add_geometries(urban_districts[i], crs=ccrs.PlateCarree(), facecolor='skyblue')

    ax.axis('off')

    time_now = time.time()
    plt.savefig(f"./Benchmark3/{time_now}_outline_{city}.jpg", transparent=True)
    return
