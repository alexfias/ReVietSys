import pypsa
data_folder = "./data_vietnam/"
network = pypsa.Network(import_name=data_folder)
time_steps = 876

network.lines.capital_cost = network.lines.length*400./time_steps
network.generators.capital_cost = network.generators.capital_cost/time_steps

#rescale loads to ca. 600 billion kWh
network.loads_t.p_set = network.loads_t.p_set*2.23



def my_extra_functionality(network,snapshots): 
	from pyomo.core.base.expr import identify_variables

	pv_limit = 12000.
	wind_limit = 6000.
	coal_limit = 55300.
	ocgt_limit = 19000.
	oil_limit = 1000.

	gen_solar = network.generators[network.generators['carrier']=='solar'].index
	gen_wind = network.generators[network.generators['carrier']=='windon'].index
	gen_coal = network.generators[network.generators['carrier']=='coal'].index
	gen_ocgt = network.generators[network.generators['carrier']=='OCGT'].index
	gen_oil = network.generators[network.generators['carrier']=='oil'].index

	flexibility = 0.1 

    	network.model.pv_limit_low = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_solar) >= pv_limit * (1.-flexibility))
	network.model.pv_limit_up = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_solar) <= pv_limit * (1.+flexibility))
    	network.model.wind_limit_low = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_wind) >= wind_limit * (1.-flexibility))
	network.model.wind_limit_up = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_wind) <= wind_limit * (1.+flexibility))
    	network.model.coal_limit_low = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_coal) >= coal_limit * (1.-flexibility))
	network.model.coal_limit_up = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_coal) <= coal_limit * (1.+flexibility))
    	network.model.ocgt_limit_low = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_ocgt) >= ocgt_limit * (1.-flexibility))
	network.model.ocgt_limit_up = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_ocgt) <= ocgt_limit * (1.+flexibility))
    	network.model.pv_oil_up = pypsa.opt.Constraint(expr=sum(network.model.generator_p_nom[name] for name in gen_oil) <= oil_limit)




extra_funct = 1
if extra_funct == 1:
	network.lopf(extra_functionality=my_extra_functionality, snapshots=network.snapshots[0:8760:time_steps], solver_name='gurobi')
else:
	network.lopf(snapshots=network.snapshots[0:8760:time_steps], solver_name='gurobi')

network.generators.to_csv('./results/generators.csv')
network.lines.to_csv('./results/lines.csv')
