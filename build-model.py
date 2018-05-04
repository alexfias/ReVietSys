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


n = pypsa.Network('original-model')
n.set_snapshots(pd.DatetimeIndex(start='2015', end='2017', closed='left', freq='h'))

#drop generators
n.mremove('Generator', n.generators.index)
n.buses['substation_lv'] = True # assume all are substations

#add generators from pm 
pm.config.set_target_countries('Vietnam')
ppl = pm.data.WRI(filter_other_dbs=False) #could also match with pm.data.CARMA()
#assume all hydro are rors
ppl, ror  = ppl[ppl.Fueltype != 'Hydro'], ppl[ppl.Fueltype == 'Hydro'] 
pm.export.to_pypsa_network(ppl, n)




vietshape = vshapes.countries(subset=['VN'])['VN']
onshore_locs = n.buses.loc[:, ["x", "y"]]
regions = gpd.GeoDataFrame({
        'geometry': voronoi_partition_pts(onshore_locs.values, vietshape),
        'country': 'VN'}, index=onshore_locs.index).rename_axis('bus')


#%% add layout for rors 
cutout = atlite.Cutout("vietnam-2015-2016-era5", 
                       module='era5', 
                       bounds=[101,8, 110, 23],
                       years=slice(2015,2016, None))

layout = ( cutout.meta.drop(['height', 'time', 'year-month', 'lat', 'lon'])
                 .to_dataframe().reset_index() )

kdtree = KDTree(layout[['x','y']].values)
ror_grouped = (ror.assign(
                cell = layout.index[kdtree.query(ror[['lon','lat']].values)[1]])
                             .groupby(['Fueltype','cell']).Capacity.sum() )

ror_layout = (pd.concat([layout, ror_grouped.unstack(0)], axis=1)
          .set_index(['x','y'])
          .fillna(0).to_xarray().transpose())['Hydro']


#%% add solar, wind

indicatormatrix = cutout.indicatormatrix(regions.geometry)

method = {'onshore':'wind', 
          'offshore':'wind', 
          'solar':'pv', 
          'ror':'runoff'}

resource = {'onshore' : {'turbine': 'Vestas_V112_3MW'}, 
            'offshore' : {'turbine': 'NREL_ReferenceTurbine_5MW_offshore'},
            'solar' : {'panel': 'CSi', 'orientation': 'latitude_optimal'},
            'ror' : {'layout': ror_layout} }

correction_factor = {'onshore':1, 
                     'offshore':1, 
                     'solar':0.882, 
                     'ror':1}

for carrier in method.keys():
    print(carrier)

    func = getattr(cutout, method[carrier])
    profile, capacities = func(matrix=indicatormatrix, index=regions.index,
                           per_unit=True, 
                           return_capacity=True, **resource[carrier])
        
    profile = (correction_factor[carrier] * profile.to_pandas().T
                           .rename(columns=lambda x: x + ' ' + carrier))

    if carrier=='ror':
#        assume ror generation statistics 
#        from https://www.hydropower.org/country-profiles/vietnam
        stats = pd.Series([52., 52.], index=[2015, 2016]) * 1e3
        gen_per_year = (profile.groupby(pd.Grouper(freq='y')).sum() * 
                         capacities.to_series().rename(index= lambda x : x + ' ' + carrier)
                        ).sum(1).rename(index=lambda x : x.year)
        scale_factor = (1/ gen_per_year * stats)
        profile = profile.mul(pd.Series(n.snapshots.year, 
                                        index=n.snapshots
                                        ).map(scale_factor), axis=0)

    n.madd('Generator', names = capacities.bus + ' ' + carrier,
                 bus=capacities.bus, carrier=carrier, 
                 p_nom = capacities,
                 p_max_pu = profile)

n.export_to_netcdf('vietnam.nc')




