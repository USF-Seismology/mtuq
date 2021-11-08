#!/bin/bash

# Source this file, either "source setup_mtuq_env.bash" or ". setup_mtuq_env.bash"
# To set up your environment for using MTUQ, including a lot of necessary persistent changes

# This block handles first time setup of a user's modulefiles directory
# This is necessary for custom modulefiles, like the one in /shares/seismo_lab/modulefiles/mtuq"
if [ ! -f ~/.bashrc ]; then
    echo "Creating a .bashrc file in your home directory."
    echo "# .bashrc" > ~/.bashrc
fi

if [ $( grep /etc/bashrc ~/.bashrc | wc -l ) -eq 0 ]; then
    echo "Adding global definitions to your .bashrc and reloading it now."
    # If these lines aren't in your bashrc, then module won't work.
    echo "#Source global definitions" >> ~/.bashrc
    echo "if [ -f /etc/bashrc ]; then" >> ~/.bashrc
    echo "    . /etc/bashrc" >> ~/.bashrc
    echo "fi" >> ~/.bashrc
    . ~/.bashrc
fi

if [ ! -d ~/.modulefiles ]; then
    echo "Creating hidden .modulefiles directory in home directory."
    mkdir ~/.modulefiles
    echo "Adding ~/.modulefiles to your \$MODULEPATH with 'module use -a ~/.modulefiles'"
    module use -a ~/.modulefiles
fi

if [ ! -d ~/.modulefiles/mtuq ]; then
    echo "Copying mtuq modulefile to home directory"
    mkdir ~/.modulefiles/mtuq
    cp /shares/seismo_lab/modulefiles/mtuq ~/.modulefiles/mtuq/mtuq
    
fi

# This is a necessary step for getting set up to use conda
if [ $( grep conda ~/.bashrc | wc -l ) -eq 0 ]; then
    echo "Initializing conda for the first time (with bash). Check .bashrc to see the changes."
    module purge
    /shares/seismo_lab/miniconda3/bin/conda init bash
    . ~/.bashrc # Sourcing bashrc with . /env/bashrc line will re-load default modules, an unwanted side effect
    # So we load mtuq module afterwards
fi

echo "Loading mtuq module with 'module load mtuq'"
echo "If you already have mtuq loaded, this may give an error message which can be safely ignored."
module load mtuq 

echo "Activating Miniconda3 environment for MTUQ with 'conda activate $MTUQENV'"
conda activate $MTUQENV

# This block should run only on your first time
# It creates a user directory based on your username, to keep your scripts and outputs separate from other users
# It also copies /examples into your directory, and puts example1 into the scheduler queue for you. 
if [ ! -d ./$USER ]; then
    echo "Creating user directory at ./"$USER
    mkdir $USER
    cp -r examples $USER/examples
    echo "Running first example with 'sbatch $USER/examples/example1.sh'"
    echo "Run command 'squeue -u $USER' to see your queue"
    cd $USER/examples
    sbatch example1.sh
    echo "Use command 'scancel [job number]' if you want to cancel a job"
fi
