# WINDOWS 

# Environment setup 

### Install Anaconda 

- Download the Anaconda installation .exe file for windows from https://www.anaconda.com/distribution/ 

- Run the installation setup 

  

### Make an environment 

- Open the Anaconda Prompt (found under Windows start) 

- Create a new environment: `conda create --name <NAME> python=3.7` Where `<NAME>` is a name of your choosing, for instance `py3` 

- Activate the environment: `activate <NAME>` 

  

### Install the dependencies 

- Install the python dependencies: `conda install numpy pyyaml pyserial colorama` 

- Install the python dependencies: `pip install ruamel.yaml pushbullet.py` (these are not available on conda) 

- Install Jupyter Lab: `conda install -c conda-forge jupyterlab` 

- Add the environment to Jupyter Lab: `python -m ipykernel install --user --name <NAME> --display-name '<NAME>'` 

- Install Notepadd++ from: https://notepad-plus-plus.org 

  

# ROBOFISH setup 

### Get source 

- Clone or download this repository. 

  

# Machine configuration 

Depending on your configuration of the ROBOFISH system download the files of the following devices and place them in the ROBOFISH folder: 

- [ThermoCube](https://github.com/linnarsson-lab/ThermoCube) recirculating chiller. 

- [Oasis](https://github.com/linnarsson-lab/Oasis_chiller) recirculating chiller. 

- [TC-720](https://github.com/linnarsson-lab/Py_TC-720) temperature controller. 

- [Tecan syringe pump (Original repository)](https://github.com/benpruitt/tecancavro) or [Tecan syringe pump (Forked repository with code for XCalibur with or without distribution valve and XE1000)](https://github.com/linnarsson-lab/tecancavro). (At the time of publishing the original repository has not been merged to support all models, so use the second link. However, we want to acknowledge the original authors.) 

  

### Start user program 

The user program is the main interface for the user to give experimental parameters to the system.   

With the user program you can open a text file (FISH2_System_datafile.yaml) that contains all metadata of the system and the experiments. This data is uploaded to a central database that the system can access to perform the correct experiment. 

- Start a new Anaconda Prompt and activate your environment using: `activate <NAME>` 

- Change directory to the folder with the ROBOFISH code: `cd <PATH>` for instance if it is on your desktop: `cd Desktop\ROBOFISH` 

- Start the user program with: `python FISH2_user_program.py` 

- A database will be created and the datafile will open. 

- You do not need to change anything at this point so close the window.  

- In the Anaconda prompt running the user program, hit enter. 

- A dialogue will open asking if any of the buffers need to be primed which is not needed at this point. Close to continue. 

- The information will now be uploaded to the central database. 

- Afterwards, the user program will return to its default state, which gives the user the option to update the experimental parameters or pause the experiment. 

  

### Run system 

The system is controlled using a Jupyter Lab notebook. In this notebook you will find some standard high level functions to perform an experiment on the ROBOFISH system. Furthermore, you can make your own functions and put them in the scheduler function that executes the experiment. 

- Open a second Anaconda Prompt and activate your environment with: `activate <NAME>`. 

- Change directory to the ROBOFISH folder: `cd <PATH>`. 

- Start Jupyter Lab by running: `jupyter lab`, it will open in your web browser. 

- Copy the [ROBOFISH_custom_functions.ipynb](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Example_notebooks/ROBOFISH_custom_functions.ipynb) file from the `Example_notebooks` folder to the parent ROBOFISH folder.

- Run the ROBOFISH_program by clicking `ROBOFISH_custom_functions.ipynb`. 

- Make sure the correct kernel is selected. Under `Kernel` click: `Change kernel...` and select the name of the environment.  

  

### Find communication ports for all devices 

Next you need to find the communication ports with which the computer can communicate with the devices. The FISH2_functions, contains a convenience function `find_address()` that helps you find the ports.   

There are two ways to tell the system how to communicate with the devices, either through a unique machine identifier or by giving the identifier of the USB port the machine is connected to. It is advised to use the unique machine identifier method, because this will still work if you switch around the USB cables. While the other method assigns a specific USB port and thus will not work when you change the cables. Many USB controlled machines contain an FTDI chip that converts the signal coming from the USB port to serial. These chips store a number of attributes that can be used to identify the machine, for instance FTDI unique identifier, or machine company name. If you happen to know one of these attribute you can try to use that to identify the device. Otherwise, the `find_address()` function guides you through the process of finding the machine identifier and port by unplugging and plugging in the USB cable. For the USB addresses; On windows these ports are called "COMX" where X is the number of the port. In Linux they are labeled '/dev/ttyUSBX' where X is the number of the port. For both methods, the identification numbers or ports need to be added to the FISH_System_datafile so that the system can connect to the devices.  

- Make sure all machines are connected and ON. 

- In the user program open the datafile by typing `all`, this will open the System_datafile in Notepad++. 

- In the Jypyter Lab import the FISH2_functions: `import FISH2_functions`. 

- Call the find_address function: `FISH2_functions.find_address(identifier=None)`. 

- If you know the identifier of the machine give it to the function as string: `FISH2_functions.find_address(identifier='XYZ123')`. 

- Follow the instruction of the `find_address()` function. 

- Once you have the identifier and USB port, fill it in in the FISH_System_datafile. Either fill in the unique machine identifier in the Machine_identification table, or fill in the USB port in the Fixed_USB_port table. Preferentially use the Machine_identification method. Different strategies can be used for different machines. Make sure there is a space between name and the value in the FISH_System_datafile, like: MXValve1: XYZ123. 

- In the Ports table add the port numbers the buffers are connected to. The port numbers are written on the multi valve front. The valve connected to the reservoir and syringe-pump is called `MXValve1` and its ports are numbered 1 through 10. The other valve which has its central port connected to `MXValve1` is called MXValve2 and its ports are numbered 11 through 20 in the program.  

- In the Machines table, put a 1 for each machine that is connected. 

- Save and close the Notepad. In the user program hit enter to save the data and close the prime port popup. 

  

### Yoctopuce Thermistor 

If you are using the FCS2 flow cell you need to connect the Yoctopuce Thermistor temperature sensor to measure the room temperature and chamber temperature. 

To set it up follow these steps: 

- Connect one of the supplied Thermistors to port 1. 

- Connect the FCS2 thermistor to the Yoctopuce Thermistor with an electrical wire and two pins. Use the middle two slots on the FCS2. 

- Connect the Yoctopuce Thermistor with a USB to USB micro cable to the computer. The lights should turn on now. 

- From the Yoctopuce website download the Python [libraries](https://www.yoctopuce.com/EN/libraries.php). 

- Copy the following files to the main ROBOFISH folder" 
  - yocto_api.py
  - yocto_temperature.py
  - The entire `cdll` folder 

- Download the Virtual hub software from [here](https://www.yoctopuce.com/EN/virtualhub.php) and install it with [these instructions](https://www.yoctopuce.com/projects/VirtualHub/VIRTHUB0.usermanual-EN.pdf) 

- Go to the web page of the Thermistor [http://127.0.0.1:4444/](http://127.0.0.1:4444/) 

- Here you can configure the individual temperature sensors by putting in the specifications. Please refer to the manual for guidance. For the FCS2 use the thermistor specifications you got from Bioptechs.  

- Save the settings and then make sure the temperature readings are correct (double click on the Thermistor name in the main menu). If all works close the website and the Virtual hub program. 

  

### Pushbullet communication 

The system communicates with the user with push messages through the program Pushbullet. The system will update you about the status of the experiment and will let you know if any of the buffers are running low. Furthermore, it will sound the alarm is something is wrong. You will need an account at Pushbullet to use this functionality. It is recommended to get a paid account. The free account only allows an X amount of messages to be sent. In normal operation this should be enough but in case there is something wrong the ROBOFISH system can send a lot of messages to alarm the user, maxing out the quota, so that you will not receive any messages.  

- Go to the website of [Pushbullet](https://www.pushbullet.com/).  

- Make an account. 

- Go to settings and create and access token. This will be your address. 

- Install the Pushbullet [app](https://www.pushbullet.com/apps) on your [phone](https://play.google.com/store/apps/details?id=com.pushbullet.android&referrer=utm_source%3Dpushbullet.com) (android only), web browser or Windows. 

- In the user program open the datafile by typing `part`. 

- In the Operator_address table add your Pushbullet token after one of the `OperatorX` slots. When you are using the program you will need to use your `OperatorX` identifier as your name. You can add up to 10 operators. 

- Save and close the datafile, hit enter in the user program. 

- In the popup window indicate that you updated the Operator_address. In this section you used the `part` updating method. This is a bit quicker than using `all` but there is a risk that you forget to click the tickboxes so that the data is not uploaded to the machine.  

  

### Configuring ports 

In the user program select `all`. Go to the ports table and fill in the names of the buffers that are, or will be, connected. If you do not know that at this point, it is no problem just leave it empty. However, you need to define the port connected to the `Waste` and `Valve2`. Valve1 is the valve that has its central port connected to the reservoir at its port are called P1 to P10. On the valve you will find numbers to figure our which port is which number. Valve2 has its middle port connected to Valve1 and its ports are called P11 to P20 in the program.  

- Fill in which port is connected to `Waste` and `Valve2`. 

- Fill in the names of the connected buffers and the name of the RunningBuffer. For instance, in our case the RunningBuffer is SSC 2X so we fill in `RunningBuffer: SSC2X`. 

- To connect flow-cells add the names `Chamber1` and if applicable `Chamber2` to the ports. 

- To connect hybridization mixes the names should have the format `HYBXX` where `XX` is the number.    

Continue with the next part. 

  

### Configuring Volumes 

For the buffer names you just added, fill in the volume of the connected buffer in microliter at the corresponding port. For instance, if you have connected 100ml of Running buffer, enter 100000 after Running buffer. Or if the waste bottle is empty, enter 0 after the port connected to the waste.   

Continue with the next part. 

  

### Configuring alarm volumes. 

Scroll down in the info file until you found the Alert_volumes table. This table contains volumes below or above which the system will warn the user. For instance ,if the waste container is full, meaning it is above the given alter volume, it will send a message to the user. Or if one of the buffers is running low it will send an alarm. Additionally, it checks if there is enough disk space. For now, just add a volume for the connected buffers at 10% of the containers volume. Or at 90% of the waste container volume. Later you can fine-tune these numbers depending on your protocol.   

  

### Configuring connected machines. 

In the machines table add a `1` for machines that are connected or a `0` for machines that are not connected.  

   

Save and close the Notepad. In the user program hit enter to save the data and close the prime port popup. 

  

### Initiate the system 

The next cell in the Jupyter lab notebook will contain the functions to initiate the system. First make sure all paths in this cell are correct. 

- Make sure the path to the database is correct. In your ROBOFISH folder a new folder should have been made called `FISH_database` containing the database: `FISH_System2_db.sqlite`. Add the path to this file in the Jupyter lab (Windows: right click, properties, Location).  

- For the first run you can ignore the `start_imaging_file_path` and the `imaging_output folder`. Below are the explanations if you want to set them up. 

  - The `start_imaging_file` is a file that the system uses to communicate with the Nikon software to automatically start the imaging once a staining is done. It is present in this repository. Find the 'start_imaging_file.txt', and put the path to this file in the program. (The `start_imaging_file.txt` is a text file with a single number in it. If you make it from scratch put a `0`. `0` means no sample to image. `1` means start imaging of Chamber1, `2` means start imaging of Chamber2.) 

  - For the `imaging_output_folder` specify the path where the images will be saved. The program will make a log file containing all details of that imaging round and experiment to the specified folder. It is a pickeled python dictionary that can be opened with: `pickle.load(open('<path to file>', 'rb)` 

  
- The pump needs to know which side is the input port and which is the output port. At the moment this is hardcoded and needs to be changed manually. In the ROBOFISH folder open the `FISH2_functions.py` file, change it and save: 

  - For the Tecan Cavro XE1000 pump: In line 348 you can change the input port. The input port is the port that is connected to the RunningBuffer. If the Running buffer is connected left and the reservoir right, set the `'in_port'` equal to `'lef'`, like: `self.pump.init(in_port='left', init_speed = 20)` If your ports are mirrored  set `in_port` equal to `'right'`.   

  - For the Tecan Cavro XCalibur pump: In line 372 set direction equal to `'Z'` if the RunningBuffer is connected to the left port and the reservoir to the the right, like: `direction='Z'`. If your ports are mirrored set `direction` equal to `'Y'`. 

     
- Now initiate the system by calling: `F2 = FISH2_functions.FISH2(db_path, imaging_output_folder, start_imaging_file_path, system_name='ROBOFISH')` 

- To run a notebook it needs to be in the main ROBOFISH folder. Thus, to use the provided template notebooks described in the next points they need to be moved to the parent folder.

- In the [ROBOFISH_custom_functions.ipynb](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Example_notebooks/ROBOFISH_custom_functions.ipynb) file you will find examples and explanation of the basic and advanced functions of ROBOFISH so that you can program you own protocols.  

-  In the [EEL.ipynb](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Example_notebooks/EEL.ipynb) file you will find the full protocol to run EEL experiments.   

- For running serial smFISH experiments like osmFISH use the [osmFISH.ipynb](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Example_notebooks/osmFISH.ipynb) notebook. 

- If something goes wrong and you want to restart the initiation, you need to restart the kernel of the notebook (Kernel --> Restart kernel). This is because the COM ports will be dedicated already and cannot be reassigned by the same python kernel.  

  

### Prime the system 

The reservoir needs to be filled with RunningBuffer for proper operation. There is a convenience function that guides you through all steps of the priming. Fill the RunningBuffer bottle with your buffer or water and then call the function with: `F2.primeSystem(system_dry = True)`. Prime all connected buffers by following the steps. 

  

### Find padding volumes 

The system needs to know the dead volumes between the valves, buffers and flow cell(s) to accurately dispense the liquids to a specific location. Dead volumes are called Padding volume and there are 3 different functions for helping you to find the correct volumes: `F2.findPaddingVolumeChamber()` for finding the padding volume between Valve1 and the flow cell. `F2.findPaddingVolumeHYBmix()` For finding the dead volume between Valve1 and the hybridization mixes. And `F2.findPaddingVolumeBuffer()` for finding the padding volume between Valve1 and a connected buffer container.   

For the hybridization mixes and buffers these functions just aspirate a user defined volume and the user needs to see if the liquid reaches the reservoir, and the function guides the user through this process. It is best if the liquid just enters it. To accurately determine the dead volume it is advised to use a test liquid with matching viscosity to the actual liquid that is going to be used.   

For the flow cells and degasser, an air bubble is dispensed and the user needs to see if this air bubble just reaches its destination. For this to work properly remove the bubble trap and connected the tubbing with an IDEX P710 (or similar) connector. Additionally switch off the degasser. Afterwards, add the known dead volume of the bubble trap to the padding volume.   

These functions need also one `air_port` this is a port that is not connected to anything so that the machine can aspirate air. Give it the port ID like: 'P3' for port 3.   

For every port that is connected to something (Excluding Valve2 and Waste) start the respective function and fill in the found padding volume in the Padding table of te FISH_system_datafile through the user program.  

  

# Operation 

  

Starting a new experiment should start with filling in the experimental info into the datafile using the user program. Below the various parts are explained if they have not yet been described above. Additionally, the datafile has many comments that help the user to format the data. 

  

## Configuring the datafile and priming of ports 

Open the file by entering `all` in the FISH2_user_program. When all data has been changed, safe the file and close. You will now see a popup that asks you if you want to prime any buffers. Even though all ports are listed you should only prime buffers that you connect. So do not prime: Flow cells, RunningBuffer, Waste port or hybridization mixes! If you for instance have connected a new aliquot of imaging buffer, click the box of the port number it is connected to. The ROBOFISH system will not immediately prime it, but it will do it before it executes its next operation. 

  

### Configure experimental parameters 

In the `Parameters` table you will find space to fill in various parameters and metadata variables for the experiment. Below is a highlight of a couple of the most important parameters. Up to two flow cells are supported and the parameters for a respective flow cell are followed by and `_1` for Chamber1 or `_2` for Chamber2. 

- Operator: This is used to send messages to the user and should match the items in `Operator_address` for instance; `operator3`. 

- EXP_name_X: For an experiment to get started by the ROBOFISH system it needs to have an experiment name. 

- There are various parameters that are needed to determine steps of the image analysis pipeline. See the options in the comments of the datafile and the image analysis documentation. 

- `Hybmix_volume`: This is the volume used for hybridization. It also determines how much of the other buffers need to be dispensed to the flow cell and is synonymous for the flow cell internal volume. It is advisable to have this volume slightly larger than the actual volume of the flow cell and when hybridization mixes are loaded into the system to put a little bit more in the eppendorf tube to prevent air bubbles.  

- There are multiple temperature values for various parts of the protocol. In the ROBOFISH program these will later be accessible from the F2.Parameters dictionary.  

  

### Configure volumes 

As discussed above, in the `Volumes` table the actual buffer volumes are tracked. When placing a new buffer in the system enter its volume here in microliter. When the datafile is opened through the user program the volumes will be updated to the actual current values.  

  

### Configure Hybridization mixes 

In the `Hybmix` table you can tell the system to which ports a certain hybridization mix is connected. The names of the hybridization mixes should be of the format `<chamber>_<cycle>`. For instance, if you put the hybridization mix with probes for the first round of Chamber1 in the slot connected to port 1, you enter `C1_01` after P1. Or for Chamber2 cycle 12 use the code `C2_12`.   

For more advanced hybridization schemes where first one or two amplifier probes are hybridized you can use the addition of `_A`,  `_B` or `_C` for up to 3 hybridizations in the same cycle.  

  

### Configure targets 

In the `Targets` table you can fill in the target that is imaged in a certain channel in a certain cycle. For each Chamber there is a list of 20 hybridization rounds with all the channels listed. After the channel write the target that is imaged in that channel in that cycle. For instance, if you stained for Actin in the FITC channel in cycle 1, enter Actb after FITC in the Hybridization01 table. You can also enter a barcode bit number, Nuclei, PolyA, or beads. 

  

## Configure the scheduler 

Once the parameters are all filled in you can start the experiment. You do this by defining two functions and giving this to the scheduler. The first function should perform the first cycle of the experiment. The second function is a function that is repeated for all other cycles. Please see the  [ROBOFISH_custom_functions.ipynb](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Example_notebooks/ROBOFISH_custom_functions.ipynb) for an introduction on how to program your own protocol and execute it with the scheduler. Or run the EEL experiment by using the [EEL.ipynb](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Example_notebooks/EEL.ipynb) file.  

  

# Imaging with Nikon NIS Elements 

  

### Install job 

Open the NIS Elements JOBS explorer and import the [Nikon_imaging_job_template.bin](https://github.com/linnarsson-lab/ROBOFISH/blob/master/Nikon_imaging_job_template.bin) imaging job file. 

  

### Set up color channels 

The ROBOFISH system has a predefined set of fluorescent channel names that should be used. These names need to be standardized because the metadata file links the labeled gene or barcode bit to the actual image using this name.   

The allowed names are: `DAPI`, `Atto425`, `Europium`, `FITC`, `Cy3`, `TxRed`, `Cy5`, `Cy7`, `QDot` and `Brightfield`   

In the Nikon NIS Elemens software call the optical configurations with these names.  

   

Unfortunately, these names cannot be changed easily, but it is possible. If you want this follow the below steps: 

- In the `FISH2_peripherals.py` file you will have to replace all instances of one of the above names with the new name.  

- Do the same for the `FISH2_functions.py` file. 

- And also for the `FISH_System_datafile.yaml` and `FISH_System_datafile_template.yaml` files. 

- Then delete the `FISH2_System2_db.sqlite` file from the `ROBOFISH\FISH_database` folder. 

- Afterwards, Restart the ROBOFISH user program by calling `python FISH2_user_program.py`. This will recreate the database with the new names. 

- Make sure Nikon Nis Elements has the new name as name for the Optical Configuration.  

  

# Windows 

  

### Enable info file renaming   

The ROBOFISH program makes an info file for every round of labeling, which contains all metadata for that round and puts it in the folder with all the images. The info file contains the Targets given by the user which couples image color channel with the target gene or target barcoding bit name.   

To match this round info file with a certain image, the Imaging job renames the info file to match the file name of the image. The images get a "CountXXXXX" number by the imaging Job, and the imaging Job renames the info file with same "CountXXXX" number. To do this Nis Elements needs to run the `Rename_info_file.py` script. The following steps make Python installed by Anaconda available for the entire system. Skip these steps if python is already available; test this by running `python` in a Windows Command Prompt (Not the Anaconda prompt). If this gives you a Python interpreter, you should be set. If not follow the next steps: 

- In the Anaconda prompt enter `where python`. Copy the path without the `\python.exe`. 

- In Windows search enter `Environment variables` and open the `Edit the system environment variables` 

- Under Advanced click on `Environment variables...` a new window will appear. 

- Double click on the `Path` variable under your username and a new window will appear. 

- Click New and add the copied path like: `C:\<User path to anaconda>\Anaconda3`. 

- Again, add a new but now append `\Scripts` to the copied path like: `C:\<User path to anaconda>\Anaconda3\Scripts`. 

- Click Ok on all windows. 

- To test if it worked, open a new Windows Command Prompt and type `python`. You should now see the python interpreter and Nis Elements should be able to run the Rename_info_file script.  

 

### Windows updates 

The most annoying feature of Windows is automatic updates that can suddenly reboot your computer in the middle of an imaging cycle. To prevent yourself from this frustration, you should disable automatic updates and prevent reboots. See online for instructions for your Windows version. 

  

# Hardware alternatives 

### Other imaging software 

The start of the imaging software is regulated through the `start_imaging_file.txt` in the `ROBOFISH\FISH_database` folder as explained above. To start the imaging, the Nikon software checks this file every ~2 minutes to see if the zero has been changed to a 1 or 2. If it did, it will start the imaging of the respective flow cell. When the imaging is done the Nikon software resets the `start_imaging_file.txt` to zero, so that the ROBOFISH software knows that it can continue with the next fluidic round. If you use different microscope software, you should make functions that mimic this behavior and it should work.   

   

To link the info files to specific image file you can use the `rename_info_file.py` program. The info files will be generated with a name starting with `TEMPORARY` the `rename_info_file.py` program changes the temporary part to `CountXXXXX` where XXXXX will be a number for the labeling cycle. Have your program call the `rename_info_file.py` program with the cycle number and the imaging output folder as inputs. 

 
