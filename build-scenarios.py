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

scenarios = pd.read_csv('scenario_limits.csv')
scenarios = scenarios.set_index(scenarios['scenario']).drop(columns='scenario').dropna(axis=1)

limits = scenarios.loc[2020]
flexibility = 0.1


def scenario_constraints(n,snapshots,limits=None,flexibility=0.1):
    carrier_constraints = ['wind', 'solar', 'hydro', 'bioenergy',
                           'hard coal', 'oil', 'ocgt', 'nuclear']
    
    for constraint in limits.index:
        if constraint in carrier_constraints:
            if constraint == 'hydro':
                index = n.storage_units[n.storage_units['carrier']==constraint].index
                setattr(n.model,constraint+"_limit_low",Con(expr=sum(n.model.storage_p_nom[name] \
                                                          for name in index) >= limits[constraint] * (1.-flexibility)))
                setattr(n.model,constraint+"_limit_up",Con(expr=sum(n.model.storage_p_nom[name] \
                                                          for name in index) <= limits[constraint] * (1.+flexibility)))
            else:
                index = n.generators[n.generators['carrier']==constraint].index
                setattr(n.model,constraint+"_limit_low",Con(expr=sum(n.model.generator_p_nom[name] \
                                                          for name in index) >= limits[constraint] * (1.-flexibility)))
                setattr(n.model,constraint+"_limit_up",Con(expr=sum(n.model.generator_p_nom[name] \
                                                          for name in index) <= limits[constraint] * (1.+flexibility)))
    return



def set_constraints(network, snapshots):
    return scenario_constraints(network, snapshots, limits = limits, flexibility = flexibility)


n.lopf(extra_functionality = set_constraints,
       snapshots=n.snapshots[0:1000], solver_name='gurobi', solver_options={"threads":4}, 
       formulation='kirchhoff', keep_files=True)

n.name = 'vietnam_2015_2016'
n.export_to_netcdf('vietnam_2015_2016.nc')
