#!/bin/bash
#SBATCH --job-name=GridSearch.FullMomentTensor.py
#SBATCH --output=slurm_output.GridSearch.FullMomentTensor.py.%j
#SBATCH --time=00:15:00
#SBATCH --mem-per-cpu=512
#SBATCH --ntasks=8

# Ran out of memory (default 512 MB per core and per cpu)
# If arises still, try --mem, which controls memory per core

logfile="slurm_output."$SLURM_JOB_NAME"."$SLURM_JOB_ID
echo "TIME BEGAN: " >> $logfile
date >> $logfile
SECONDS=0
mpirun -n $SLURM_NTASKS python $SLURM_JOB_NAME

echo "TIME COMPLETE: " >> $logfile
date >> $logfile

