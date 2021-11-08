#!/bin/bash
#SBATCH --job-name=[python script name]
#SBATCH --output=slurm_output.[same as job name].%j
#SBATCH --time=00:10:00
#SBATCH --ntasks=4
#SBATCH --mem-per-cpu=1024

# This is an example of a script that could be called with sbatch to schedule
# A multithreaded python script. For a serial example, change "ntasks" to 1. 
# THIS IS NOT A FUNCTIONAL SCRIPT AS IS. MAKE SURE TO CHANGE THE FIRST TWO SBATCH LINES
# This script is suitable for running from your /work directory, and will use CPU resources.

logfile="slurm_output.test4."$SLURM_JOB_NAME"."$SLURM_JOB_ID
echo "TIME BEGAN: " >> $logfile
date >> $logfile
SECONDS=0

mpirun -n $SLURM_NTASKS python "python_scripts/"$SLURM_JOB_NAME".py"

echo "TIME COMPLETE: " >> $logfile
date >> $logfile

