#!/bin/bash
#SBATCH --job-name=SerialGridSearch.DoubleCouple
#SBATCH --output=slurm_output.SerialGridSearch.DoubleCouple.%j
#SBATCH --time=00:15:00

logfile="slurm_output."$SLURM_JOB_NAME"."$SLURM_JOB_ID
echo "TIME BEGAN: " >> $logfile
date >> $logfile
SECONDS=0
python $SLURM_JOB_NAME".py"

echo "TIME COMPLETE: " >> $logfile
date >> $logfile

