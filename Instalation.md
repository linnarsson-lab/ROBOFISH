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
- Create a new environment: `conda create --name <NAME> pyton=3.7`
- Activate the environment: `source activate <NAME>`
  
### Install the dependencies
- Install the python dependencies: `conda install numpy pyyaml pyserial`
- Install the python dependencies: `pip install ruamel.yaml pushbullet.py` (these are not available on conda)




# WINDOWS
# Environment setup
### Install Anaconda
- Download the Anaconda installation .exe file for windows from https://www.anaconda.com/distribution/
- Run the installation setup

### Make an environment
- Open the Anaconda Prompt (found under Windows start)
- Create a new environment: `conda create --name <NAME> pyton=3.7`
- Activate the environment: `activate <NAME>`

### Install the dependencies
- Install the python dependencies: `conda install numpy pyyaml pyserial`
- Install the python dependencies: `pip install ruamel.yaml pushbullet.py` (these are not available on conda)
- Install Jupyter Lab: conda install `-c conda-forge jupyterlab`
- Install Notepadd++ from: https://notepad-plus-plus.org

# ROBOFISH setup
### Get source
- Clone or download this repository (is this correct??)


I set up the system first as it is on the other computer. Afterwards, make the updates to make it nice and then upload everything here.
- Choose temperature controller
- COM ports in the datafile
- ports with numbers and not names
- extra dictionary which says which buffers are in which port for the logging
- make pushbullet dictionary in datafile


### Start user program
The user program is the main interface for the user to give expermental parameters to the system.  
With the user program you can open a text file (FISH2_System_datafile.yaml) that contains all metadata of the system and the experiments. This data is uploaded to a central database that the system can acces to perform the correct experiment.
- Open the FISH_System_datafile_template.yaml
- Edit the data if needed and save as FISH_System_datafile.yaml. This is the main entry point for data (eperimental parameters, settings, etc.) for the user. For now it is not needed to change any data.
- Start a new Anaconda Prompt and activate your environment using: `activate <NAME>`
- Change directory to the folder with the ROBOFISH code: `cd <PATH>` for instance if it is on your desktop: `cd Desktop\ROBOFISH`
- Start the user program with: `python FISH2_user_program.py` (CHANGE TO ROBOFISH)
- A database will be created and the datafile will open.
- Edid the data if needed and close.
- Hit enter if all data is updated and Notepad++ is closed
- A dialoage will open asking if any of the buffers need to be primed which is not needed at this point. Close to continue.
- The information will now be uploaded to the central database.

### Run system
The system is run using a jupyter lab notebook. In this notebook you will find some standard high level functions to perform an experiment on the ROBOFISH system. Furthermore, you can make your own functions and put them in the scheduler function that executes the experiment.
- Open a second Anaconda Prompt and activate your environment with: `activate <NAME>`.
- Change directory to the ROBOFISH folder: `cd <PATH>`.
- Start Jupyter Lab by running: `jupyter lab`, it will open in your browser.
- Run the ROBOFISH_program by clicking `ROBOFISH_program.ipynb`.

### Find communication ports for all devices
Next you need to find the communication ports with which the computer can communicate with the devices. The FISH2_functions, contains a convienicence function `find_address()` that helps you find the ports. There are two ways to tell the system how to communicate with the devices, either through a unique machine identifier or by giving the identifier of the USB port teh machine is connected to. It is advised to use the unique machine identifier method, because this will still work if you swich around the USB cabels. While the other method asigns a specific USB port and thus will not work when you change the cabels. Many USB controlled machines contain an FTDI chip that converts the signal comming from the USB port to serial. These chips store a number of atributes that can be used to identify the machine, for instance FTDI unique identifier, or machine company name. If you happen to know one of these attribute you can try to use that to identify the device. Otherwise, the `find_address()` function guides you through the process of finding the machine identifier and port by unplugging and plugging the USB cable. For the USB adresses; On windows these ports are called "COMX" where X is the number of the port. In linux they are labeled '/dev/ttyUSBX' where X is the number of the port. For both methods, the identification numbers or ports need to be added to the FISH_System_datafile so that the system can connect to the devices. 
- Make sure all machines are connected and ON.
- In the user program open the datafile by typing `all`, this will open the System_datafile in Notepad++.
- In the Jypyter lab import the FISH2_functions: `import FISH2_functions`.
- Call the find_address function: `FISH2_functions.find_address(identifier=None)`.
- If you know the identifier of the machine give it to the function as string: `FISH2_functions.find_address(identifier='XYZ123')`.
- Follow the instruction of the `find_address()` function.
- Once you have the identifier and USB port, fill it in in the FISH_System_datafile. Either fill in the unique machine identifire in the Machine_identification table, or fill in the USB port in the Fixed_USB_port table. Preferentially use the Machine_identification method. Different strategies can be used for different machines. Make sure there is a space between name and the value in the FISH_System_datafile, like: MXValve1: XYZ123.
- In the Machines table, put a 1 for each machine that is connected.
- Save and close the Notepad. In the user program hit enter to save the data and click away the prime port popup.

### Initiate the system
The next cell in the Jupyter lab notebook will contain the functions to initiate the system. First make sure all paths in this cell are correct.
- Make sure the path to the database is correct. In your ROBOFISH folder a new folder should have been made called `FISH_database` containing the database: `FISH_System2_db.sqlite`. Add the path to this file in the Jupyter lab (Windows: right click, properties, Location). 
- For the first run you can ignore the `start_imaging_file_path` and the `imaging_output folder`. Below are the explanations if you wan to set them up.
  - The `start_imaging_file` is a file that the system uses to communicate with the Nikon software to automatically start the imaging once a staining is done. It is present in this repository. Find the 'start_imaging_file.txt', and put the path to this file in the program. (The `start_imaging_file.txt` is a text file with a single number in it. If you make it from scratch put a 0. 0 means no sample to image. 1 means start imaging of the sample or sample number 1. Or another number if there are multiple samples.)
  - For the 'imaging_output_folder' specifiy the path were the images will be saved. The program will make a log file containing all details of that imaging round and experiment to the specified folder. It is a pickeled python dictionary that can be opened with: `pickle.load(open('<path to file>', 'rb)`

- Make sure the recevoir is on the right side of the pump.

