#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Air_Corridor_Design/Key_Elements/Point.py
"""
Module: point_class
This module defines the Point class, which represents a point in a 3D space with various attributes
such as coordinates, densities, risk, noise, and state vector. It also includes methods to set
pedestrian and vehicle densities.

Classes:
    Point: Represents a point in a 3D space with various attributes and methods.
"""

import numpy as np
from .weight import get_value
from shapely.geometry import Polygon
from .point_params import *

class Point(object):
    def __init__(self, x=0, y=0, z=0, alpha_n=0, PeoDens=0.0, VehDens=0.0):
        """
        A class to represent a point in a 3D space.

        Attributes:
            x (int): X-coordinate of the point.
            y (int): Y-coordinate of the point.
            z (int): Z-coordinate of the point.
            h (float): Height of the point.
            PeoDens (float): Pedestrian density at the point.
            VehDens (float): Vehicle density at the point.
            risk (float): Risk value at the point.
            noise (float): Noise value at the point.
            Cr_f (float): Crash risk factor.
            Cr_p_d (float): Crash probability density.
            alpha_n (int): Alpha value.
            P_crash (float): Crash probability.
            father (Point): Parent point.
            isread (bool): Read status.
            StateVector (np.array): State vector.
            index (int): Index of the point.
            geometry (object): Geometry of the point.
            Building (list): Building risk assessment.
        """
        self.x = x
        self.y = y
        self.z = z
        self.h = (z + 0.5) * dz
        self.PeoDens = PeoDens
        self.VehDens = VehDens
        self.risk = 0.0
        self.noise = 0.0
        self.Cr_f = 0.0
        self.Cr_p_d = 0.0
        self.Cr_r = 0.0
        self.alpha_n = alpha_n
        # self.P_crash=float(np.random.randint(3,5))*1e-6
        self.P_crash = P_crash
        # self.P_crash=5.0*10e-5
        self.father = None
        self.isread = False
        # state_vector=[Distance, Cost_all_i, Acumulative Rnoise, Cost_rescue, j=0->i(1-pj)]
        # self.StateVector=np.array([float('inf'),0.0,0.0,0.0])
        self.StateVector = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        self.index = -1
        self.geometry = None
        # building risk assessment
        # (area,height)
        self.Building = []
        # self.miu=0.0
        # self.sigma=0.0
        

    def set_PeoDens(self,_PeoDens):
        self.PeoDens = _PeoDens

    def set_VehDens(self,_VehDens):
        self.VehDens = _VehDens
    
    def set_Cr_f(self,_Cr_f):
        self.Cr_f = _Cr_f

    def set_Cr_r(self,_Cr_r):
        self.Cr_r = _Cr_r

    def set_risk(self,_risk):
        self.risk = _risk

    def set_noise(self,_noise):
        self.noise = _noise

    def get_statevector(self,Pk):
        Dis = Pk.StateVector[0] + np.sqrt((self.x - Pk.x)**2 + (self.y - Pk.y)**2 + (self.z - Pk.z)**2)
        TPR_Cost = Pk.StateVector[1] + (self.risk + self.alpha_n * (self.noise + Pk.StateVector[2])) \
                * Pk.StateVector[4] * self.P_crash
        Anoise = self.noise + Pk.StateVector[2]
        Rescue_cost = Pk.StateVector[3] + self.Cr_r * Pk.StateVector[4] * self.P_crash
        # P_safe = Pk.StateVector[3]-self.P_crash
        P_safe = Pk.StateVector[4] * (1 - self.P_crash)
        return np.array([Dis, TPR_Cost, Anoise, Rescue_cost, P_safe])

    def set_statevector(self,array):
        self.StateVector[0] = array[0]
        self.StateVector[1] = array[1]
        self.StateVector[2] = array[2]
        self.StateVector[3] = array[3]
        self.StateVector[4] = array[4]

    def set_geometry(self,lat_max,lon_min):
        p00 = (lon_min + self.y * y_ratio * 1.0e-4, lat_max - self.x * x_ratio * 1.0e-4)
        p01 = (lon_min + self.y * y_ratio * 1.0e-4, lat_max - (self.x + 1) * x_ratio * 1.0e-4)
        p11 = (lon_min + (self.y + 1) * y_ratio * 1.0e-4, lat_max - (self.x + 1) * x_ratio * 1.0e-4)
        p10 = (lon_min + (self.y + 1) * y_ratio * 1.0e-4, lat_max - self.x * x_ratio * 1.0e-4)
        self.geometry = Polygon([p00, p01, p11, p10])

    """def __lt__(self,other):
        array1=self.StateVector
        array2=other.StateVector
        index=self.index
        if index==0 or index==1:
            if array1[0]>array2[0]:
                return False
            elif array1[0]==array2[0]:
                if array1[1]>array2[1]:
                    return False
                elif array1[1]==array2[1]:
                    if array1[3]<array2[3]: #!!!
                        return False
                    elif array1[3]==array2[3]:
                        if array1[2]>array2[2]:
                            return False
                        else:
                            return True
                    else:
                        return True
                else:
                    return True
            else:
                return True
        elif index==2:
            if array1[1]/(array1[0]+0.00001)>array2[1]/(array2[0]+0.00001):
                return False
            elif array1[1]/(array1[0]+0.00001)==array2[1]/(array2[0]+0.00001):
                if array1[3]<array2[3]:
                    return False
                elif array1[3]==array2[3]:
                    if array1[2]>array2[2]:
                        return False
                    else:
                        return True
                else:
                    return True
            else:
                return True
        else:
            if array1[1]>array2[1]:
                return False
            elif array1[1]==array2[1]:
                if array1[3]<array2[3]:
                    return False
                elif array1[3]==array2[3]:
                    if array1[2]>array2[2]:
                        return False
                    else:
                        return True
                else:
                    return True
            else:
                return True"""

    # change the comparison method
    def __lt__(self, other):
        array1 = self.StateVector
        array2 = other.StateVector
        ER_Weight_Distance = get_value('ER_Weight_Distance')
        ER_Weight_Rescue = get_value('ER_Weight_Rescue')
        Enlarge_param_TPR = get_value('Enlarge_param_TPR')
        Enlarge_param_Rescue = get_value('Enlarge_param_Rescue')
        index = self.index
        if index == 0:
            if array1[0] > array2[0]:
                return False
            else:
                return True
        elif index == 1:
            if ER_Weight_Distance * array1[0] + Enlarge_param_TPR * (1 - ER_Weight_Distance - ER_Weight_Rescue) * array1[1] + \
                Enlarge_param_Rescue * ER_Weight_Rescue * array1[3] > \
                ER_Weight_Distance * array2[0] + Enlarge_param_TPR * (1 - ER_Weight_Distance - ER_Weight_Rescue) * array2[1] + \
                Enlarge_param_Rescue * ER_Weight_Rescue * array2[3]:
                return False
            else:
                return True
        else:
            if array1[1] > array2[1]:
                return False
            else:
                return True

