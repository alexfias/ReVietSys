#!/usr/bin/python3

import os
import time as t

files=os.listdir('./')
files.sort()
files.remove('execute_optimisations.py')
files.remove('slurm_batches.py')
files.remove('build_scenarios.py')

#counter = 0

for f in files:
    #counter += 1
    #if (counter == 3) or (counter == 5) or (counter == 7) or (counter == 9) or (counter == 11): t.sleep(172800) # two days idle

    job_name = '--job-name='+f
    partition = '--partition=vres'
    nodes = '--nodes=1'
    ntasks = '--ntasks=1'
    cpus = '--cpus-per-task=20'
    memory = '--mem=100000'
    output = '--output='+f[:-3]+'.out'
    time = '--time=10-00:00:00'

    print('Call "' +
          'sbatch' + ' ' + job_name + ' ' + partition + ' ' +
                           nodes + ' ' +
                           ntasks + ' ' + cpus + ' ' + memory + ' ' + output + ' ' + time + ' ' +
          'slurm_batches.py' + ' ' + f + '"')

    os.system('sbatch' + ' ' + job_name + ' ' + partition + ' ' +
                               nodes + ' ' +
                               ntasks + ' ' + cpus + ' ' + memory + ' ' + output + ' ' + time + ' ' +
              'slurm_batches.py' + ' ' + f)

