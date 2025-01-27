#!/usr/bin/python3

import pypsa
import pandas as pd
import numpy as np
import sys
from pypsa.opt import Constraint as Con


def renewable_scenario_constraints(n,snapshots,limits=None,flexibility=0.1):
    carrier_constraints = ['hydro', 'nuclear', 'hydro ror']
    
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

def renewable_set_constraints(network, snapshots):
    return renewable_scenario_constraints(network, snapshots, limits = limits, flexibility = flexibility)


model = 'fias-model'
data = 'era5-data'
name = 'vietnam'
fn = './../vietnam3.nc'

attribute = 'renewable'  # or 'devplan'
storage = False
year = 2020

scenarios = pd.read_csv('./../scenario_limits.csv')
scenarios = scenarios.set_index(scenarios['scenario']).drop(columns='scenario').dropna(axis=1)
limits = scenarios.loc[year]
flexibility = 0.1

n = pypsa.Network(fn)

co2_limit = 1.84*87.84e6*0.05 #tons_per_citizen*citizens http://www.worldbank.org/ 2011 data
n.global_constraints = n.global_constraints.reindex(['co2_limit'])
n.global_constraints.type = 'primary_energy'
n.global_constraints.carrier_attribute = 'co2_emissions'
n.global_constraints.sense = '<='
n.global_constraints.constant = co2_limit #tons
n.global_constraints.mu = 0.0

#n.storage_units.p_nom_max = np.Inf
n.loads_t.p_set = n.loads_t.p_set * limits['load_increase']

if storage == True:
    scenario = '{}_{}_{}'.format(attribute, year, 'storage')
else:
    scenario = '{}_{}'.format(attribute, year)
n.lopf(extra_functionality = renewable_set_constraints,
       snapshots=n.snapshots[:8760],
       solver_name='gurobi',
       solver_options={"threads":32, "method":-1, "crossover":-1},
       formulation='kirchhoff', keep_files=False,
       solver_logfile=sys.argv[1]+'.log')

n.name = name + '_' + scenario
n.export_to_csv_folder('/home/vres/data/ReVietSys/' + model + '_' +
                   data + '/' + scenario)
