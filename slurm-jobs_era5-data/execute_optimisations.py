import os

files=os.listdir('./')
files.sort()
files.remove('execute_optimisations.py')
files.remove('slurm_batches.py')
files.remove('build_scenarios.py')
for f in files:
    print('Call "' + 'sbatch' + ' ' + 'slurm_batches.py' + ' ' + f + '"')
    os.system('sbatch' + ' ' + 'slurm_batches.py' + ' ' + f)
