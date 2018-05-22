#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue May 22 12:59:48 2018

@author: fabian
"""

import pypsa
from pypsa.opt import Constraint as Con
import pandas as pd

n = pypsa.Network('vietnam.nc')

#%%

limits = pd.Series({    
            'solar' : 12000.,
            'wind' : 6000.,
            'hard coal' : 55300.,
            'ocgt' : 19000.,
            'oil' : 1000.})
        
def scenario_constraints(n,snapshots,limits=None,flexibility=0.1): 
  for carrier in limits.index:    
     index = n.generators[n.generators['carrier']==carrier].index
        
     setattr(n.model,carrier+"_limit_low",Con(expr=sum(n.model.generator_p_nom[name] \
                                          for name in index) >= limits[carrier] * (1.-flexibility)))
     setattr(n.model,carrier+"_limit_up",Con(expr=sum(n.model.generator_p_nom[name] \
                                         for name in index) <= limits[carrier] * (1.+flexibility)))
  return



def set_constraints(network, snapshots):
    return scenario_constraints(network, snapshots, limits = limits)

n.lopf(extra_functionality = set_constraints,
       snapshots=n.snapshots[0:1000], solver_name='gurobi', solver_options={"threads":4}, 
       formulation='kirchhoff')

n.name = 'vietname_2015_2016'
n.export_to_netcdf('vietnam_2015_2016.nc')
