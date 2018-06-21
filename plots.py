#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue May 22 15:59:14 2018

@author: fabian
"""

import pypsa 
import matplotlib.pyplot as plt
from powerplantmatching.utils import tech_colors

model = 'fias-model'
data = 'era5-data'
attribute = 'test_runs'

name = 'vietnam'
scenario = '2020'

n = pypsa.Network(model + '_' + data + '_' + attribute + '/' + scenario + '/' + name + '_'+ model + '.nc')

#%%
capas = n.generators.groupby(['bus','carrier']).p_nom_opt.mean().fillna(0.)
stores = n.storage_units.groupby(['bus','carrier']).p_nom_opt.mean().fillna(0.)
lines = n.lines.groupby(['bus0', 'bus1']).s_nom_opt.mean().fillna(0.)

capas = capas.loc[capas.index.levels[0][capas.groupby(level='bus').sum()!=0],:]
capas = capas.unstack(level=1)
capas['hydro'] = stores.unstack(level=1)
capas = capas.stack(level=0)

plotcapas = capas
plotlines = lines

fig, ax = plt.subplots(1,1, figsize=(15,15))

bus_scale = 2e4
link_scale = 4e2

colors = dict(zip(['ocgt', 'wind', 'solar', 'hydro', 'hard coal', 'oil', 'bioenergy', 'nuclear', 'perpetuum'],
                  ['blue', 'green', 'yellow', 'navy', 'brown', 'black', 'darkgreen', 'lime', 'pink']))

n.plot(bus_sizes=plotcapas/bus_scale, bus_colors=colors, ax=ax,
             line_widths={'Link':0.0, 'Line':plotlines/link_scale},
             line_colors={'Link':'purple', 'Line':'indianred'})
