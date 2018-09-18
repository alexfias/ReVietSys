import pypsa
import pandas as pd
import numpy as np
import sys
sys.path.append('./../')

try:
    from build_scenarios import scenario_lopf, get_limits
except ImportError:
    print('No Import')



model = 'fias-model'
data = 'era5-data-disconnected'
name = 'vietnam'
fn = './../vietnam3_storage_disconnected.nc'

attribute = 'devplan'  # or 'renewable'
storage = True
year = 2020
flexibility=0.1

n = pypsa.Network(fn)
n.storage_units.p_nom_max = np.Inf
n.loads_t.p_set = n.loads_t.p_set * get_limits(year)['load_increase']
if storage == True:
    scenario = '{}_{}_{}'.format(attribute, year, 'storage')
else:
    scenario = '{}_{}'.format(attribute, year)
n.lopf(extra_functionality = scenario_lopf(year, attribute=attribute, flexibility=flexibility),
       snapshots=n.snapshots[:8760],
       solver_name='gurobi',
       solver_options={"threads":32, "method":-1, "crossover":-1},
       formulation='kirchhoff', keep_files=False)

n.name = name + '_' + scenario
n.export_to_csv_folder('/home/vres/data/ReVietSys/' + model + '_' +
                   data + '/' + scenario)
