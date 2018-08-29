#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 28 14:17:50 2018

@author: fabian
"""

import pypsa
import pandas as pd
import numpy as np
from build_scenarios import scenario_lopf, get_limits

model = 'fias-model'
data = 'era5-data'
attribute = 'devplan'  # or 'renewable'
name = 'vietnam'
fn = 'vietnam3_storage.nc'


for year in [2020, 2025, 2030]:
    n = pypsa.Network(fn)
    n.storage_units.p_nom_max = np.Inf
    n.loads_t.p_set = n.loads_t.p_set * get_limits(year)['load_increase']
    scenario = '{}_{}'.format(attribute, year)
    n.lopf(extra_functionality = scenario_lopf(year, attribute=attribute),
           snapshots=n.snapshots[:8760],
           solver_name='gurobi',
           solver_options={"threads":12, "method":-1, "crossover":-1},
           formulation='kirchhoff', keep_files=False)

    n.name = name + '_' + scenario
    n.export_to_csv_folder('/home/vres/data/ReVietSys/' + model + '_' +
                           data + '/' + scenario)