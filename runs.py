import pypsa 
import atlite 
import vresutils.shapes as vshapes
from vresutils.graph import voronoi_partition_pts
import geopandas as gpd
import powerplantmatching as pm
import pandas as pd
from scipy.spatial import KDTree
import numpy as np
import geopandas as gpd

from pypsa.opt import Constraint as Con

import matplotlib.pyplot as plt
%matplotlib inline
import xarray as xr


def scenario_constraints(n, snapshots, limits=None, flexibility=0.1,
                         carrier_constraints=None):

    for constraint in limits.index:
        if constraint in carrier_constraints:
            if constraint == 'hydro':
                index = n.storage_units[n.storage_units['carrier']==constraint].index
                setattr(n.model,constraint+"_limit_low",
                        Con(expr=sum(n.model.storage_p_nom[name] \
                        for name in index) >= limits[constraint] * (1.-flexibility)))
                setattr(n.model,constraint+"_limit_up",
                        Con(expr=sum(n.model.storage_p_nom[name] \
                        for name in index) <= limits[constraint] * (1.+flexibility)))
            else:
                index = n.generators[n.generators['carrier']==constraint].index
                setattr(n.model,constraint+"_limit_low",
                        Con(expr=sum(n.model.generator_p_nom[name] \
                        for name in index) >= limits[constraint] * (1.-flexibility)))
                setattr(n.model,constraint+"_limit_up",
                        Con(expr=sum(n.model.generator_p_nom[name] \
                        for name in index) <= limits[constraint] * (1.+flexibility)))
    return

def get_limits(year):
    scenarios = pd.read_csv('scenario_limits.csv')
    scenarios = (scenarios
                 .set_index(scenarios['scenario'])
                 .drop(columns='scenario')
                 .dropna(axis=1))
    return scenarios.loc[year]

def scenario_lopf(year=2020, attribute='devplan', flexibility=0.1):
    if attribute == 'devplan':
        carrier_constraints = ['hydro', 'nuclear']
    elif attribute == 'renewable':
        carrier_constraints = ['wind', 'solar', 'hydro', 'bioenergy',
                               'hard coal', 'oil', 'ocgt', 'nuclear']
    else:
        raise(SyntaxError('No valid attribute {}'.format(attribute)))

    limits = get_limits(year)
    def set_constraints(network, snapshots):
        return scenario_constraints(network, snapshots,
                                    limits=limits,
                                    flexibility=flexibility,
                                    carrier_constraints=carrier_constraints)
    return set_constraints


model = 'fias-model'
data = 'era5-data'
attribute = 'devplan'  # or 'renewable'
name = 'vietnam'
fn = 'vietnam3_storage.nc'


for year in [2020, 2025, 2030]:
    n = pypsa.Network(fn)
    n.storage_units.p_nom_max = np.Inf
    n.loads_t.p_set = n.loads_t.p_set * get_limits(year)['load_increase']
    scenario = '{}_{}_{}'.format(attribute, year, 'storage')
    n.lopf(extra_functionality = scenario_lopf(year=year, attribute=attribute, flexibility=0.1),
           snapshots=n.snapshots[:8760],
           solver_name='gurobi',
           solver_options={"threads":12, "method":-1, "crossover":-1},
           formulation='kirchhoff', keep_files=False)

    n.name = name + '_' + scenario
    n.export_to_csv_folder('/home/vres/data/ReVietSys/' + model + '_' +
                           data + '/' + scenario)
