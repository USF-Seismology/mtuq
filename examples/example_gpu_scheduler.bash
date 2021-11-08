#!/bin/bash
#SBATCH --job-name=[python script name]
#SBATCH --output=slurm_output.[same as job name].%j
#SBATCH --time=00:10:00
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1
#SBATCH --mem-per-gpu=1024
#SBATCH --partition=snsm_itn19
#SBATCH --qos=openaccess
#SBATCH --gres=gpu:1

# This is an example of a script that could be called with sbatch to schedule
# A multithreaded python script. For a serial example, change "nodes" to 1. 
# THIS IS NOT A FUNCTIONAL SCRIPT AS IS. MAKE SURE TO CHANGE THE FIRST TWO SBATCH LINES
# This script is set up to use a GPU partition, and so must be run from your /work_bgfs directory. 

module purge
module load mtuq
conda activate $MTUQENV

logfile="slurm_output.test4."$SLURM_JOB_NAME"."$SLURM_JOB_ID
echo "TIME BEGAN: " >> $logfile
date >> $logfile
SECONDS=0

mpirun -n $SLURM_NTASKS python "python_scripts/"$SLURM_JOB_NAME".py"

echo "TIME COMPLETE: " >> $logfile
date >> $logfile

