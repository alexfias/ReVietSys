import pypsa
import numpy as np
import atlite
import vresutils.shapes as vshapes
from vresutils.graph import voronoi_partition_pts
import geopandas as gpd
import powerplantmatching as pm
import pandas as pd
from scipy.spatial import KDTree



n = pypsa.Network('original-model_original-data')
n.buses['substation_lv'] = True  # assume all buses are substations
n.lines['type'] = '490-AL1/64-ST1A 380.0'
n.mremove('Generator', n.generators.index)


# tranfer loads, fill NaNs in DongAnh with load values that are nearby
# its first entry
n.loads_t.p_set['DongAnh'] = n.loads_t.p_set['NghiSon']
# rescale loads (in MW) to approx value of
# https://www.worlddata.info/asia/vietnam/energy-consumption.php (in billion kWh)
n.loads_t.p_set = (n.loads_t.p_set / n.loads_t.p_set.sum().sum()
                   * (134.3 * 1e9) / 1e3)
loads = n.loads_t.p_set.fillna(0).copy()
n.set_snapshots(pd.DatetimeIndex(start='2015', end='2017',
                                 closed='left', freq='h'))
n.loads_t.p_set = (
    pd.concat([loads.rename(index=lambda ds:
                            ds - pd.Timedelta(270 - i * 52, 'W'))
              for i in [0, 1, 2]])
    [lambda df: ~ df.index.duplicated()].reindex(n.snapshots))

# add generators from pm
pm_config = pm.config.get_config(target_countries=['Vietnam'])
ppl = (pm.data.GPD(filter_other_dbs=False, config=pm_config)
       .replace({'Fueltype': {'Natural Gas': 'Ocgt'}}))
ppl.loc[ppl.Fueltype == 'Hydro', 'Set'] = 'Store'
pm.export.to_pypsa_network(ppl, n)
n.generators = n.generators.assign(p_nom_min=n.generators.p_nom,
                                   p_nom_extendable=True)


storages = pd.read_csv('storage_units.csv', index_col=0)
n.storage_units = (
    n.storage_units.assign(
        max_hours=storages.max_hours
        .reindex(n.storage_units.index).fillna(0),
        p_nom_min=n.storage_units.p_nom,
        p_nom_extendable=True,
        efficiency_storage=0.9))

# %% add artificial generators and storages
carriers = ['wind', 'solar', 'bioenergy', 'hard coal', 'oil', 'ocgt',
            'nuclear', 'perpetuum']
for carrier in carriers:
    not_included = (n.buses.index
                    .difference(n.generators[n.generators.carrier == carrier]
                                .set_index('bus').index))
    n.madd('Generator', names=not_included + ' ' + carrier,
           bus=not_included,
           carrier=carrier,
           p_nom_extendable=True)

params_su = pd.DataFrame({
    'max_hours': [6, 168, 0],
    'efficiency_dispatch': [0.9, 0.58, 0.9],
    'efficiency_storage': [0.9, 0.75, 0.9]},
    index=['battery', 'hydrogen', 'hydro'])

for st in params_su.index:
    not_included = ((n.buses.index).difference(
                    n.storage_units[n.storage_units.carrier == st]
                    .set_index('bus').index))
    n.madd('StorageUnit', names=not_included + ' ' + st,
           bus=not_included, carrier=st,
           max_hours=params_su.loc[st, 'max_hours'],
           efficiency_dispatch=params_su.loc[st, 'efficiency_dispatch'],
           efficiency_storage=params_su.loc[st, 'efficiency_storage'],
           p_nom_extendable=True)
n.storage_units.assign(p_nom_max=np.inf)

# %%
vietshape = vshapes.countries(subset=['VN'])['VN']
onshore_locs = n.buses.loc[:, ["x", "y"]]
regions = gpd.GeoDataFrame({
    'geometry': voronoi_partition_pts(onshore_locs.values, vietshape),
    'country': 'VN'}, index=onshore_locs.index).rename_axis('bus')
regions.crs = {'init': u'epsg:4326'}
regions['Area'] = (regions.geometry
                   .to_crs({'init': 'epsg:3395'})
                   .map(lambda p: p.area / 10**6))


# %% add cutout
cutout = atlite.Cutout("vietnam-2015-2016-era5",
                       module='era5',
                       bounds=[100, 6, 112, 25],
                       years=slice(2015, 2016, None))

