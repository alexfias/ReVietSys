#!/usr/bin/python

#SBATCH --job-name=Vietnam
#SBATCH --partition=x-men
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 32
#SBATCH --mem=60000

import os

os.system('python' + ' ' + sys.argv[1])
