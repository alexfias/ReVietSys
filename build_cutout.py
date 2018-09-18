#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu May  3 11:00:41 2018

@author: fabian
"""

import atlite
import pypsa



cutout = atlite.Cutout("vietnam-2015-2016-era5", 
                       module='era5', 
                       bounds=[100,6, 112,25],
                       years=slice(2015,2016, None))
cutout.prepare()