cells = gpd.GeoDataFrame({'geometry': cutout.grid_cells()})
cells.crs = {'init': u'epsg:4326'}
cells['Area'] = (cells.geometry.to_crs({'init': 'epsg:3395'})
                 .map(lambda p: p.area / 10**6))

meta = (cutout.meta
        .drop(['height', 'time', 'year-month', 'lat', 'lon'])
        .to_dataframe().reset_index())

indicatormatrix = cutout.indicatormatrix(regions.geometry)

# %% add layouts


def custum_layout(meta, cap_per_sq_km):
    return (meta.assign(caps=cells.Area * cap_per_sq_km)
            .set_index(['x', 'y'])
            .fillna(0).to_xarray().transpose().caps)


# hydro
kdtree = KDTree(meta[['x', 'y']].values)
hydro = ppl[ppl.Fueltype.isin(['hydro'])]
hydro_grouped = (hydro.assign(
    cell=meta.index[kdtree.query(hydro[['lon', 'lat']].values)[1]])
    .groupby(['Fueltype', 'cell']).Capacity.sum())

# fill p_nom_max density for unbuilt capacities
# alternative could be 25% quantile of cell density
hydro_missing_cap = ((n.storage_units.groupby(['carrier', 'bus'])
                      .p_nom.sum()['hydro'] / regions.Area)
                     [lambda ds:ds != 0].min())

# expand upper bound for existing capacities by max 50%
hydro_layout = (pd.concat([meta, hydro_grouped.unstack(0)], axis=1)
                .set_index(['x', 'y']).mul(1.5)
                .fillna(hydro_missing_cap).to_xarray().transpose())

# %% calaculate profile via atlite

method = {'wind': 'wind', 'solar': 'pv', 'hydro': 'runoff'}

resource = {'wind': {'turbine': 'Vestas_V112_3MW',
                     'layout': custum_layout(meta, 10),
                     'per_unit': True, 'smooth': True},
            'solar': {'panel': 'CSi', 'orientation': 'latitude_optimal',
                      'layout': custum_layout(meta, 170),
                      'per_unit': True},
            'hydro': {'layout': custum_layout(meta, hydro_missing_cap),
                      'per_unit': False,
                      'smooth': True}}


for carrier in method.keys():
    print(carrier)

    func = getattr(cutout, method[carrier])
    profile, capacities = func(matrix=indicatormatrix, index=regions.index,
                               return_capacity=True, **resource[carrier])

    profile = (profile.to_pandas().T
               .rename(columns=lambda x: x + ' ' + carrier))
    capacities = (capacities.to_series()
                  .rename(index=lambda ds: ds + ' ' + carrier))

    if carrier == 'hydro':
        #        assume hydro generation statistics
        #        from https://www.hydropower.org/country-profiles/vietnam

        capacities = n.storage_units.p_nom_min.where(
            n.storage_units.p_nom_min > 0, capacities)
        inflow = profile * capacities
        # assume about 10% will be spillage
        inflow *= (120.0*1e6) / \
            inflow.sum().reindex((n.storage_units.p_nom_min > 0).index).sum()
        n.storage_units_t.inflow = inflow
        n.storage_units.p_nom_max = capacities * 1.5

    else:
        n.generators.loc[capacities.index, 'p_nom_max'] = capacities
        n.generators_t.p_max_pu = pd.concat(
            [n.generators_t.p_max_pu, profile], axis=1)


# only assumptions, no research done on this yet
n.carriers = pd.read_csv('costs.csv', index_col=0)
n.generators['marginal_cost'] = n.generators.carrier.map(n.carriers.marginal)
n.generators['capital_cost'] = n.generators.carrier.map(n.carriers.capital)
n.generators['weight'] = 1.0
n.storage_units['marginal_cost'] = n.storage_units.carrier.map(
    n.carriers.marginal)
n.storage_units['capital_cost'] = n.storage_units.carrier.map(
    n.carriers.capital)
n.lines.capital_cost = 0.4*n.lines.length  # Davids assumption


# Fix small values
n.generators_t.p_max_pu[n.generators_t.p_max_pu <= 1e-6] = 0.0

# Fix pandas 0.23.4 update change, where former 0.0s are now initialised with NaNs
n.storage_units_t.inflow = n.storage_units_t.inflow.fillna(0.0)

n.export_to_netcdf('vietnam3_storage.nc')


# Construct a network with critical lines removed
n = pypsa.Network('vietnam3_storage.nc')

n.lines = n.lines.drop(labels=['28', '29'])

n.export_to_netcdf('vietnam3_storage_disconnected.nc')
