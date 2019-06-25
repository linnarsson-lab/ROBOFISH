# Environment setup
### Install Ubuntu terminal
- Go to: Control Panel - Programs - Turn Windows Features On Or Off
- Enable "Windows Subsyustem for Linux" and click OK
- Restart computer
- Go to: Microsoft Store and seach for Ubuntu
- Install the Ubuntu terminal
- Open the terminal and pin the Ubuntu terminal to the taskbar for convenience
  
### Install Anaconda
- Install Anaconda by: sudo wget https://repo.continuum.io/archive/ <VERSION>
- In my case: sudo wget https://repo.continuum.io/archive/Anaconda3-2019.03-Linux-x86_64.sh
- Install by: sudo bash Anaconda <VERSION>
- In my case: sudo bash Anaconda3-2019.03-Linux-x86_64.sh
  
### Make an environment
- In the Ubuntu terminal
- Create a new environment: conda create --name <NAME> pyton=3.7
- Activate the environment: source activate <NAME>
  
### Install the dependencies
- Install the python dependencies: conda install numpy pyyaml pyserial
- Install the python dependencies: pip install ruamel.yaml pushbullet.py (these are not available on conda)




# WINDOWS
# Environment setup
### Install Anaconda
- Download the Anaconda installation .exe file for windows from https://www.anaconda.com/distribution/
- Run the installation setup

### Make an environment
- Open the Anaconda Prompt (found under Windows start)
- Create a new environment: conda create --name <NAME> pyton=3.7
- Activate the environment: activate <NAME>

### Install the dependencies
- Install the python dependencies: conda install numpy pyyaml pyserial
- Install the python dependencies: pip install ruamel.yaml pushbullet.py (these are not available on conda)
- install Jupyter Lab: conda install -c conda-forge jupyterlab

# ROBOFISH setup
### Get source
- Clone or download this repository (is this correct??)


