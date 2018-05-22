#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue May 22 15:59:14 2018

@author: fabian
"""

import pypsa 
import matplotlib.pyplot as plt
from powerplantmatching.utils import tech_colors


n = pypsa.Network('vietnam_2015_2016.nc')

#%%
capas = n.generators.groupby(['bus','carrier']).p_nom_opt.mean().fillna(0.)
lines = n.lines.groupby(['bus0', 'bus1']).s_nom_opt.mean().fillna(0.)

capas = capas.loc[capas.index.levels[0][capas.groupby(level='bus').sum()!=0],:]

plotcapas = capas
plotlines = lines

fig, ax = plt.subplots(1,1, figsize=(10,10))

bus_scale = 4e4
link_scale = 5e1

colors = dict(zip(['ocgt','wind','hydro','solar', 'hard coal', 'oil', 'bioenergy'],
                  ['blue','green','navy','yellow', 'brown', 'k', 'darkgreen']))

n.plot(bus_sizes=plotcapas/bus_scale, bus_colors=colors, ax=ax,
             line_widths={'Link':0.0, 'Line':plotlines/link_scale},
             line_colors={'Link':'purple', 'Line':'indianred'})