# todo : change the comparison method
def sv_lt(array1, array2, index):
    ER_Weight_Distance = get_value('ER_Weight_Distance')
    ER_Weight_Rescue = get_value('ER_Weight_Rescue')
    Enlarge_param_TPR = get_value('Enlarge_param_TPR')
    Enlarge_param_Rescue = get_value('Enlarge_param_Rescue')
    if index == 0:
            if array1[0] > array2[0]:
                return False
            else:
                return True
    elif index == 1:
        if ER_Weight_Distance * array1[0] + Enlarge_param_TPR * (1 - ER_Weight_Distance - ER_Weight_Rescue) * array1[1] + \
            Enlarge_param_Rescue * ER_Weight_Rescue * array1[3] > \
            ER_Weight_Distance * array2[0] + Enlarge_param_TPR * (1 - ER_Weight_Distance - ER_Weight_Rescue) * array2[1] + \
            Enlarge_param_Rescue * ER_Weight_Rescue * array2[3]:
            return False
        else:
            return True
    else:
        if array1[1] > array2[1]:
            return False
        else:
            return True



def get_peo_risk(p, x_ratio, y_ratio):
    # Cr_f, the fatality risk cost
    # sigma_p = np.exp(1-r^2)*sigma_p_avg
    # sigma_v = np.exp(1-r^2)*sigma_v_avg
    
    # v, the velocity when the drone hit the ground
    h = p.h
    v = np.sqrt(2 * m * gravity / (R_I * S_hit * rho_A) * (1 - np.exp(-h*R_I*S_hit*rho_A/m)))
    
    # E_imp, the kinetic energy of falling drone primarily
    E_imp = 0.5 * m * v**2
    
    R_f_p = (1 + np.sqrt(alpha/beta) * (beta/E_imp)**(1/(4*S_c)))**(-1)
    
    # N_hit_p, the number of pedestrians hit by crashed drone
    sigma_p = p.PeoDens / (dx * dy * x_ratio * y_ratio) * 10e6
    N_hit_p = S_hit * sigma_p
    
    # Cr_p, the fatality risk cost to pedestrians
    Cr_p = p.P_crash * N_hit_p * R_f_p

    # N_hit_v, the number of vehicles hit by the crashed drone
    sigma_v = p.VehDens / (dx * dy * x_ratio * y_ratio) * 10e6
    N_hit_v = S_hit * sigma_v
    # Cr_v, the fatality risk cost to person in the vehicle
    Cr_v = p.P_crash * N_hit_v * R_f_v

    Cr_f = Cr_p + Cr_v

    # # Cr_p_d, property damage risk cost
    # if h_b>0 and h_b<=np.exp(miu):
    #     Cr_p_d=1/(h_b*sigma*np.sqrt(2*pi))
    # elif h_b > np.exp(miu):
    #     Cr_p_d=1/(h_b*sigma*np.sqrt(2*pi))*np.exp(-(np.log(h_b)-miu)^2/(2*sigma^2))
    # Cr_p_d=10e-8

    # global Cr_f_max
    # # global Cr_p_d_max
    # Cr_f_max=max(Cr_f_max,Cr_f)
    # Cr_p_d_max=max(Cr_p_d_max,Cr_p_d)

    return Cr_f

# assess noise disturbance

def get_noise(p):
    # Cnoise, the cost of noise impact
    # h_r, vertical distance between the drone and people
    h_r = abs(p.h - 1.7) + 0.5 * dz
    # d_r, horizontal distance between the drone and people
    # d_r = np.sqrt(((p.x-op.x)*dx*x_ratio)**2+((p.y-op.y)*dy*y_ratio)**2)
    
    # Cnoise = omega*L_h/(h_r**2+d_r**2)
    # Cnoise = (p.PeoDens+p.VehDens+100)*omega*L_h/(h_r**2)
    C_noise = omega * L_h/(h_r**2 + d**2)
    # global Cnoise_max
    # Cnoise_max=max(Cnoise_max,Cnoise)

    return C_noise
