#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue May 22 12:59:48 2018

@author: fabian
"""

import pypsa
from pypsa.opt import Constraint as Con
import pandas as pd



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
    if attribute == 'renewable':
        carrier_constraints = ['hydro', 'nuclear']
    elif attribute == 'devplan':
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
