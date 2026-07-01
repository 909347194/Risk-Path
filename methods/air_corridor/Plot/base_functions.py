#! /usr/bin/env python3
#! -*- coding:utf-8 -*-

# ./Emergency_Landing/Plot/base_functions.py
"""
Module: base_functions
This module contains utility functions for plotting and data manipulation in emergency landing scenarios.
It includes functions to explode 3D data arrays, convert float values to colors, and add color axes to plots.

Functions:
    explode(data): Expands a 3D array by inserting zeros between elements.
    float2color(zero2one): Converts a float value in the range [0, 1] to an RGBA color.
    add_right_cax(ax, pad, width): Adds a color axis (cax) to the right of an axis (ax).
"""

import matplotlib as mpl
import numpy as np
from cnmaps import get_adm_maps

def explode(data):
    """
    Expands a 3D array by inserting zeros between elements.

    Parameters:
        data (np.array): The input 3D array.

    Returns:
        np.array: The expanded 3D array.
    """
    size = np.array(data.shape)*2
    data_e = np.zeros(size - 1, dtype=data.dtype)
    data_e[::2, ::2, ::2] = data
    return data_e


def float2color(zero2one):
    """
    Converts a float value in the range [0, 1] to an RGBA color.

    Parameters:
        zero2one (float): The input float value.

    Returns:
        list: The RGBA color as a list of four float values.
    """
    x = zero2one * 255
    r = 255
    g = 255 - x
    b = 255
    r = round(float(r / 256), 2)
    g = round(float(g / 256), 2)
    b = round(float(b / 256), 2)
    return [r, g, b, 0.6]

def add_right_cax(ax, pad, width):
    """
    Adds a color axis (cax) to the right of an axis (ax).

    Parameters:
        ax (matplotlib.axes.Axes): The axis to add the color axis to.
        pad (float): The distance between the color axis and the main axis.
        width (float): The width of the color axis.

    Returns:
        matplotlib.axes.Axes: The created color axis.
    """
    axpos = ax.get_position()
    caxpos = mpl.transforms.Bbox.from_extents(
        axpos.x1 + pad,
        axpos.y0,
        axpos.x1 + pad + width,
        axpos.y1
    )
    cax = ax.figure.add_axes(caxpos)
    return cax

def add_left_cax(ax, pad, width):
    '''
    Add a cax to the left of an ax that is the same height as it
    Pad is the distance between cax and ax
    Width is the width of CAX
    '''
    axpos = ax.get_position()
    caxpos = mpl.transforms.Bbox.from_extents(
        axpos.x1 - pad,
        axpos.y0,
        axpos.x1 - pad + width,
        axpos.y1
    )
    cax = ax.figure.add_axes(caxpos)

    return cax

def add_down_cax(ax, pad, width):
    '''
    Add a cax to the downside of an ax that is the same height as it
    Pad is the distance between cax and ax
    Width is the width of CAX
    '''
    caxpos = mpl.transforms.Bbox.from_extents(
        ax[0],
        ax[1] + pad,
        ax[2],
        ax[1] + pad + width
    )

    return caxpos

