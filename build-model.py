#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri May  4 09:29:00 2018

@author: fabian
"""

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

n = pypsa.Network('original-model_original-data')

#tranfer loads, fill NaNs in DongAnh with load values that are nearby its first entry
n.loads_t.p_set['DongAnh'] = n.loads_t.p_set['NghiSon']
#rescale loads (in MW) to approx value of
#https://www.worlddata.info/asia/vietnam/energy-consumption.php (in billion kWh)
n.loads_t.p_set = n.loads_t.p_set / n.loads_t.p_set.sum().sum() * (134.3 * 1e9) / 1e3
loads = n.loads_t.p_set.fillna(0).copy()
n.set_snapshots(pd.DatetimeIndex(start='2015', end='2017', closed='left', freq='h'))
n.loads_t.p_set = (pd.concat([loads.rename(index = lambda ds : ds - pd.Timedelta(270 - i * 52,'W'))
                                 for i in [0,1,2]])
                              [lambda df : ~df.index.duplicated()].reindex(n.snapshots))

n.lines['type'] = '490-AL1/64-ST1A 380.0'
n.lines['s_nom_min'] = (np.sqrt(3) * n.lines['type'].map(n.line_types.i_nom) *
                        n.lines.bus0.map(n.buses.v_nom) * n.lines.num_parallel)


storages = pd.read_csv('storage_units.csv', index_col=0)


#drop generators
n.mremove('Generator', n.generators.index)
n.buses['substation_lv'] = True # assume all buses are substations

#add generators from pm 
pm.config.set_target_countries('Vietnam')
ppl = (pm.data.WRI(filter_other_dbs=False) #could also match with pm.data.CARMA()
        .replace({'Fueltype': {'Gas': 'Ocgt'}}))
ppl.loc[ppl.Fueltype=='Hydro', 'Set'] = 'Store'

pm.export.to_pypsa_network(ppl, n)
n.generators = n.generators.assign(p_nom_min = n.generators.p_nom).assign(p_nom_extendable = True)

n.storage_units = (n.storage_units.assign(max_hours = 
                                         storages.max_hours.reindex(n.storage_units.index).fillna(0))
                                 .assign(p_nom_min = n.storage_units.p_nom)
                                 .assign(p_nom_extendable = True))

#add artificial generators for vres 
carriers = ['wind', 'solar', 'bioenergy', 'hard coal', 'oil', 'ocgt', 'nuclear']
for carrier in carriers:
    not_included = ((n.buses.index).difference(
                        n.generators[n.generators.carrier == carrier].set_index('bus').index) )
    n.madd('Generator', names = not_included + ' ' + carrier,
                        bus = not_included, carrier=carrier, 
                        p_nom_extendable = True) 

not_included = ((n.buses.index).difference(
                    n.storage_units[n.storage_units.carrier == 'hydro'].set_index('bus').index) )
n.madd('StorageUnit', names = not_included + ' ' + 'hydro',
                    bus = not_included, carrier='hydro',
                    p_nom_extendable = True) 


vietshape = vshapes.countries(subset=['VN'])['VN']
onshore_locs = n.buses.loc[:, ["x", "y"]]
regions = gpd.GeoDataFrame({
        'geometry': voronoi_partition_pts(onshore_locs.values, vietshape),
        'country': 'VN'}, index=onshore_locs.index).rename_axis('bus')
regions.crs = {'init': u'epsg:4326'}
regions['Area'] = regions.geometry.to_crs({'init': 'epsg:3395'}).map(lambda p: p.area / 10**6)


#%% add cutout
    
#TODO recalculate cutout
cutout = atlite.Cutout("vietnam-2015-2016-era5", 
                       module='era5', 
                       bounds=[101,8, 110, 24],
                       years=slice(2015,2016, None))

cells = gpd.GeoDataFrame({'geometry' : cutout.grid_cells()})
cells.crs = {'init': u'epsg:4326'}
cells['Area'] = cells.geometry.to_crs({'init': 'epsg:3395'}).map(lambda p: p.area / 10**6)

meta = ( cutout.meta.drop(['height', 'time', 'year-month', 'lat', 'lon'])
                 .to_dataframe().reset_index() )

indicatormatrix = cutout.indicatormatrix(regions.geometry)

#%% add layouts

def custum_layout(meta, cap_per_sq_km):
    return meta.assign(caps = cells.Area * cap_per_sq_km).set_index(['x','y']) \
                .fillna(0).to_xarray().transpose().caps

#hydro
kdtree = KDTree(meta[['x','y']].values)
hydro = ppl[ppl.Fueltype.isin(['hydro'])] 
hydro_grouped = (hydro.assign(
                cell = meta.index[kdtree.query(hydro[['lon','lat']].values)[1]])
                             .groupby(['Fueltype','cell']).Capacity.sum() )

#fill p_nom_max density for unbuilt capacities
#alternative could be 25% quantile of cell density 
hydro_missing_cap = ((n.storage_units.groupby(['carrier', 'bus']).p_nom.sum()['hydro'] / regions.Area)
                        [lambda ds:ds != 0].min())

#expand upper bound for existing capacities by 15% 
hydro_layout = (pd.concat([meta, hydro_grouped.unstack(0)], axis=1)
          .set_index(['x','y']).mul(1.15) 
          .fillna(hydro_missing_cap).to_xarray().transpose())

#%% calaculate profile via atlite

method = {'wind':'wind', 
          'solar':'pv', 
          'hydro':'runoff'}

resource = {'wind' : {'turbine': 'Vestas_V112_3MW',
                         'layout': custum_layout(meta, 10),
                         'per_unit':True, 'smooth':True
                         }, 
            'solar' : {'panel': 'CSi', 'orientation': 'latitude_optimal',
                       'layout' : custum_layout(meta, 170), 
                       'per_unit':True},
            'hydro' : {'layout': custum_layout(meta, hydro_missing_cap), 
                     'per_unit':False,
                     'smooth':True} }


for carrier in method.keys():
    print(carrier)

    func = getattr(cutout, method[carrier])
    profile, capacities = func(matrix=indicatormatrix, index=regions.index,
                           return_capacity=True, **resource[carrier])
        
    profile = (profile.to_pandas().T.rename(columns=lambda x: x + ' ' + carrier))
    capacities = capacities.to_series().rename(index = lambda ds: ds + ' ' + carrier) 

    if carrier=='hydro':
#        assume hydro generation statistics 
#        from https://www.hydropower.org/country-profiles/vietnam
        
        capacities = n.storage_units.p_nom_min.where( n.storage_units.p_nom_min > 0, capacities)
        inflow = profile * capacities
        #assume about 10% will be spillage
        inflow *= (120*1e6)/inflow.sum().reindex((n.storage_units.p_nom_min>0).index).sum() 
        n.storage_units_t.inflow = inflow
        n.storage_units.p_nom_max = capacities * 1.1  

    else:       
        n.generators.loc[capacities.index, 'p_nom_max'] = capacities
        n.generators_t.p_max_pu =  pd.concat( [n.generators_t.p_max_pu , profile], axis=1)


#only assumptions, no research done on this yet
costs = pd.read_csv('costs.csv', index_col=0)
n.generators['marginal_cost'] = n.generators.carrier.map(costs.marginal)
n.generators['capital_cost'] = n.generators.carrier.map(costs.capital)
n.generators['weight'] = 1 
n.storage_units['marginal_cost'] = n.storage_units.carrier.map(costs.marginal)
n.storage_units['capital_cost'] = n.storage_units.carrier.map(costs.capital)
n.lines.capital_cost =  n.lines.length


#only assumptions, no research done on this yet
n.carriers = n.carriers.rename(index= lambda ds: ds.lower()).rename(index= {'windon': 'wind'})
co_2 = dict(zip(carriers, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,]))
short = dict(zip(carriers, ['W', 'S', 'B', 'C', 'O', 'G', 'N']))
for carrier in carriers:
    n.carriers.loc[carrier, 'co2_emissions'] = co_2[carrier]
    n.carriers.loc[carrier, 'short_name'] = short[carrier]
n.carriers.loc['hydro', 'co2_emissions'] = 0.0
n.carriers.loc['hydro', 'short_name'] = 'H'

n.export_to_netcdf('vietnam.nc')
