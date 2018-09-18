import os

files=os.listdir('./')
files.sort()
files.remove('execute_optimisations.py')
files.remove('slurm_batches.py')
for f in files:
    print('Call "' + 'sbatch' + ' ' + 'slurm_batches.py' + ' ' + f + '"')
    os.system('sbatch' + ' ' + 'slurm_batches.py' + ' ' + f)