def get_outline(city): 
    if city=='Beijing':
        beijing=get_adm_maps(province='北京市',only_polygon=True,record='first',engine='geopandas')
        haidian=get_adm_maps(province='北京市',city='北京市',district='海淀区',only_polygon=True,record='first',engine='geopandas')
        xicheng=get_adm_maps(province='北京市',city='北京市',district='西城区',only_polygon=True,record='first',engine='geopandas')
        dongcheng=get_adm_maps(province='北京市',city='北京市',district='东城区',only_polygon=True,record='first',engine='geopandas')
        shijingshan=get_adm_maps(province='北京市',city='北京市',district='石景山区',only_polygon=True,record='first',engine='geopandas')
        fengtai=get_adm_maps(province='北京市',city='北京市',district='丰台区',only_polygon=True,record='first',engine='geopandas')
        chaoyang=get_adm_maps(province='北京市',city='北京市',district='朝阳区',only_polygon=True,record='first',engine='geopandas')

        whole_city=beijing
        urban_district=haidian+xicheng+dongcheng+shijingshan+fengtai+chaoyang
        urban_districts=[haidian,xicheng,dongcheng,shijingshan,fengtai,chaoyang]

    elif city=='Shanghai':
        shanghai=get_adm_maps(province='上海市',only_polygon=True,record='first',engine='geopandas')
        huangpu=get_adm_maps(province='上海市',city='上海市',district='黄浦区',only_polygon=True,record='first',engine='geopandas')
        xuhui=get_adm_maps(province='上海市',city='上海市',district='徐汇区',only_polygon=True,record='first',engine='geopandas')
        changning=get_adm_maps(province='上海市',city='上海市',district='长宁区',only_polygon=True,record='first',engine='geopandas')
        jingan=get_adm_maps(province='上海市',city='上海市',district='静安区',only_polygon=True,record='first',engine='geopandas')
        putuo=get_adm_maps(province='上海市',city='上海市',district='普陀区',only_polygon=True,record='first',engine='geopandas')
        hongkou=get_adm_maps(province='上海市',city='上海市',district='虹口区',only_polygon=True,record='first',engine='geopandas')
        yangpu=get_adm_maps(province='上海市',city='上海市',district='杨浦区',only_polygon=True,record='first',engine='geopandas')
        baoshan=get_adm_maps(province='上海市',city='上海市',district='宝山区',only_polygon=True,record='first',engine='geopandas')
        jiading=get_adm_maps(province='上海市',city='上海市',district='嘉定区',only_polygon=True,record='first',engine='geopandas')
        qingpu=get_adm_maps(province='上海市',city='上海市',district='青浦区',only_polygon=True,record='first',engine='geopandas')
        songjiang=get_adm_maps(province='上海市',city='上海市',district='松江区',only_polygon=True,record='first',engine='geopandas')
        minhang=get_adm_maps(province='上海市',city='上海市',district='闵行区',only_polygon=True,record='first',engine='geopandas')
        pudong=get_adm_maps(province='上海市',city='上海市',district='浦东新区',only_polygon=True,record='first',engine='geopandas')
        chongming=get_adm_maps(province='上海市',city='上海市',district='崇明区',only_polygon=True,record='first',engine='geopandas')

        whole_city=shanghai
        urban_district=huangpu+xuhui+changning+jingan+putuo+hongkou+yangpu+baoshan+jiading+qingpu+songjiang+minhang+pudong+chongming
        urban_districts=[huangpu,xuhui,changning,jingan,putuo,hongkou,yangpu,baoshan,jiading,qingpu,songjiang,minhang,pudong,chongming]

    elif city=='Shenzhen':
        shenzhen=get_adm_maps(province='广东省',city='深圳市',only_polygon=True,record='first',engine='geopandas')
        shenzhen=get_adm_maps(province='广东省',city='深圳市',only_polygon=True,record='first',engine='geopandas')
        baoan=get_adm_maps(province='广东省',city='深圳市',district='宝安区',only_polygon=True,record='first',engine='geopandas')
        guangming=get_adm_maps(province='广东省',city='深圳市',district='光明区',only_polygon=True,record='first',engine='geopandas')
        nanshan=get_adm_maps(province='广东省',city='深圳市',district='南山区',only_polygon=True,record='first',engine='geopandas')
        longhua=get_adm_maps(province='广东省',city='深圳市',district='龙华区',only_polygon=True,record='first',engine='geopandas')
        futian=get_adm_maps(province='广东省',city='深圳市',district='福田区',only_polygon=True,record='first',engine='geopandas')
        luohu=get_adm_maps(province='广东省',city='深圳市',district='罗湖区',only_polygon=True,record='first',engine='geopandas')
        longgang=get_adm_maps(province='广东省',city='深圳市',district='龙岗区',only_polygon=True,record='first',engine='geopandas')
        yantian=get_adm_maps(province='广东省',city='深圳市',district='盐田区',only_polygon=True,record='first',engine='geopandas')
        pingshan=get_adm_maps(province='广东省',city='深圳市',district='坪山区',only_polygon=True,record='first',engine='geopandas')

        whole_city=shenzhen
        urban_district=baoan+guangming+nanshan+longhua+futian+luohu+longgang+yantian+pingshan
        urban_districts=[baoan,guangming,nanshan,longhua,futian,luohu,longgang,yantian,pingshan]

    elif city=='Chongqing':
        chongqing=get_adm_maps(province='重庆市',only_polygon=True,record='first',engine='geopandas')
        shapingba=get_adm_maps(province='重庆市',city='重庆市',district='沙坪坝区',only_polygon=True,record='first',engine='geopandas')
        jiulongpo=get_adm_maps(province='重庆市',city='重庆市',district='九龙坡区',only_polygon=True,record='first',engine='geopandas')
        nanan=get_adm_maps(province='重庆市',city='重庆市',district='南岸区',only_polygon=True,record='first',engine='geopandas')
        jiangbei=get_adm_maps(province='重庆市',city='重庆市',district='江北区',only_polygon=True,record='first',engine='geopandas')
        banan=get_adm_maps(province='重庆市',city='重庆市',district='巴南区',only_polygon=True,record='first',engine='geopandas')
        yubei=get_adm_maps(province='重庆市',city='重庆市',district='渝北区',only_polygon=True,record='first',engine='geopandas')
        beipei=get_adm_maps(province='重庆市',city='重庆市',district='北碚区',only_polygon=True,record='first',engine='geopandas')
        dadukou=get_adm_maps(province='重庆市',city='重庆市',district='大渡口区',only_polygon=True,record='first',engine='geopandas')
        yuzhong=get_adm_maps(province='重庆市',city='重庆市',district='渝中区',only_polygon=True,record='first',engine='geopandas')

        whole_city=chongqing
        urban_district=shapingba+jiulongpo+nanan+jiangbei+banan+yubei+beipei+dadukou+yuzhong
        urban_districts=[shapingba,jiulongpo,nanan,jiangbei,banan,yubei,beipei,dadukou,yuzhong]
        
    elif city=='Guangzhou':
        guangzhou=get_adm_maps(province='广东省',city='广州市',only_polygon=True,record='first',engine='geopandas')
        haizhu=get_adm_maps(province='广东省',city='广州市',district='海珠区',only_polygon=True,record='first',engine='geopandas')
        liwan=get_adm_maps(province='广东省',city='广州市',district='荔湾区',only_polygon=True,record='first',engine='geopandas')
        yuexiu=get_adm_maps(province='广东省',city='广州市',district='越秀区',only_polygon=True,record='first',engine='geopandas')
        tianhe=get_adm_maps(province='广东省',city='广州市',district='天河区',only_polygon=True,record='first',engine='geopandas')
        huangpu=get_adm_maps(province='广东省',city='广州市',district='黄埔区',only_polygon=True,record='first',engine='geopandas')
        panyu=get_adm_maps(province='广东省',city='广州市',district='番禺区',only_polygon=True,record='first',engine='geopandas')
        baiyun=get_adm_maps(province='广东省',city='广州市',district='白云区',only_polygon=True,record='first',engine='geopandas')

        whole_city=guangzhou
        urban_district=haizhu+liwan+yuexiu+tianhe+huangpu+panyu+baiyun
        urban_districts=[haizhu,liwan,yuexiu,tianhe,huangpu,panyu,baiyun]
    else:
        return

    return urban_district,urban_districts,whole_city
