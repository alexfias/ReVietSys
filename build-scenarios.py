#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue May 22 12:59:48 2018

@author: fabian
"""

import pypsa
from pypsa.opt import Constraint as Con
import pandas as pd

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



n = pypsa.Network('vietnam.nc')

# Configure scenario settings
scenarios = pd.read_csv('scenario_limits.csv')
scenarios = scenarios.set_index(scenarios['scenario']).drop(columns='scenario').dropna(axis=1)
limits = scenarios.loc[2020]
flexibility = 0.1

n.storage_units.p_nom_max = np.Inf
n.loads_t.p_set = n.loads_t.p_set * limits['load_increase']

model = 'fias-model'
data = 'era5-data'
attribute = 'test_runs'

name = 'vietnam'
scenario = '2020'

n.lopf(extra_functionality = set_constraints,
       snapshots=n.snapshots[0:8760], solver_name='gurobi', solver_options={"threads":12}, 
       formulation='kirchhoff', keep_files=True)

n.name = name + '_' + scenario
n.export_to_netcdf(model + '_' + data + '_' + attribute + '/' + scenario + '/' + name + '_'+ model + '.nc')
n.export_to_csv_folder(model + '_' + data + '_' + attribute + '/' + scenario + '/csv')
