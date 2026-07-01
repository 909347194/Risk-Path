#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Key_Elements/point_params.py

from Data_Process.preprocess import haversine_distance
import numpy as np


# weights in the model
# alpha_f = 0.7 # fatality risk cost
# alpha_b = 0.2 # property risk cost
# alpha_n = 0.1  # noise impact cost
# gamma = 3.16e3 # Magnification coefficient, sqrt(10)e3

# map param
x_ratio = 40.0
y_ratio = 40.0

# scale
dx = 1000.0*haversine_distance(0.0,0.0,1.0e-4,0.0)
dy = 1000.0*haversine_distance(0.0,0.0,0.0,1.0e-4)
dz = 3

# a=alpha_n # noise cost param
A=0.99 # risk weight


# params definition
pi = np.pi # pi
P_crash = 3.42*1e-4 # the probability of UAV system failure
S_c = 0.1 # sheltering coefficient (0,1]
alpha = 10e6 # (J) the impact energy that might cause 50% fatality with S_c = 0.5
beta = 100.0 # (J) the impact energy threshold required to cause fatality as S_c -> 0
m = 9.2 # (kg) mass of UAV
R_I = 0.3 # the drag coefficient
rho_A = 1.225 # (kg/m3) the density of air
# v_TAS = 0 # the true airspeed of the falling UAV
gravity = 9.8 # (m/s2) the gravity acceleration
# h = 120 # the height of the UAV above the ground
S_hit = 4.88 # (m2) the size of UAV crash impact area

# Fatality risk to pedestrians
# R_f_p = 0.2 # the fatality rate that people killed in UAV accidents
# sigma_p = 8.358*10e3 # (people/km2) the population density in the administrative unit

# Fatality risk to persons in the vehicle
R_f_v = 0.8 # the average fatality rate the persons in vehicles are killed
# sigma_v = 7.12*10e3 # (vehicle/km2) the vehicle density in a road network

# Estimation of population density and traffic density
# sigma_p_avg = 0 # the average population density in the whole area
# r = 1.0 # (km) the radius of the gravity influence area induced by the amenity
# sigma_v_avg = 0 # the average traffic density in the given area

# Property damage risk cost model
# h_b = 100.0 # (m) building height
# miu = 3.0467 # mean of the logarithmic variable
# sigma = 0 # standard deviation of the logarithmic variable

# Noise impact cost model
# I_noise = 0 # the sound intensity
# L_sl = 0 # (dB) sound level
omega = 0.9 # conversion factor from sound intensity to sound level
L_h = 55.0 # (dB) the reference noise produced by drone
d = 9.1 # (m) average distance between UAVs and pedestrians

# assess the risk of a grid
# Cr_f_max = 10e-8
# Cr_p_d_max = 10e-8