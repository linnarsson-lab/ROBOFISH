#Python 3 package to perform and experiment on ROBOFISH.
#Date: 03 April 2017
#Author: Lars E. Borm
#E-mail: lars.borm@ki.se or larsborm@gmail.com
#Python version: 3.5.1

## CONTENT ##
    # Hardware address
    # Class initiation
    # Experimental parameters management
    # Hardware management
    # System calibration (utility functions)
    # Communication with user with push messages
    # Fluid tracking (update buffers, notify user)
    # Fluid handling, Lower level functions
    # Function decorator
    # Fluid handling, Higher level functions
    # Temperature control
    # Imaging functions
    # Error checking
    # Scheduler

################################################################################

# DEPENDENCIES
import serial
from serial.tools import list_ports
from collections import deque
import time
from datetime import datetime, timedelta
import numpy as np
from functools import wraps
from tkinter import *
import pickle
import shutil

# FISH peripherals
import FISH2_peripherals as perif
import sqlite3

# HARDWARE
    # Syringe Pump
import tecanapi
import transport
import syringe
import models
    #Syringe pump models
try:
    from models import XE1000
except ModuleNotFoundError:
    print('Module XE1000 not found. Ignore if not in use.')
try:
    from models import XCalibur
except ModuleNotFoundError:
    print('Module XCalibur not found. Ignore if not in use.')

    ## MX Valve
import MXII_valve

    ## Thermo Cube
try:
    import ThermoCube
except ModuleNotFoundError:
    print('Module ThermoCube not found. Ignore if machine is not in use.')

    ## Oasis
try:
    import Oasis
except ModuleNotFoundError:
    print('Module Oasis not found. Ignore if machine is not in use.')

    ## Yoctopuce Thermistor
try:
    import YoctoThermistor_FISH
except ModuleNotFoundError:
    print('Module YoctoThermisto_FISH not found. Ignore if machine is not in use.')

    ## TC-720 temperature controller
try:
    import Py_TC720
except ModuleNotFoundError:
    print('Module Py_TC720 not found. Ignore if machine is not in use.')

#=============================================================================
# Hardware address      
#=============================================================================    

def find_address(identifier = None):
    """
    Find the address of a serial device. It can either find the address using
    an identifier given by the user or by manually unplugging and plugging in 
    the device.
    Input:
    `identifier`(str): Any attribute of the connection. Usually USB to Serial
        converters use an FTDI chip. These chips store a number of attributes
        like: name, serial number or manufacturer. This can be used to 
        identify a serial connection as long as it is unique. See the pyserial
        list_ports.grep() function for more details.
    Returns:
    The function prints the address and serial number of the FTDI chip.
    `port`(obj): Returns a pyserial port object. port.device stores the 
        address.
    
    """
    found = False
    if identifier != None:
        port = [i for i in list(list_ports.grep(identifier))]
        
        if len(port) == 1:
            print('Device address: {}'.format(port[0].device))
            found = True
        elif len(port) == 0:
            print('''No devices found using identifier: {}
            \nContinue with manually finding USB address...\n'''.format(identifier))
        else:
            print('{:15}| {:15} |{:15} |{:15} |{:15}'.format('Device', 'Name', 'Serial number', 'Manufacturer', 'Description') )
            for p in port:
                print('{:15}| {:15} |{:15} |{:15} |{:15}\n'.format(str(p.device), str(p.name), str(p.serial_number), str(p.manufacturer), str(p.description)))
            raise Exception("""The input returned multiple devices, see above.""")

    if found == False:
        print('Performing manual USB address search.')
        while True:
            input('    Unplug the USB. Press Enter if unplugged...')
            before = list_ports.comports()
            input('    Plug in the USB. Press Enter if USB has been plugged in...')
            after = list_ports.comports()
            port = [i for i in after if i not in before]
            if port != []:
                break
            print('    No port found. Try again.\n')
            while True:
                awnser = input('    Do you want to try again? Y/N')
                if awnser.lower() == 'y' or awnser.lower() == 'n':
                    break
                else:
                    print('    Invalid awnser, type Y for Yes, or N for No')
            if awnser == 'n':
                return
        print('Device address: {}'.format(port[0].device))
        try:
            print('Device serial_number: {}'.format(port[0].serial_number))
        except Exception:
            print('Could not find serial number of device.')
    
    return port[0]

#=============================================================================
# Initiation  
#=============================================================================    
class FISH2():
    """
    Class containing all functions for performing the experiment
    (see: FISH2_peripherals.py for complementing funcitons)
    
    """
    
    def __init__(self, db_path, imaging_output_folder, start_imaging_file_path, system_name='ROBOFISH'):
        """
        Initiate system 
        Input:
        `db_path`(str): Path to the database. Or new name if it does not exist. 
            Suggested name: "FISH_System2_db.sqlite".
        `imaging_output_folder`(str): Path to where the images are saved.
        
        """
        
        self.system_name = system_name
        self.L = perif.FISH_logger(system_name = self.system_name)

        #Some check if it does not exist yet???
        self.db_path = db_path
        print(self.db_path)
        self.imaging_output_folder = imaging_output_folder
        self.start_imaging_file_path = start_imaging_file_path
        self.Parameters = {}
        self.Volumes = {}
        self.Targets = {}
        self.Ports = {}
        self.Ports_reverse = {}
        self.Hybmix = {}
        self.devices = []
        self.Machines = {}
        self.Machine_identification = {}
        self.Fixed_USB_port = {}
        self.Operator_address = {}
        self.Padding = {}
        self.Alert_volume = {}
        self.target_temperature= [None, None]
        self.found_error = False

        self.L.logger.info(f'System name: {system_name}')
        self.L.logger.info(f'Path to database: {self.db_path}')
        self.L.logger.info(f'Path to imaging_output_folder: {imaging_output_folder}')
        self.L.logger.info(f'Path to start_imaging_file_path: {start_imaging_file_path}')
        
              
        # Ask user if hardware can be initialized and primed.
        input('''\nPress Enter if:
            * Flowcell(s) is placed in stage and connected.
            * Heating/cooling cables are connected.
            * All buffers are in the correct position and connected.
            * System is connected.
            * Valves are open.
            * Datafile is committed to the database using the user program.
            * Optional temperature sensor is connected.\n''')

        self.L.logger.info('User confirmed system is ready for operation.')
        

        # Get all data from database
        self.L.logger.info('Retrieving data from database.')
        self.updateExperimentalParameters(self.db_path, ignore_flags=True)
        self.L.logger.info('Successful retrieved data from database.')
        
        #Connecting to hardware
        self.L.logger.info('Connecting and initiating hardware.')
            
        #Find addresses
        self.L.logger.info('    Finding device addresses.')
        device_COM_port = self.deviceAddress()

        #Initiate all connected devices, connected is determined by the user
        # initialize MXValve1
        if self.Machines['MXValve1'] == 1:
            if device_COM_port['MXValve1'] == None:
                self.L.logger.warning('    MXValve1 not connected (no address available).')
            else:
                self.MXValve1 = MXII_valve.MX_valve(address = device_COM_port['MXValve1'], ports=10, name = 'MXValve1', verbose = False)
                self.L.logger.info('    MXValve1 Initialized.')
                self.devices.append('MXValve1')
        else:
            self.L.logger.info('        MXValve1 not connected according to user. Ignore if not needed.')
        
        # initialize MXValve2
        if self.Machines['MXValve2'] == 1:
            if device_COM_port['MXValve2'] == None:
                self.L.logger.warning('    MXValve2 not connected (no address available).')
            else:
                self.MXValve2 = MXII_valve.MX_valve(address = device_COM_port['MXValve2'], ports=10, name = 'MXValve2', verbose = False)
                self.L.logger.info('    MXValve2 Initialized.')
                self.devices.append('MXValve2')
        else:
            self.L.logger.info('        MXValve2 not connected according to user. Ignore if not needed.')
        
        # initialize Temperature Controller 1 (TC_1)
        if self.Machines['ThermoCube1'] == 1:
            if device_COM_port['ThermoCube1'] == None:
                self.L.logger.warning('    ThermoCube_1 not connected (no address available).')
            else:
                self.TC_1 = ThermoCube.ThermoCube(address = device_COM_port['ThermoCube1'], 
                                                  name = 'ThermoCube_1')
                if self.TC_1.connected == True:
                    self.L.logger.info('    Temperature controller TC_1 Initialized.')
                    self.setTemp(20, 'Chamber1')
                    self.devices.append('ThermoCube1')
                else:
                    self.L.logger.warning('    Could not make a connection with ThermoCube_1.')
        else:
            self.L.logger.info('        ThermoCube1 not connected according to user. Ignore if not needed.')

        # initialize Temperature Controller 2 (TC_2) Replace this with your temperature controller if needed.
        if self.Machines['ThermoCube2'] ==1:
            if device_COM_port['ThermoCube2'] == None:
                self.L.logger.warning('    ThermoCube_2 not connected (no address available).')
            else:
                self.TC_2 = ThermoCube.ThermoCube(address = device_COM_port['ThermoCube2'], 
                                                  name = 'ThermoCube_2')
                if self.TC_2.connected == True:
                    self.L.logger.info('    Temperature controller TC_2 Initialized.')
                    self.setTemp(20, 'Chamber2')
                    self.devices.append('ThermoCube2')
                else:
                    self.L.logger.warning('    Could not make a connection with ThermoCube_2.')
        else:
            self.L.logger.info('        ThermoCube2 not connected according to user. Ignore if not needed.')

        # initialize Temperature Controller 1 (TC_1)
        if self.Machines['Oasis1'] == 1:
            if device_COM_port['Oasis1'] == None:
                self.L.logger.warning('    Oasis_1 not connected (no address available).')
            else:
                self.TC_1 = Oasis.Oasis(address = device_COM_port['Oasis1'], 
                                                  name = 'Oasis_1')
                if self.TC_1.connected == True:
                    self.L.logger.info('    Temperature controller TC_1 Initialized.')
                    self.setTemp(20, 'Chamber1')
                    self.devices.append('Oasis1')
                else:
                    self.L.logger.warning('    Could not make a connection with Oasis_1.')
        else:
            self.L.logger.info('        Oasis1 not connected according to user. Ignore if not needed.')

        # initialize Temperature Controller 2 (TC_2) Replace this with your temperature controller if needed.
        if self.Machines['Oasis2'] ==1:
            if device_COM_port['Oasis2'] == None:
                self.L.logger.warning('    Oasis_2 not connected (no address available).')
            else:
                self.TC_2 = Oasis.Oasis(address = device_COM_port['Oasis2'], 
                                                  name = 'Oasis_2')
                if self.TC_2.connected == True:
                    self.L.logger.info('    Temperature controller TC_2 Initialized.')
                    self.setTemp(20, 'Chamber2')
                    self.devices.append('Oasis2')
                else:
                    self.L.logger.warning('    Could not make a connection with Oasis_2.')
        else:
            self.L.logger.info('        Oasis2 not connected according to user. Ignore if not needed.')

        # Initiate TC720
        if self.Machines['TC720'] == 1:
            if device_COM_port['TC720'] == None:
                self.L.logger.warning('    TC720 not connected (no address available).')
            else:
                print(device_COM_port['TC720'])
                self.TC720 = Py_TC720.TC720(address = device_COM_port['TC720'],
                                    name = 'TC720',
                                    mode = 0, 
                                    control_type = 0,
                                    default_temp = 20, 
                                    verbose = False)
                self.L.logger.info('    TC720 Initialized.')
                self.devices.append('TC720')
        else:
            self.L.logger.info('        TC720 not connected according to user. Ignore if not needed.')

        # initialize Yocto_Thermistor
        if self.Machines['YoctoThermistor'] == 1:
            try:
                self.temp = YoctoThermistor_FISH.FISH_temperature_deamon(serial_number = self.Machine_identification['YoctoThermistor'], log_interval=10)
                self.L.logger.info('    YoctoThermistor Initialized.')
                self.temp.deamon_start()
                self.devices.append('YoctoThermistor')
            except SystemExit as e:
                self.L.logger.info('    YoctoThermistor not connected, temperature functions will not work!')
                self.L.logger.info('    Error code: {}'.format(e))
        else:
            self.L.logger.info('        YcotoThermistor not connected according to user. Ignore if not needed.')

        # Initialize syringe pump CavroXE1000
        if self.Machines['CavroXE1000'] == 1:
            self.L.logger.info('    Connecting with CavroXE1000.')
            pump_address = transport.TecanAPISerial.findSerialPumps()
            self.pump = models.XE1000(com_link =transport.TecanAPISerial(0, pump_address[0][0] , 9600 ))
            self.L.logger.info('    Established connection with CavroXE1000.')
            self.L.logger.info('    Initiating CavroXE1000.')
            self.connectPort('Waste') #Change to waste port
            self.pump.init(in_port='right', init_speed = 20)
            self.pump.setSpeed(speed=400, execute = True)
            self.pump.setBacklashSteps(5, execute = True)
            self.L.logger.info('    CavroXE1000 Initialized.')
            self.devices.append('CavroXE1000')
        else:
            self.L.logger.info('        CavroXE1000 not connected according to user. Ignore if not needed.')

        # Initiate Syringe pump CavroXCalibur
        if self.Machines['CavroXCalibur'] == 1:
            self.L.logger.info('    Connecting with CavroXCalibur')
            pump_address = transport.TecanAPISerial.findSerialPumps()
            self.connectPort('Waste') #Change to waste port
            self.pump = models.XCalibur(com_link= transport.TecanAPISerial(0, pump_address[0][0] , 9600 ),
                    syringe_ul=2500, 
                    direction='Z',
                    microstep=False, 
                    slope=14, 
                    speed=22,
                    debug=False, 
                    debug_log_path='.')
            self.L.logger.info('    Established connection with CavroXCalibur.')
            self.L.logger.info('    Initiating CavroXCalibur.')
            self.pump.init(speed=16, 
                    direction='Z') #Z = Input left, output right. Y = Input right, output left
            self.pump.setSpeed(20)
            self.L.logger.info('    CavroXCalibur initiated.')
            self.devices.append('CavroXCalibur')

        #Update active machines
        self.L.logger.info('    Connected devices: {}\n'.format(self.devices))
        #   Set them to 0 or 1 in the local dictionary and the database
        for m in ['MXValve1', 'MXValve2', 'YoctoThermistor', 'CavroXE1000', 'CavroXCalibur', 'ThermoCube1', 'ThermoCube2', 'Oasis1', 'Oasis2', 'TC720']:
            if m in self.devices:
                print('Active machine: {}'.format(m))
                self.Machines[m] = 1
                perif.updateValueDB(self.db_path, 'Machines', column = m, new_value = 1)
            else:
                self.Machines[m] = 0
                perif.updateValueDB(self.db_path, 'Machines', column = m, new_value = 0)
        #   Write them to the yaml info file.
        perif.DBToYaml(self.db_path)

        # Log all the parameters
        self.L.logger.info( 'Start parameters:\n'+''.join(['{}: {}\n'.format(i, self.Parameters[i]) for i in self.Parameters]))
        self.L.logger.info( 'Ports:\n'+''.join(['{}: {}\n'.format(i, self.Ports[i]) for i in self.Ports]))
        self.L.logger.info( 'Active machines:\n'+''.join(['{}: {}\n'.format(i, self.Machines[i]) for i in self.Machines]))
        self.L.logger.info( 'Machine_identification:\n'+''.join(['{}: {}\n'.format(i, self.Machine_identification[i]) for i in self.Machine_identification]))
        self.L.logger.info( 'Fixed_USB_port:\n'+''.join(['{}: {}\n'.format(i, self.Fixed_USB_port[i]) for i in self.Fixed_USB_port]))
        self.L.logger.info( 'Padding:\n'+''.join(['{}: {}\n'.format(i, self.Padding[i]) for i in self.Padding]))
        self.L.logger.info('____')
        self.L.logger.info('System ready for operation.')
        self.L.logger.info('____')

#=============================================================================
# Experimental parameters management        
#=============================================================================        

    def updateExperimentalParameters(self, db_path, ignore_flags=False, verbose=False):
        """
        Checks if any of the flags are up and if so copies the values into memory.
        Flags indicate new values.
        Makes global dictionaries: Parameters, Buffers, Targets, Ports & Hybmix
        Input:
        `db_path`(str): Full path to database.
        `ignore_flags`(bool): Option to ignore the flags and update everything.
                              If False, it only updates the Tables with new information.
                              Pause flag is not ignored.
        """
        #Check if experiment is paused
        count = 0
        while True:
            flags = perif.returnDictDB(db_path, 'Flags')[0]
            if flags['Pause_flag'] == 0:
                if verbose == True:
                    print('No Pause flag, retrieving data from database.\n')
                break
            else:
                count += 1
                if count % 120 == 0:
                    print('Database blocked. Waiting for user to finish updating datafile. {} minutes'.format((count*(1/6))))
                time.sleep(10)
        
        #Ignore the flags that indicate change and update everything.
        if ignore_flags == True:
            self.Parameters = perif.returnDictDB(db_path, 'Parameters')[0]
            self.Volumes = perif.returnDictDB(db_path, 'Volumes')[0]
            self.Targets = perif.returnDictDB(db_path, 'Targets')
            self.Ports = perif.returnDictDB(db_path, 'Ports')[0]
            self.Ports_reverse = {v:k for k,v in self.Ports.items()}
            self.Hybmix = perif.returnDictDB(db_path, 'Hybmix')[0]
            self.Machines = perif.returnDictDB(db_path, 'Machines')[0]
            self.Machine_identification = perif.returnDictDB(db_path, 'Machine_identification')[0]
            self.Fixed_USB_port = perif.returnDictDB(db_path, 'Fixed_USB_port')[0]
            self.Operator_address = perif.returnDictDB(db_path, 'Operator_address')[0]
            self.Padding = perif.returnDictDB(db_path, 'Padding')[0]
            self.Alert_volume = perif.returnDictDB(db_path, 'Alert_volume')[0]
        
        #Update all parameters from the database, if there has been an update. 
        else:  
            flags = perif.returnDictDB(db_path, 'Flags')[0]
            if flags['Parameters_flag'] == 1:
                self.Parameters = perif.returnDictDB(db_path, 'Parameters')[0]
                perif.removeFlagDB(db_path, 'Parameters_flag')
            if flags['Volumes_flag'] == 1:
                self.Volumes = perif.returnDictDB(db_path, 'Volumes')[0]
                perif.removeFlagDB(db_path, 'Volumes_flag')
            if flags['Targets_flag'] == 1:
                self.Targets = perif.returnDictDB(db_path, 'Targets')
                perif.removeFlagDB(db_path, 'Targets_flag')
            if flags['Ports_flag'] == 1:
                self.Ports = perif.returnDictDB(db_path, 'Ports')[0]
                self.Ports_reverse = {v:k for k,v in self.Ports.items()}
                perif.removeFlagDB(db_path, 'Ports_flag')
            if flags['Hybmix_flag'] == 1:
                self.Hybmix = perif.returnDictDB(db_path, 'Hybmix')[0]
                perif.removeFlagDB(db_path, 'Hybmix_flag')
            if flags['Machines_flag'] == 1:
                self.Machines = perif.returnDictDB(db_path, 'Machines')[0]
                perif.removeFlagDB(db_path, 'Machines_flag')
            if flags['Machine_identification_flag'] == 1:
                self.Machine_identification = perif.returnDictDB(db_path, 'Machine_identification')[0]
                perif.removeFlagDB(db_path, 'Machine_identification_flag')
            if flags['Fixed_USB_port_flag'] == 1:
                self.Fixed_USB_port = perif.returnDictDB(db_path, 'Fixed_USB_port')[0]
                perif.removeFlagDB(db_path, 'Fixed_USB_port_flag')
            if flags['Operator_address_flag'] == 1:
                self.Operator_address = perif.returnDictDB(db_path, 'Operator_address')[0]
                perif.removeFlagDB(db_path, 'Operator_address_flag')
            if flags['Padding_flag'] == 1:
                self.Padding = perif.returnDictDB(db_path, 'Padding')[0]
                perif.removeFlagDB(db_path, 'Padding_flag')
            if flags['Alert_volume_flag'] == 1:
                self.Alert_volume = perif.returnDictDB(db_path, 'Alert_volume')[0]
                perif.removeFlagDB(db_path, 'Alert_volume_flag')
        
        
#=============================================================================
# Hardware management        
#=============================================================================

    def deviceAddress(self):
        """
        Functions that finds the Windows 'COM' ports of all used devices
        automatically. Devices are identified by their FTDI chip identifier.
        To find the FTDI chip identifier use the find_address() function 
        and add the identifier to the user FISH_System_datafil.yaml
        Returns:
        `device_COM_port` (dict): Dictionary with name of device and COM port. 
        Devices need to be added to the database using the FISH2_user_program and
        the FISH_system_datafile.yaml
        """
        device_COM_port = {
            'CavroXE1000': None,
            'CavroXCalibur': None,
            'MXValve1': None,
            'MXValve2': None,
            'ThermoCube1': None,
            'ThermoCube2': None,
            'Oasis1': None,
            'Oasis2': None,
            'YoctoThermistor': None,
            'TC720': None}

        #Find all serial ports
        ports_info = serial.tools.list_ports.comports()
        #Invert the Machine_identification to get the name of the machines using the identifier
        identifier = {v: k for k, v in self.Machine_identification.items()}

        #Try if machine can be found using the given identifiers.
        for port in ports_info:
            try:
                corresponding_machine = identifier[port.serial_number]
                device_COM_port[corresponding_machine] = port.device
            except Exception as e:
                pass
        
        #For machines without an identification method, add the static address.
        for machine in device_COM_port.keys():
            if device_COM_port[machine] == None:
                if self.Fixed_USB_port[machine] != 'None':
                    print(repr(self.Fixed_USB_port[machine]))
                    device_COM_port[machine] = self.Fixed_USB_port[machine]
                    print(device_COM_port[machine])
                    print('Communication port for: {} added using a static address. Use with care. Do not move around USB cables without remapping the addresses.'.format(machine))
                else:
                    if self.Machines[machine] == 1:
                        print(f'Warning! No USB port information or serial identification code present for: {machine} add either to the Fixed_USB_port or Machine_identification table using the user program. Ignore if machine has its own identification method.')
 
        return device_COM_port
  
    def getSerialPump_XCalibur(self):
        ''' 
        Adapted from the "XCaliburD" function in "gui_setup.py"
        In the "tecancavro" package, written by: Ben Pruitt & Nick Conway
        https://github.com/benpruitt/tecancavro
        
        Assumes that the pump is a XCalibur pump and returns a tuple
        (<serial port>, <instantiated XCalibur>)
        
        '''
        pump_list = transport.TecanAPISerial.findSerialPumps()
        return [(ser_port, XCalibur(com_link=transport.TecanAPISerial(0,
                pump_list[0][0] , 9600 ))) for ser_port, _, _ in pump_list]

    def getSerialPump_XE1000(self):
        ''' 
        Adapted from the "XCalibur" function in "gui_setup.py"
        In the "tecancavro" package, written by: Ben Pruitt & Nick Conway
        https://github.com/benpruitt/tecancavro
        
        Assumes that the pump is a XE1000 pumps and returns a tuple
        (<serial port>, <instantiated XCalibur>)
        
        '''
        pump_list = transport.TecanAPISerial.findSerialPumps()
        return [(ser_port, XE1000(com_link=transport.TecanAPISerial(0,
                 ser_port, 9600))) for ser_port, _, _ in pump_list]

    
#=============================================================================    
# System calibration
#=============================================================================    
    
    def findPaddingVolumeChamber(self, volume, air_port , target):
        """
        find the padding volume between valve and chamber by testing a volume.
        The function will aspirate an air bubble from the given port. (make sure no
        fluid tubes are connected to that port).
        Then it will create a padding volume that is specified and push it to the
        target port. By monitoring the location of the air bubble you can
        determine the padding volume. If the air bubble is just out of the tube/on
        the correct position, the padding volume is correct and should be saved in 
        the "FISH_System_datafile.yaml".
        Input:
        `volume`(int): Volume to test as padding volume
        `air_port`(str): Name of port that is disconnected. Like: 'P3'
        `target`(str): Target to push to. Like: 'Chamber1' or 'P2'
        """
        input('This function will push a tiny air bubble to the hybridization chamber, if it just reaches it you have found the padding volume. Press Enter to continue...')
        self.connectPort(air_port)
        self.pump.extract(volume_ul = 20 , from_port = 'output', execute=True)
        self.connectPort(target)
        self.pump.extract(volume_ul = volume, from_port = 'input', execute=True)
        self.pump.dispense(volume_ul = (volume+20), to_port = 'output', execute=True)
        print('If the padding volume of {}ul is correct, add it to the "FISH_System_datafile.yaml" for the target: {}. Press Enter to continue...'.format(volume, target))
        

    def findPaddingVolumeHYBmix(self, volume, hybmix):
        """
        Find the padding volume between valve and HYBmix by testing a volume.
        
        Start with low volumes, this function will aspirate the hybmix into
        the reservoir, if there still is air between hybmix and running liquid
        the given volume is not sufficient.
        Input:
        `volume`(int): Volume to test as padding volume
        `hybmix`(str): Hybmix to aspirate. Like: 'HYB01'
        """
        input('Place some liquid (use same viscosity as real experiment) in the system. This function will aspirate the volume and you need to see if the liquid reaches the reservoir tube. The best is if it just reaches the reservoir. Press Enter to continue...')
        self.connectPort(hybmix)
        self.pump.extract(volume_ul = volume , from_port ='output', execute=True)
        self.resetReservoir(0)
        self.connectPort(hybmix)
        self.pump.extract(volume_ul = 150, from_port = 'output', execute=True)
        print('Look at reservoir, if you see an air bubble you need to aspirate more.')
        input('Press enter to continue, this will empty the tubes...')
        
        self.resetReservoir(0)
        self.connectPort(hybmix)
        self.pump.extract(volume_ul = 1000 , from_port = 'output', execute=True)
        self.resetReservoir(200)
        print('If the padding volume of {}ul is correct, add it to the "FISH_System_datafile.yaml" for the port: {}. Press Enter to continue...'.format(volume, hybmix))
        
    def findPaddingVolumeBuffer(self, volume, port, air_port):
        """
        find the padding volume between valve and a buffer by testing a volume.
        If you see the buffer after the air bubble in the reservoir, the volume is
        sufficient and should be saved in "FISH_System_datafile.yaml".
        Input:
        `volume`(int): Volume to test as padding volume
        `buffer_intrest`(str): Name of port of interest
        `air_port`(str): Port connected to air
        """
        print('Make sure the tube of the buffer of interest is filled with air.')
        input('Press Enter to start and aspirate {}ul of the buffer. Please look at the buffer and note where it ends up. Press Enter to continue...'.format(volume))
        self.extractBuffer(port, volume)
        print('Look at reservoir, if you see that the buffer passed the valve and is just in the reservoir tube, the volume is good.')
        input('Press enter to continue, this will fill the tube with air so you can perform the test again...')
        self.resetReservoir(0)
        self.extractBuffer(air_port, (volume + 200))
        self.connectPort(port)
        self.pump.dispense(volume_ul=(volume+200), to_port='output', execute=True)
        print('If the padding volume of {}ul is correct, add it to the "FISH_System_datafile.yaml" for the port: {}. Press Enter to continue...'.format(volume, port))

#=============================================================================    
# Communication with user by push messages
#=============================================================================

    def push(self, short_message='', long_message=''):
        """
        Wrapper around the send_push() function from peripherals.
        Input:
        `short_message`(str): Subject of message.
        `long_message`(str): Body of message.
        """
        sm = '{}: {}'.format(self.system_name, short_message)
        perif.send_push(self.Operator_address, operator = self.Parameters['Operator'],
                       short_message=sm, long_message=long_message)
    
#=============================================================================    
# Fluid tracking (update buffers, notify user)
#=============================================================================
     
    def checkBuffer(self):
        """
        Function that checks if any of the buffers is running low. 
        It will notify the Operator if any of the buffers need a refill
        The minimal volumes can be defined with the user program in the 
        Alert_volume table. Waste is checked if it is too full.
        """
        #Check current volumes
        almost_empty = []
        for p, v in self.Volumes.items():
            if isinstance(v, int) or isinstance(v, float): #Do not check unconnected buffers
                #Check if buffer has a name and alert volume
                if self.Ports[p] == 'None' or self.Alert_volume[p] == 'None':
                    raise Exception('Port {} is not correctly configured, a volume is listed but no name or no Alert volume is specified. Name: {}, Alert_volume: {}. Please update datafile.'.format(p,self.Ports[p], self.Alert_volume[p]))
                #Check waste
                elif p == self.Ports_reverse['Waste']:
                    if v > self.Alert_volume[p]:
                        almost_empty.append([p, v])
                #Check buffers
                elif v < self.Alert_volume[p]:
                    almost_empty.append([p, v])
                else:
                    pass

        #Send message
        if almost_empty != []: 
            long_message = 'Replace:\n'
            for i in almost_empty:
                #Get the name of the buffer connected to the port
                if i[0] != 'RunningBuffer':
                    buffer_name = self.Ports[i[0]]
                else:
                    buffer_name = i[0]
                #Compose message
                long_message += '{}: {}, current vol: {}ml\n'.format(i[0], buffer_name, round(i[1]/1000))
            long_message += time.strftime("%d-%m-%Y %H:%M:%S")

            self.push(short_message='Buffer status', long_message= long_message)
            print(long_message)
            
    def updateBuffer(self, target, volume, check=True):
        """
        Subtract used volume of a certain buffer.
        Input:
        `target`(str): Buffer name or port number
        `volume`(int): volume to subtract. in ul
        `check`(bool): Check if buffers need to be replaced, Default = True
        
        """
        #Find the buffer code of the buffer
        port = self.getPort(target, port_number=False)

        #Update waste by summing
        if port == self.Ports_reverse['Waste']:
            self.Volumes[port] = self.Volumes[port] + volume
            perif.updateValueDB(self.db_path, 'Volumes', column = port, operation = '+', value = volume)
        #Update buffer by substacting
        else:
            self.Volumes[port] = self.Volumes[port] - volume
            perif.updateValueDB(self.db_path, 'Volumes', column = port, operation = '-', value = volume)

        #Check if buffers need replacement
        if check == True:
            self.checkBuffer()

#=============================================================================    
# Fluid handling, Lower level functions
#=============================================================================

    def getPort(self, target, port_number=False):
        """
        Return the port code of a target buffer
        Input:
        `target`(str): Either the port number (P1-P20) or
            the buffer name as in the 'Ports' dictionary..
        `port_number`(bool): If False, returns the port code P1-P20.
            If True, returns the port number 1-20.
        """
        #Check input
        if target not in self.Ports.keys() and target not in self.Ports.values(): 
            raise(ValueError('Invalid target name: {}, Not present in Ports'.format(target))) 

        if target in self.Ports.keys():
            port = target
        else:
            port = self.Ports_reverse[target]

        #Return the port code.
        if port_number == False:
            return port
        #Return the port number
        if port_number == True:
            return int(port[1:])


    def connectPort(self, target):
        """
        Function to connects the reservoir to the target buffer.
        Input:
        `target`(str): Either the port number (P1-P20) or
            the buffer name as in the 'Ports' dictionary.
        """
        #Get the number of the port
        port = self.getPort(target, port_number=True)

        #Change port
        if  port > 10:
            #Check if valve 2 is connected
            if 'Valve2' not in self.Ports.values():
                raise(ValueError('Connection to "Valve2" is not defined. Add "Valve2" to the Ports table.'))
            #Connect valve 1 with valve 2
            port_valve2 = self.getPort('Valve2', port_number=True)
            self.MXValve1.change_port(port_valve2)
            #Connect to the right port on valve 2
            self.MXValve2.change_port(port - 10)
        else:
            #Connect to the right port on valve 1
            self.MXValve1.change_port(port)
    
    def extractBuffer(self, buffer, volume, bubble = False, bubble_volume = 30):
        """
        Load a certain volume of a certain buffer into the reservoir with or 
        without an air bubble.
        Input:
        `buffer`(str): Target buffer/port as in the 'Ports' dictionary.
        `volume`(int): Volume to aspirate.
        `bubble`(bool): If a bubble of 30ul should be aspirated. Default = False
        `bubble_volume`(int): Volume of bubble. Default 30ul.
        """
        if bubble == True:
            self.airBubble(bubble_volume = bubble_volume)

        self.connectPort(buffer) #Change to port of buffer
        self.pump.extract(volume_ul = volume, from_port = 'output', execute=True)        
        
    def dispenseBuffer(self, target, volume):
        """
        Dispenses a volume to the target port.
        Presumes that some buffer is extracted with a volume not larger than the
        dispense volume first.
        Input:
        `target`(str): target buffer/port as in the 'ports' dictionary.
        `volume`(int): volume in ul to dispense.
        """
        self.connectPort(target)
        self.pump.dispense(volume_ul = volume, to_port= 'output', execute=True)       

    def padding(self, target):
        """
        Aspirates a padding volume to bridge the tubing from reservoir to target,
        so that the buffer reaches the target..
        Input:
        `target`(int): Target to dispense to, eiter Buffer name as in Ports,
            or the port number. 
        Returns the padding volume.
        """
        target = self.getPort(target)
        volume = self.Padding[self.getPort(target)]
        self.pump.extract(volume_ul = volume, from_port = 'input', execute=True)
        return volume    

    def airBubble(self, bubble_volume = 30): #Not advised to use air bubble
        """
        Aspirate an air bubble into the reservoir. To separate running liquid
        from the buffer to dispense.
        Input:
        `bubble_vollume`(int): size of the bubble in ul. Default = 30.
                               volume should be between 10 and 50 ul.
        10ul might be unstable. 30 works consistent
        """
        #in the 1/8"OD, 0.62" tube of the reservoir, 1mm holds 1.94778 ul
        if not 10 <= bubble_volume <= 50:
                raise(ValueError('`bubble_volume` must be between 0 and {}'.format(bubble_volume)))
        self.connectPort('Air') #Change to air port

        #When working with air, a backlash is not desired as it might pump some buffer
        #into the air filter, because the backlash is bigger than the air volume.
        original_backlash = self.pump.getBacklashSteps()
        self.pump.setBacklashSteps(0, execute=True)
        self.pump.extract(volume_ul = bubble_volume, from_port = 'output', execute=True)
        self.pump.setBacklashSteps(original_backlash, execute=True)  

    def resetReservoir(self, replace_volume = 200, update_buffer = False):
        """
        Replaces the "replace_volume" ul of RunningBuffer in the reservoir that is closest
        to the multivalve.
        Input:
        `replace_volume`(int): Volume to replace in reservoir. Default 200ul.
        `update_buffer`(bool): If true it will update the RunningBuffer  and Waste volumes.
        """
        max_volume = self.pump.syringe_ul
        if not 0 <= replace_volume <= (max_volume + 1):
                raise(ValueError('`replace_volume` must be between 0 and {}'.format(max_volume)))
        self.connectPort('Waste') #Change to waste port
        self.pump.changePort('output', execute=True) #change to output
        self.pump.movePlungerAbs(0, execute=True) #return pump to 0
        if replace_volume > 0: 
            self.pump.extract(volume_ul = replace_volume, from_port = 'input', execute=True)
            self.pump.dispense(volume_ul= replace_volume, to_port = 'output', execute=True)
        if update_buffer == True:
            self.updateBuffer('RunningBuffer', replace_volume, check=False)  
            self.updateBuffer('Waste', replace_volume, check=False)

#=============================================================================
# Function decorator
#=============================================================================

    def functionWrap(function):
        """
        Wrapper for high level functions.
        The wrapper will execute the following steps (indicated with *):
        *Check if the experiment is paused by the user.
        *Check if the database is updated and if so update the parameters.
        *If buffers are replaced, prime their respective fluid lines.
        *Start timer.
        Execute function.
        *Stop timer.
        *Calculate time to wait.
        *Sleep the wait time minus function execution time.
        Input as keyword arguments:
            `d`(int): number of days to wait.
            `h`(int): number of hours to wait.
            `m`(int): number of minutes to wait.
            `s`(int): number of seconds to wait.
        
        The function can take up till 10% of the incubation time it is given.
        If it extends that it will be set to 10% of the incubation time. And
        the remaining wait time will be 90% of the given incubation time.
            
        """
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            #Check if user paused the experiment
            count = 0
            while True:
                pause = perif.returnDictDB(self.db_path, 'Flags')[0]['Pause_flag']
                if pause == 1:
                    if count == 0:
                        print('Experiment paused. Continue the experiment in the user program.')
                    time.sleep(1)
                    count += 1
                    #Check for errors on the system and send a pause reminder after 10min, every 10min.
                    if count >= 600 and (count%600) == 0: 
                        self.check_error(35, 5, 10)
                        self.L.logger.info('Experiment paused by user. Already {} minutes.'.format(round(count/6)))
                        self.push(short_message= 'Experiment paused', 
                                  long_message='Experiment is still paused by user. Already {} minutes.'.format(round(count/6)))
                else:
                    break

            #Update
            self.updateExperimentalParameters(self.db_path, ignore_flags=False)
            
            #Prime buffers if the prime flag has been set for the specific buffer
            current_flags = perif.returnDictDB(self.db_path, 'Flags')[0]
            for p in self.Ports:
                if current_flags[p] == 1:
                    self.prime(p)
                    perif.removeFlagDB(self.db_path, p)
                    self.L.logger.info('Primed port {} connected to {} buffer after replacement.'.format(p, self.Ports[p]))

            #Input handling
            if 'd' in kwargs:
                sleep_d = kwargs['d'] * 86400
                del kwargs['d'] #If it is not deleted the function gets the kwargs, which will be invalid arguments.
            else:
                sleep_d = 0
            if 'h' in kwargs:
                sleep_h = kwargs['h'] * 3600
                del kwargs['h']
            else:
                sleep_h = 0
            if 'm' in kwargs:
                sleep_m = kwargs['m'] * 60
                del kwargs['m']
            else:
                sleep_m = 0
            if 's' in kwargs:
                sleep_s = kwargs['s']
                del kwargs['s']
            else:
                sleep_s = 0
            #Calculate total incubation time
            total_sleep = sleep_d + sleep_h + sleep_m + sleep_s
                
            #Execute wrapped function
            tic = time.time()
            r = function(self, *args, **kwargs)     
            toc = time.time()
            execution_time = toc - tic
            #A function can only take 10% of the incubation time it is given.
            #If it extends that it will be set to 10% of the incubation time.
            if execution_time > 0.1 * total_sleep:
                execution_time = 0.1 * total_sleep
            
            #Subtract function execution time
            total_sleep = total_sleep - execution_time
            if total_sleep > 0:
            
                #Secure sleep remaining time
                self.secure_sleep(total_sleep, period=120, alarm_room_temperature=35, temperature_range=5, number_of_messages=10)
                
            return r
        return wrapped
        
#=============================================================================
# Fluid handling, Higher level functions
#=============================================================================

    @functionWrap
    def extractDispenseRunningBuffer(self, volume, target, padding=True):
        """
        Extract RunningBuffer buffer into the reservoir and dispenses it to the target.
        Also tracks the buffer volume changes, and presumes that all used buffer will
        (eventually) end up in the waste container.
        Input:
        `volume`(int): volume to extract and dispense.
        `target`(str): target port as in the 'ports' dictionary.
        `padding`(bool): True if padding needs to be used to reach target.
        """
        #Check if the max volume of the syringe is not exceeded.
        max_volume = self.pump.syringe_ul
        if padding == True:
            volume_to_aspirate = volume + self.Padding[self.getPort(target)]
            padding_error = 'and padding volume: {}ul.'.format(self.Padding[self.getPort(target)])
        else:
            volume_to_aspirate = volume
            padding_error = ''
        if not 0 <= volume_to_aspirate <= (max_volume + 1):
            raise(ValueError('''Pump syringe volume exceeded.\n
                The target volume and padding can not be more than: {}ul.\n
                Volume to pipette: {}ul {}'''.format(max_volume, volume, padding_error)))
                
        #Discard 50ul of Running buffer to make sure it is clean and without air bubbles.
        self.resetReservoir(replace_volume = 50)
        #Extract
        self.pump.extract(volume_ul=volume, from_port='input', execute=True)
        if padding == True:
            pad = self.padding(target)
        else:
            pad = 0
        #Dispense
        total_vol = volume + pad
        self.dispenseBuffer(target, total_vol)
        #Data handling
        self.updateBuffer('Waste', (total_vol+50), check=False)
        self.updateBuffer('RunningBuffer', (total_vol+50), check=True)
        self.L.logger.info('    Dispensed {}ul of {} to {}, with speed {}, padding={}.'.format(volume, self.Ports['RunningBuffer'], target, self.pump.speed, pad))   
 
    @functionWrap
    def extractDispenseBuffer(self, buffer, volume, target, padding=True, same_buffer_padding=False, double_volume=False, speed=None):
        """
        Extract a desired buffer into the reservoir and dispenses it to the target.
        Also tracks the buffer volume changes, and presumes that all used buffer will
        (eventually) end up in the waste container.
        Input:
        `buffer`(str): buffer/port as in the 'ports' dictionary. Like: 'WB'
        `volume`(int): volume to extract and dispense.
        `target`(str): target port as in the 'ports' dictionary. Like: 'Chamber1'
        `padding`(bool): Whether or not to use a padding volume. Useful when
            you do multiple washes with the same buffer. The first should have
            a padding with the same_buffer_padding. The second can then just 
            have no padding. When the tissue is washed it will first be washed
            with the buffer that is already in the tubes and then with the new
            buffer. 
        `same_buffer_padding`(bool): If True, uses the same buffer for the
            padding volume, otherwise it uses RunningBuffer2X. Use in combination with 
            padding for all non-first washes.
        `double_volume` (bool): Dispense the double volume. Used in the first 
            wash of a series to completely exchange the previous buffer.
        `speed`(int): dispense speed. Unit depends on the specific pump used
            refer the pump specific speeds.
        """
        #Check if the max volume of the syringe is not exceeded.
        max_volume = self.pump.syringe_ul
        volume_to_aspirate = (volume + (volume * int(double_volume)))+ (self.Padding[self.getPort(target)] * (int(padding)))
        if not 0 <= volume_to_aspirate <= (max_volume + 1):
            raise(ValueError('''Pump syringe volume exceeded.\n
                The volume and padding can not be more than: {}ul.\n
                Volume to pipette: {}ul and padding volume: {}ul.'''.format(max_volume, volume, self.Padding[self.getPort(target)])))

        #Flush 50ul buffer to prevent any contamination.
        self.resetReservoir(replace_volume=50)
        #Extract buffer
        if double_volume == True:
            volume = volume * 2
        self.extractBuffer(buffer, volume, bubble=False)

        #Creates a padding volume in syringe to bridge the tubes between reservoir and target
        if padding == False:
            pad = 0
        else:
            if same_buffer_padding == True: #Same buffer as padding (for next washing cycle)
                pad = self.Padding[self.getPort(target)]
                self.extractBuffer(buffer, pad, bubble=False)
            else: #RunningBuffer as padding
                pad = self.padding(target)

        if speed != None: 
            if not self.pump.min_speed <= speed <= self.pump.max_speed:
                print('speed: {}, self.pump.speed: {}'.format(speed, self.pump.speed))
                raise ValueError('Invalid speed: "{}", Speed should be between {} and {}'.format(speed, self.pump.min_speed, self.pump.max_speed))

            #Change speed
            if 'CavroXCalibur' in self.devices:
                cached_speed = self.pump.getSpeed()
                print('caching pump speed, check if this is OK: {}'.format(cached_speed))
            if 'CavroXE1000' in self.devices:
                cached_speed = self.pump.getSpeed()
                print('caching pump speed, check if this is OK: {}'.format(cached_speed))
            self.pump.setSpeed(speed, execute=True)
            #Dispense buffer
            total_volume = volume + pad 
            self.dispenseBuffer(target, total_volume)
            self.pump.setSpeed(cached_speed, execute=True)
        else:
            #Dispense buffer
            speed = self.pump.speed
            total_volume = volume + pad 
            self.dispenseBuffer(target, total_volume)
            
        if padding == False:
            self.updateBuffer(buffer, (volume+50), check=False)
            self.updateBuffer('Waste', (volume+50), check = True)
        else:
            if same_buffer_padding == True:
                self.updateBuffer(buffer, (volume+50+pad), check=False)
                self.updateBuffer('Waste', (volume+50+pad), check = True)
            else:
                self.updateBuffer(buffer, (volume+50), check=False)
                self.updateBuffer('RunningBuffer', pad, check=False)
                self.updateBuffer('Waste', (volume+50+pad), check = True)
        self.L.logger.info('    Dispensed {}ul of {} to {} with speed {}, padding={}, same_buffer_padding={}, double_volume={}'.format(volume, buffer, target, speed, padding, same_buffer_padding, double_volume))

    @functionWrap    
    def extractDispenseHybmix(self, target, cycle, indirect=None, steps = 10, slow_speed = None, prehyb=True, wash=True, wash_cycles=5):
        """
        Loads Hybmix without probes in reservoir, push it towards the chamber.
        Then load Hybmix with probes in reservoir and dispense to target chamber.
        While this happens the mix without probes will be pushed through first.
        Input:
        `target`(str): Target chamber. Like: 'Chamber1'
        `cycle`(int): Current cycle of experiment.
        `indirect`(str): Optional when indirect labeling is used. Set indirect 
            to "A" if you want to dispense the encoding probes. Pass "B" if you 
            want to dispense the detection probes.
        `steps`(int): The Hybmix is pumped through the degasser intermittently
            so that the degasser can remove all air bubbles. First the hybmix 
            is pumped up to the degasser by using the "Degass" padding volume, 
            then in every step 25ul is pumped through. Make sure that the 
            "Degass" padding volume plus the number of steps times 25ul does 
            not exceed the hyb mix volume. This will result in a pump error. 
            Default = 10 (250ul) 
        `slow_speed`(int): Speed for the pump that is slower to dispense the 
            viscous buffer.
        `prehyb`(bool): Before dispensing the Hybridization mix with probes
            dispense a mix without probes to equilibrate the components in 
            the sample. 
        `wash`(bool): Wash the hybmix tubes. Default True
        `wash_cycles`(int): Number of times to wash the hybmix tubes.
        """
        #"HYB" is the hybridization buffer without probes in the big container.
        #"Hybmix" is the hybridization buffer with the probes, in the eppendorf tubes.

        Hybmix_vol = self.Parameters['Hybmix_volume']
        if target.lower() == 'chamber1':
            chamber = 'C1_'
        elif target.lower() == 'chamber2':
            chamber = 'C2_'
        else:
            raise Exception ('Unknown Target: "{}". Choose "Chamber1" or "Chamber2"'.format(target))
        
        cycle = str(cycle).zfill(2)
        
        Hybmix_code = chamber + cycle

        if indirect != None:
            if indirect.lower() == 'a':
                indirect = '_A'
                indirect = '_A'
            elif indirect.lower() == 'b':
                indirect = '_B'
            elif indirect.lower() == 'c':
                indirect = '_C'
            else:
                raise Exception ('Unknown Indirect labeling indicator: {}, Choose "A" for encoding probes, "B" for amplifiers or "C" for detection probes'.format(indirect))
            Hybmix_code = chamber + cycle + indirect
        else:
            indirect = '_A'

        #Test if Hybridization mix is placed in the system by the user.
        while True:
            try:
                Hybmix_port_reverse = {v:k for k,v in self.Hybmix.items()}
                Hybmix_port = Hybmix_port_reverse[Hybmix_code]
                break
            except KeyError as e:
                print('Right Hybridization mix is not connected. Add {} to system. KeyError: {}'.format(Hybmix_code, e))
                self.push(short_message='Hybmix not connected',
                          long_message= 'Please place Hybmix {} in system and add it to the "Hybmix" table in the datafile'.format(Hybmix_code))
                input('Press enter if {} is placed and added to the "Hybmix" table in the datafile...'.format(Hybmix_code))
                self.updateExperimentalParameters(self.db_path, ignore_flags=True)


        #Check if the volume is not exceeded
        slow_degass_vol = self.Padding['Degass'] + 25 * steps
        if Hybmix_vol < slow_degass_vol:
            raise Exception("""Hymbix_vol is lower than {0}ul, this will result in an error,
            The Hybmix is pumped through the degasser intermittently, each step
            is 25ul and the first is {1}ul, totaling to {0}ul. So if you use less 
            than {0}ul for the hybridization, remove some steps. Default: 10 steps. 
            Function: extractDispenseHybmix() in FISH2 class""".format(slow_degass_vol, self.Padding['Degass']))

        #Check if the max volume of the syringe is not exceeded.
        max_volume = self.pump.syringe_ul
        volume_to_aspirate = Hybmix_vol + self.Padding[self.getPort(target)]
        if not 0 <= volume_to_aspirate <= (max_volume + 1):
            raise(ValueError('''Pump syringe volume exceeded.\n
                The volume and padding can not be more than: {}ul.\n
                Volume to pipet: {}ul and padding volume: {}ul.'''.format(max_volume, Hybmix_vol, self.Padding[self.getPort(target)])))

        #Check if the speed is valid
        if slow_speed == None or not self.pump.min_speed <= slow_speed <= self.pump.max_speed:
            raise Exception('Slow_speed: {}, is invalid. Choose a speed between {} and {}. Refer to pump manual for speed codes.'.format(slow_speed, self.pump.min_speed, self.pump.max_speed))

        #Change speed for viscous Hybmix
        if 'CavroXCalibur' in self.devices:
            cached_speed = self.pump.getSpeed()
        if 'CavroXE1000' in self.devices:
            cached_speed = self.pump.getSpeed()
            print('caching pump speed, check if this is OK: {}'.format(cached_speed))
        self.pump.setSpeed(slow_speed, execute=True)

        if prehyb==True:
            #Suck HYB_no_probes in reservoir before Hybmix_probes
                #Discard 20ul to eliminate potential bubbles
            self.extractBuffer('HYB', 20)    

            time.sleep(2) # HYB is viscous, time to equilibrate.
            self.resetReservoir(replace_volume=0)
                #Suck HYB_no_probes, volume is same as for Hybmix_probes
            self.extractBuffer('HYB', Hybmix_vol) 
            time.sleep(2) # Hybmix is viscous, time to equilibrate

            #Dispense HYB_no_probes
            self.dispenseBuffer(target, Hybmix_vol)
            self.updateBuffer('HYB', (Hybmix_vol + 20), check=False)

        #Suck Hybmix_probes to valve 1
        Hybmix_to_valve = self.Padding[self.getPort(Hybmix_port)]
        self.extractBuffer(Hybmix_port, Hybmix_to_valve) 
        time.sleep(2) # Hybmix is viscous, time to equilibrate.

        #Push out air from Hybmix tubes that is now in the reservoir
        self.pump.setSpeed(cached_speed, execute=True)
        self.dispenseBuffer('Waste', Hybmix_to_valve)
        self.resetReservoir(replace_volume=500)
        self.pump.setSpeed(slow_speed, execute=True)

        #Suck up Hybmix_probes into reservoir
        self.extractBuffer(Hybmix_port, Hybmix_vol)

        #Creates a padding volume in syringe to bridge the tubes between reservoir and target
        self.pump.setSpeed(cached_speed, execute=True)
        pad = self.padding(target)
        self.pump.setSpeed(slow_speed, execute=True)

        #Dispense:
            #Hybmix_probes
            #Intermittently push Hybmix_probes through degasser to remove bubbles
            #(degasser is too slow for the flow speed)
        self.dispenseBuffer(target, self.Padding['Degass']) #First to degasser
        time.sleep(30)

        for s in range(steps):
            self.dispenseBuffer(target, 25)
            time.sleep(60)

        self.dispenseBuffer(target, (Hybmix_vol - (self.Padding['Degass'] + (25*steps)))) #Dispense remaining
            #Padding
            #Stop in degasser, In case there is a bubble between Hybmix_probes and
            #Runninguffer in the reservoir.
        self.dispenseBuffer(target, self.Padding['Degass']) 
        time.sleep(60) 
        self.dispenseBuffer(target,(pad - self.Padding['Degass'])) #Dispense remaining

        self.pump.setSpeed(cached_speed, execute=True)
        self.updateBuffer('RunningBuffer', pad + 200 + 500, check=False)
        self.updateBuffer('Waste', (Hybmix_vol+pad + 200 + 500), check = True)
        self.L.logger.info('    Dispensed {} to {}, start hybridization. indirect={}, steps={}, slow_speed={}, prehyb={}, wash={}'.format(Hybmix_code, target, indirect, steps, slow_speed, prehyb, wash))
        perif.removeHybmix(self.db_path, Hybmix_port)

        #Calculate time hybridization would finish.
        hyb_time_code = 'Hyb_time_{}{}'.format(target[-1], indirect)
        hyb_time = self.Parameters[hyb_time_code]        
        current_time = time.strftime("%d-%m-%Y %H:%M:%S")
        finish_time = (datetime.now() + timedelta(hours = hyb_time)).strftime("%d-%m-%Y %H:%M:%S")
        print('Hybridization start time: {}, Done at: {}'.format(current_time, finish_time))

        if wash == True:
            self.cleanHybmixTube(Hybmix_port, cycles=wash_cycles)

    def prime(self, port, update=True):
        """
        Prime the tubing (and needle) of the buffer, when the system is dry or
        after a buffer has been replaced.
        Input:
        `port`(str): Port to prime
        `update`(bool): Update the buffer volume. 
            Select True when priming. Select False when cleaning the tubes.
        """
        #Prime RunningBuffer
        if port == 'RunningBuffer':
            self.resetReservoir(replace_volume=self.pump.syringe_ul)
            self.resetReservoir(replace_volume=self.pump.syringe_ul)
            if update == True:
                self.updateBuffer('RunningBuffer', (2*self.pump.syringe_ul), check=False)
                self.updateBuffer('Waste', (2*self.pump.syringe_ul), check=False)  
        #Prime port
        else:
            if self.Padding[port] != 'None':
                self.extractBuffer(port, self.Padding[port])
                time.sleep(2) #In case of viscous buffers
                self.resetReservoir(200, update_buffer=True)
                if update==True:
                    self.updateBuffer(port, self.Padding[port], check=False)  
                    self.updateBuffer('Waste', self.Padding[port], check=True)  
            else:
                print('Port: {}, can not be primed, no Padding volume is specified.'.format(port))

    def primeSystem(self, system_dry = False):
        """
        Primes the ROBOFISH system for operation.
        Input:
        `system_dry` (bool): If the tubes are empty and the degasser is empty,
                        set to True. It will prime the pump and reservoir and
                        guide you through the priming of the Degassi.
                        If False it will presume that everything is filled with 
                        RunningBuffer except for the hyb chambers.
        """
        self.L.logger.info('Priming system')
        master = Tk()
        Label(master, text="Prime buffers:").grid(row=0, sticky=W)
        print('Select buffers to prime by aspiration (Do not select Waste and output lines like flow cells.)')

        #User input to make a priming selection
        buttons = {}
        for i, p in enumerate(self.Ports.keys()):
            buttons[p] = IntVar()
            Checkbutton(master, text='Port: {:4}, Buffer {}'.format(p, self.Ports[p]), variable=buttons[p]).grid(row=i+1, sticky=W)
        mainloop()
        response = {k: buttons[k].get() for k in buttons.keys()}

        #Prime the EX_pump and reservoir
        if system_dry == True:
            print('''\nTo prime the degasser:\n
            PULL! liquid through the degasser with a syringe. DO NOT PUSH!
            See manual for detailed instructions. If filled reconnect everything.''')
            input('Press Enter to when done...')
            
            print('Priming pump and reservoir')
            self.resetReservoir(replace_volume=self.pump.syringe_ul)
            self.resetReservoir(replace_volume=self.pump.syringe_ul)
            self.L.logger.info('    Primed degasser, Syringe and reservoir. System_dry = True.')
            self.updateBuffer('RunningBuffer', (2*self.pump.syringe_ul), check=False)
            self.updateBuffer('Waste', (2*self.pump.syringe_ul), check=False)  
            
        #Prime the buffers selected in the dialog
        for k, v in response.items():
            if v == 1:
                self.prime(k)
                self.L.logger.info('    Primed port {} connected to buffer {}'.format(k, self.Ports[k]))

        print('''\nPurge the hybridization chambers\n
        Close the shutoff valve and use the purge valve and a RunningBuffer filled syringe
        to push out all air bubbles. Open valve afterwards.\n''')
        input('Press Enter when done and valves are open...')
            
        self.L.logger.info('Primed the system, system_dry = {}.'.format(system_dry))
        
    def cleanHybmixTube(self, port, cycles=5, wash_volume=200):
        """
        Wash the tubbing of the specified port with Running buffer.
        `port`(str): Port number to wash.
        `cycles`(int): Number of wash cycles. Default 5.
        `wash_volume`(int): Extra volume to wash the Eppendorff tube with.
        """
        target = self.getPort(port)
        #Remove hybmix remainder from tubes
        self.connectPort(target)
        self.pump.extract(volume_ul = self.Padding[target], from_port = 'output', execute=True)
        self.resetReservoir(replace_volume=300)

        vol = self.Padding[target] + wash_volume #Fills Eppendorf tube with extra running buffer.
        for c in range(cycles):
            self.pump.extract(volume_ul = vol, from_port = 'input', execute=True)
            self.connectPort(target)
            self.pump.dispense(volume_ul = vol, to_port = 'output', execute=True)
            self.pump.extract(volume_ul = (vol+500), from_port = 'output', execute=True)
            self.resetReservoir(replace_volume=500)

        used_vol = 300 + ((vol + 500) * cycles)
        self.updateBuffer('RunningBuffer', used_vol, check=False)
        self.updateBuffer('Waste', used_vol, check=True)
        self.L.logger.info('    Washed port {} {} times with RunningBuffer: {}.'.format(target, cycles, self.Ports['RunningBuffer'])) 

    def cleanSystem(self, wash=True, hybmix_cycles=5, hybmix_wash_volume=200):
        """
        Clean the system. First it opens a check box where you can select the tubes,
        hybridization chambers and Hybmix tubes to clean. It also replaces the reservoir.
        There are 3 modes of cleaning for different targets:
        "Aspirate" For buffers that first need to be aspirated. Use all conected buffers.
        "Dispence" For output lines that are individually connected to the waste.
            Like a flow cell.
        "HYBMIX" For connections to a Hybmix eppendorff tube or small volume buffers.
        Input:
        `wash`(bool): If True is not only empties the tubes but also washes them
            twice with RunningBuffer for the aspiration option. Default=True
        `hybmix_cycles`(int): Specific for washing Hybmix tubes. Number of cyles
            to wash. Default=5
        `hybmix_wash_volume`(int): Specific for washing hybmix tubes. Extra volume 
            to wash the Eppendorff tube with. Default=200
        """
        self.L.logger.info('Cleaning System.')
        print('Pull up all the needles so that they are not in contact with the liquids.')
        input('Press Enter when needles are up...\n\n')

        print('''A pop-up window will appear. Check the boxes of the buffers that need to be cleaned.
        Tick the "aspirate" box if the buffer needs to be cleaned by first aspirating the remaining buffer and then washing with RunningBuffer.
        Tick the "dispence" box if the tubes need to be washed by flushing with RunningBuffer, use for Flow cells.
        Tick the "HYBMIX" box if a hybridization mix is connected and needs to be cleaned.\n''')
        master = Tk()
        Label(master, text="Clean:").grid(row=0, sticky=W)

        #User input to make a cleaning selection
        buttons = {}
        for i, p in enumerate(self.Ports.keys()):
            if p != 'RunningBuffer':
                buttons['Aspirate_{}'.format(p)] = IntVar()
                Checkbutton(master, text='Port: {:4}, Buffer {:10} ASPIRATE.'.format(p, self.Ports[p]), variable=buttons['Aspirate_{}'.format(p)]).grid(row=i+1, column=1, sticky=W)
                buttons['Dispence_{}'.format(p)] = IntVar()
                Checkbutton(master, text='Port: {:4}, Buffer {:10} DISPENSE.'.format(p, self.Ports[p]), variable=buttons['Dispence_{}'.format(p)]).grid(row=i+1, column=2, sticky=W)
                buttons['HYBMIX_{}'.format(p)] = IntVar()
                Checkbutton(master, text='Port: {:4}, Buffer {:10} HYBMIX.'.format(p, self.Ports[p]), variable=buttons['HYBMIX_{}'.format(p)]).grid(row=i+1, column=3, sticky=W)
        mainloop()
        response = {k: buttons[k].get() for k in buttons.keys()}

        #Clean the ports that need aspiration
        aspirate_vol = 0
        for k, v in response.items():
            if k.startswith('Aspirate') and v == 1:
                port = k.split('_')[1]
                self.L.logger.info('    Cleaning port: {} connected to buffer: {}'.format(port, self.Ports[port]))
                self.prime(port, update=False) #Empties the tube if the needle is not in the liquid.
                self.prime(port, update=False) #twice to clean completely
                if wash == True:
                    self.extractDispenseRunningBuffer(self.Padding[port], port, padding=False)
                    self.prime(port, update=False)
                    self.extractDispenseRunningBuffer(self.Padding[port], port, padding=False)
                    self.prime(port, update=False)
                    aspirate_vol += self.Padding[port] * 2
                    self.L.logger.info('    Washed tube and needle twice of port {} with buffer: {}'.format(port, self.Ports[port]))

        #Clean ports that need dispensing
        dispence_vol = 0
        for k, v in response.items():
            if k.startswith('Dispence') and v == 1:
                port = k.split('_')[1]
                self.extractDispenseRunningBuffer(1000, port, padding=False)
                self.extractDispenseRunningBuffer(1000, port, padding=False)
                self.extractDispenseRunningBuffer(1000, port, padding=False)
                dispence_vol += 3000
                self.L.logger.info('    Flushing port {} connected to {} with 3000ul of {}'.format(port, self.Ports[port], self.Ports['RunningBuffer']))

        #Clean the Hybmix ports:
        for k, v in response.items():
            if k.startswith('HYBMIX') and v == 1:
                port = k.split('_')[1]
                self.cleanHybmixTube(port, cycles=hybmix_cycles, wash_volume=hybmix_wash_volume)

        #Clean the reservoir
        self.resetReservoir(replace_volume=self.pump.syringe_ul, update_buffer=True)
        self.resetReservoir(replace_volume=self.pump.syringe_ul, update_buffer=True)
        self.L.logger.info('    Cleaned reservoir with {}ul of {}'.format(2*self.pump.syringe_ul, self.Ports['RunningBuffer']))

        used_vol = 2*self.pump.syringe_ul + aspirate_vol + dispence_vol
        self.updateBuffer('RunningBuffer', used_vol, check=True)
        self.updateBuffer('Waste', used_vol, check=True)
        self.L.logger.info('System cleaned by user.')  

#=============================================================================
# Temperature control
#=============================================================================

    def setTemp(self, temperature, chamber, sec_per_c = None):
        """
        Set the temperature of Hybridization chamber 1 or 2.
        Input:
        `temperature`(int/float): Desired temperature.
        `chamber`(str): "Chamber1"(Left) or "Chamber2"(right).
        """
        if 'ThermoCube1' in self.devices or 'ThermoCube2' in self.devices or 'Oasis1' in self.devices or 'Oasis2' in self.devices:
            if chamber.lower() == 'chamber1':
                self.TC_1.set_temp(temperature)
                self.target_temperature[0] = temperature
            
            elif chamber.lower() == 'chamber2':
                self.TC_2.set_temp(temperature)
                self.target_temperature[1] = temperature
            
            else:
                raise ValueError('Invalid chamber input: {}. Choose "Chamber1" or "Chamber2"'.format(chamber))
        elif 'TC720' in self.devices:
            chamber = self.TC720.name
            self.TC720.set_temp(temperature)
            self.target_temperature[0] = temperature
        else:
            raise Exception('No temperature controller connected.')
        self.L.logger.info('    {} set to {} degree Celsius.'.format(chamber, temperature))
      
    def setRampTemp(self, temperature, chamber=None, step=1, step_time=1):
        """
        Ramp to a specified temperature with a step increment/decrement
        in degree Celsius and seconds per step.
         Input:
        `temperature`(int/float): Desired temperature.
        `chamber`(str): "Chamber1"(Left) or "Chamber2"(right). None if TC720
            is used.
        `step`(int/float): The step in degree Celsius. Absolute number.
        `step_time`(int/float): Sleep time in seconds untill the next step.
        """
        step = abs(step)
        if 'ThermoCube1' in self.devices or 'ThermoCube2' in self.devices or 'Oasis1' in self.devices or 'Oasis2' in self.devices:
            if chamber.lower() == 'chamber1':
                cur_temp = self.temp.get_temp()[2]
                for t in np.arange(cur_temp, temperature, step if cur_temp<temperature else -step):
                    self.TC_1.set_temp(round(t, 2))
                    time.sleep(step_time)
                self.TC_1.set_temp(temperature)
                self.target_temperature[0] = temperature
            
            elif chamber.lower() == 'chamber2':
                cur_temp = self.temp.get_temp()[3]
                for t in np.arange(cur_temp, temperature, step if cur_temp<temperature else -step):
                    self.TC_2.set_temp(round(t, 2))
                    time.sleep(step_time)
                self.TC_2.set_temp(temperature)
                self.target_temperature[1] = temperature
            else:
                raise ValueError('Invalid chamber input: {}. Choose "Chamber1" or "Chamber2"'.format(chamber))

        elif 'TC720' in self.devices:
            chamber = self.TC720.name
            cur_temp = self.TC720.get_temp()
            for t in np.arange(cur_temp, temperature, step if cur_temp<temperature else -step):
                self.TC720.set_temp(round(t, 2))
                time.sleep(step_time)
            self.TC720.set_temp(temperature)
            self.target_temperature[0] = temperature
        else:
            raise Exception('No temperature controller connected.')
        self.L.logger.info('    {} ramped to {} degree Celsius with {}C per step of {}seconds.'.format(chamber, temperature, step, step_time))


    def waitTemp(self, target_temp, chamber, error=1, array_size=5, sd=0.02, verbose = False):
        """
        Wait until chamber has reached target temperature.
        Input:
        `target_temp`(float): Temperature to reach.
        `chamber`(str): "Chamber1"(Left) or "Chamber2"(right).
        `error`(float): Degree C error allowed between target and real temperature.
        `array_size`(int): Size of array to check if stable temperature plateau is
            reached. Default = 5
        `sd`(float): Standard deviation, if sd of temperature array drops below 
            threshold value, function returns. Default = 0.02
        `verbose`(bool): If True it prints the temperature values every second
            while waiting for set temperature.
        """
        bufferT = deque(maxlen=array_size)
        counter = 0
        send_warning = False

        #Adapt if the thermistors change position in the yoctopuce sensor.
        if chamber.lower() == 'chamber1':
            sensor = 2
        elif chamber.lower() == 'chamber2':
            sensor = 3
        else:
            raise Exception('Invalid input for chamber: "{}". Choose "Chamber1" or "Chamber2".'.format(chamber))

        while True:
            tic = time.time()

            if 'YoctoThermistor' in self.devices:
                cur_temp = self.temp.get_temp()[sensor]
            elif 'TC720' in self.devices:
                cur_temp = self.TC720.get_temp()
            else:
                raise Exception('No temperature controller connected.')
            bufferT.append(cur_temp)
            
            if verbose == True:
                print('Current temperature: ', cur_temp, ' Standard deviation: ', np.std(bufferT))

            # Check if temp is within the error range of the target_temp
            if (target_temp-error) < cur_temp < (target_temp+error):
                if verbose == True:
                    print('{} within range of target temperature {}C with error {}C'.format(chamber, target_temp, error))
                if counter > array_size:
                    #Check if slope has plateaued by checking the standard deviation
                    if np.std(bufferT) < sd:
                        if verbose == True:
                            print('Temperature {} stable, slope minimal'.format(chamber))
                        #Send message that temperature has been reached, after an initial warning has been reached.
                        if send_warning == True:
                            correction_message = 'Target temperature or {}C has been reached. Ignore previous warning. Current temperature: {}C'.format(target_temp, cur_temp)

                            self.L.logger.info('    ' + correction_message)
                            self.push(short_message='Temperature false alarm',
                                      long_message=correction_message)                           
                        break

            #Notify the user if the temperature could not be reached.
            if counter >= 600 and (counter%300) == 0: #send 5 messages after 10min, every 5min.
                #Check if the Temperature Control Unit reports an error.
                if chamber.lower() == 'chamber1' and  ('ThermoCube1' in self.devices or 'Oasis1' in self.devices):
                    error_response = self.TC_1.check_error(verbose = True, raise_error = False)
                    tc = 'TC_1'
                elif chamber.lower() == 'chamber2' and   ('ThermoCube2' in self.devices or 'Oasis2' in self.devices):
                    error_response = self.TC_2.check_error(verbose = True, raise_error = False)
                    tc = 'TC_2'
                elif 'TC720' in self.devices:
                    error_response = self.TC720.check_error(set_idle = True, raise_exception = False)
                    tc = 'TC720'
                
                if error_response[0] == True:
                    error_message = 'NONE, No errors on {}'.format(tc)
                else:
                    error_message = error_response[1]           
                    #Make a function to switch off the system???         

                #Communicate the issue
                send_warning = True
                for i in range(5):
                    timeout_message = 'Target temperature of {}C could not be reached in 10 min, check system. Current temperature: {}C on {}, Errors on {}: {}'.format(target_temp, cur_temp, chamber, tc, error_message)
                    self.L.logger.info('    ' + timeout_message)
                    self.push(short_message='Temperature warning',
                               long_message= timeout_message)

            counter +=1        
            toc = time.time()
            execute_time = toc - tic
            if execute_time > 1:
                execute_time = 0.001
            # Check every second
            time.sleep(1-execute_time)
        self.L.logger.info('    {} within range of target temperature {}C, allowed error {}C. Reached in {} seconds after starting the waitTemp() function.'.format(chamber, target_temp, error, counter))

#=============================================================================
# Imaging functions
#=============================================================================

    def waitImaging(self, start_imaging_file_path):
        """
        Wait untill imaging is done. (value reverted to 0 in Start_Imaging_File)
        Checking interval is 60 seconds
        Input:
        `start_imaging_file_path` (str): Path to the start imaging file. This is a
            text file with a single integer. 0: No chamber ready for imaging, 1: 
            Chamber1 ready for imaging, 2: Chamber2 ready for imaging.
        
        """
        count = 0
        while True:
            try:
                with open(start_imaging_file_path, 'r') as start_imaging_file:
                    value = start_imaging_file.read()
                    if int(value) == 0:
                        print('Imaging of other chamber finished, waited {} minutes. (This time could be used to extend the hybridization with {} hours.)'.format(count, (round(count/60., 2))))
                        break
                if count == 0:
                    print('Waiting for imaging to finish...')
                count += 1
                self.secure_sleep(120, period=60, alarm_room_temperature=35, temperature_range=5, number_of_messages=10)
            except Exception as e:
                print ("Error, Unable to open Start_Imaging_File with path: {}, Make sure the file is present at this location or correct the path. Error message: {}".format(start_imaging_file_path, e))
                
    def startImaging(self, chamber, start_imaging_file_path):
        """
        Start the imaging of chamber 1 or 2, by notifying the Nikon software
        Input:
        `chamber`(str): "Chamber1" or "Chamber2"
        `start_imaging_file_path` (str): Path to the start imaging file. This is a
            text file with a single integer. 0: No chamber ready for imaging, 1: 
            Chamber1 ready for imaging, 2: Chamber2 ready for imaging.
        
        """
        if chamber.lower() != 'chamber1' and chamber.lower() != 'chamber2':
            raise ValueError('Invalid input, choose "Chamber1" or "Chamber2".')
        if chamber.lower() == 'chamber1':
            start_val = 1
        elif chamber.lower() == 'chamber2':
            start_val = 2    

        #Wait until current imaging is done
        self.waitImaging(start_imaging_file_path)

        #Write new value to Start_Imaging_File to start the imaging
        tried = 0
        while True:
            try:  
                with open(start_imaging_file_path, 'w') as start_imaging_file:
                    start_imaging_file.write(str(start_val))
                break
            except Exception as e:
                time.sleep(0.551)
                print ("Error, Unable to open Start_Imaging_File with path: {}, Make sure the file is present at this location or correct the path. Error message: {}".format(start_imaging_file_path, e))
                tried +=1
                if tried >200:
                    raise Exception('Could not write to: {} and start the imaging. Please check if path and file are correct.'.format(start_imaging_file_path))

#=============================================================================
# Error checking
#=============================================================================

    def check_error_TC1(self, verbose=False):
        'Check errors on ThermoCube1.'
        if self.Machines['ThermoCube1'] == 1 or self.Machines['Oasis1'] == 1:
            try:
                TC_1_error = self.TC_1.check_error(verbose=False, raise_error=False)
            except Exception as e:
                TC_1_error = [False, 'TC_1 POSSIBLY NOT CONNECTED, did you switch it off? If yes, remove it from the active machines in the datafile. Error: {}'.format(e)]
            if verbose:
                print('    TC1: {}'.format(TC_1_error))
            return TC_1_error
        else:
            return None

    def check_error_TC2(self, verbose=False):
        'Check errors on ThermoCube2.'
        if self.Machines['ThermoCube2'] == 1 or self.Machines['Oasis2'] == 1:
            try:
                TC_2_error = self.TC_2.check_error(verbose=False, raise_error=False)
            except Exception as e:
                TC_2_error = [False, 'TC_2 POSSIBLY NOT CONNECTED, did you switch it off? If yes, remove it from the active machines in the datafile. Error: {}'.format(e)]
            if verbose:
                print('    TC2: {}'.format(TC_2_error))
            return TC_2_error
        else:
            return None

    def check_error_yoctopuce(self, alarm_room_temperature=35, temperature_range=5, verbose=False):
        'Check temperatures ycotupuce thermistor.'
        if self.Machines['YoctoThermistor'] == 1:
            try:
                current_temp = self.temp.get_temp()
                room_temp = current_temp[1]
                C1_temp = current_temp[2]
                C2_temp = current_temp[3]
                if room_temp > alarm_room_temperature:
                    roomtemp_yocto_error = [False, 'CURRENT ROOM TEMPERATURE {}C'.format(room_temp)]
                else:
                    roomtemp_yocto_error = [True, 'CURRENT ROOM TEMPERATURE {}C'.format(room_temp)]

                #Check if chamber 1 is far off from the target temperature
                C1_temprature_error = None
                if self.target_temperature[0] != None:
                    if C1_temp > (self.target_temperature[0] + temperature_range) or C1_temp < (self.target_temperature[0] - temperature_range):
                        C1_temprature_error = [False, 'Chamber1 is {}C, and should be at {}C'.format(C1_temp, self.target_temperature[0])]
                        if verbose:
                            print('    C1: {}'.format(C1_temprature_error))

                #Check if chamber 2 is far off from the target temperature
                C2_temprature_error = None
                if self.target_temperature[1] != None:
                    if C2_temp > (self.target_temperature[1] + temperature_range) or C2_temp < (self.target_temperature[1] - temperature_range):
                        C2_temprature_error = [False, 'Chamber2 is {}C, and should be at {}C'.format(C2_temp, self.target_temperature[1])]
                        if verbose:
                            print('    C2: {}'.format(C2_temprature_error))
                        
            except Exception as e:
                temperature_error = [False, 'Could not read temperature from Yocto Thermistor, check connection. Error: {}'.format(e)]
                C1_temperature_error = None
                C2_temprature_error = None
                room_temp, C1_temp, C2_temp = None, None, None
            if verbose:
                print('    Temperature: {}'.format(temperature_error))
            
            return roomtemp_yocto_error, C1_temperature_error, C2_temprature_error, [room_temp, C1_temp, C2_temp]
        else:
            return None, None, None, [None, None, None]

    def check_error_TC720(self, alarm_room_temperature=35, temperature_range=5, verbose=False):
        'Check errors on TC720'
        if self.Machines['TC720'] == 1:
            try:
                #Check for errors
                TC720_error = self.TC720.check_error(raise_exception=False)
                #Check temperature readings
                C1_temp = self.TC720.get_temp()
                C2_temp = '-'
                room_temp = self.TC720.get_temp2()

                #Check if chamber 1 is far off from the target temperature
                TC720_temperature_error = None
                if self.target_temperature[0] != None:
                    if C1_temp > (self.target_temperature[0] + temperature_range) or C1_temp < (self.target_temperature[0] - temperature_range):
                        TC720_temperature_error = [False, 'Chamber is {}C, and should be at {}C'.format(C1_temp, self.target_temperature[0])]
                        if verbose:
                            print('    TC720: {}'.format(TC720_temperature_error))

                #Check room temperature
                roomtemp_TC720_error = None
                if room_temp > alarm_room_temperature:
                    roomtemp_TC720_error = [False, 'CURRENT ROOM TEMPERATURE {}C'.format(room_temp)]

            except Exception as e:
                TC720_error = [False, 'TC720 POSSIBLY NOT CONNECTED, did you switch it off? If yes, remove it from the active machines in the datafile. Error: {}'.format(e)]
                TC720_temperature_error = None
                roomtemp_TC720_error = None
                room_temp, C1_temp, C2_temp = None, None, None
            if verbose:
                print('    TC720: {}'.format(TC720_error))

            return TC720_error, TC720_temperature_error, roomtemp_TC720_error, [room_temp, C1_temp, C2_temp]
        else:
            return None, None, None, [None, None, None]

    def check_error_disk(self):
        """
        Check disk usage to warn user if it is too high.
        """
        drive = self.imaging_output_folder[:2] #Only on windows??
        total, used, free = shutil.disk_usage(drive)
        if (used / total) > self.Alert_volume['Disk']:
            return [False, f'Disk usage high: {used // (2**30)}GB used, {free // (2**30)}GB free, of total {total // (2**30)}GB']
        else:
            return [True, f'Disk usage: {used // (2**30)}GB used, {free // (2**30)}GB free, of total {total // (2**30)}GB']

    def check_error(self, alarm_room_temperature=35, temperature_range=5, number_of_messages=10):
        """
        Checks errors on all connected machines.
        Input:
        `alarm_room_temperature(int): Degree Celsius that is the threshold, 
            above which the program should send an alarm. Default 35 C.
        `temperature_range`(int/float): Degrees the actual chamber temperature is
            allowed to be off from the target temperature. Default 5C.
        `number_of_messages`(int): Number of messages that are sent every period 
            that an error is detected. Default to 10. This is a lot but it will 
            hopefully wake up the user.
        """
        #Update parameters
        self.updateExperimentalParameters(self.db_path, ignore_flags=True)

        #Check for errors in all connected machines
        TC_1_error = self.check_error_TC1()
        TC_2_error = self.check_error_TC2()
        roomtemp_yoct_error, C1_temprature_error, C2_temprature_error, t1 = self.check_error_yoctopuce(alarm_room_temperature, temperature_range)
        TC720_error, TC720_temperature_error, roomtemp_TC720_error, t2 = self.check_error_TC720(alarm_room_temperature, temperature_range)
        disk_error = self.check_error_disk()

        #Get the temperature readings of the connected machines
        if t1 == [None, None, None]:
            room_temp, C1_temp, C2_temp = t2
        elif t2 == [None, None, None]:
            room_temp, C1_temp, C2_temp = t1

        #Gather issues
        errors = []
        ##### Add new error codes here if you add machines:
        for report in [TC_1_error, TC_2_error, roomtemp_yoct_error, C1_temprature_error, C2_temprature_error, 
                       TC720_error, TC720_temperature_error, roomtemp_TC720_error, disk_error]:
            if report != None:
                if report[0] == False:
                    errors.append(report)
                    self.L.logger.warning('{}'.format(report[1]))
                            
        #Warn user by sending a number of messages
        if errors != []:
            self.found_error = True
            
            #If only the disk has an error do not send a million messages
            if len(errors) == 1 and errors[0][1].startswith('Disk usage high'):
                self.push(short_message = 'ERROR on {}'.format(self.Parameters['Machine']),
                            long_message = '\n\nWarning: '.join(er[1] for er in errors if er[0]==False))
            else:
                for i in range(number_of_messages):
                    self.push(short_message = 'ERROR on {}'.format(self.Parameters['Machine']),
                                long_message = '\n\nWarning: '.join(er[1] for er in errors if er[0]==False))
        else:
            if self.found_error == True:
                self.L.logger.info('Issue resolved, no errors detected anymore.')
                self.push(short_message = 'Resolved error',
                         long_message = '''No errors detected anymore, it resolved itself. Check system if needed, some devices may have been set to idle.\n Current temperatures: Room: {}C, Chamber1: {}C, Chamber2: {}C. Allowed difference: {}C'''.format(room_temp, C1_temp, C2_temp,temperature_range))
                self.found_error = False

    def secure_sleep(self, sec, period=120, alarm_room_temperature=35, temperature_range=5, number_of_messages=10, verbose=False):
        """
        Function that sleeps an X amount of time in total but it wakes up every
        period to check if there are errors reported on one of the machines. It
        warns the user by sending messages if there is an error. 
        Input:
        `sec`(int/float): Number of seconds the program needs to sleep.
        `period`(int): The length of every cycle. Default 120 seconds.
        `alarm_room_temperature(int): Degree Celsius that is the threshold, 
            above which the program should send an alarm. Default 35 C.
        `temperature_range`(int/float): Degrees the actual chamber temperature is
            allowed to be off from the target temperature. Default 5C.
        `number_of_messages`(int): Number of messages that are sent every period 
            that an error is detected. Default to 10. This is a lot but it will 
            hopefully wake up the user. 
        `Verbose`(bool): Prints status and remaining wait time.
            
        If you change the system machines you can add and remove machines that 
        need to be checked by this function. 
        Adding a machine:
        1) Add 'new-machine_error' and another None to the line initiating the 
        variables.
        2) Add the code that check for the error. It is advised to add a line 
        that tries to check for errors and an except in case no connection could
        be made. Then set the 'new-machine_error' to a list of: [bool, "error 
        message"]. False means an error. The error message will be send to 
        the user.
        3) Add the error codes in the last list where they are checked if they 
        are False and an error needs to be reported to the user.
        
        """ 
        current_temp = ''
        
        #Loop through the wait time.
        while sec > 0:
            if verbose:
                print('Secure sleep function: {} seconds remaining'.format(sec))
            #Just sleep if wait time is less than 30 seconds
            if sec < 30:
                if verbose:
                    print('    Less than 30 seconds to sleep, will return after {} seconds'.format(sec))
                if sec > 0:
                    time.sleep(sec)
                    return
                else:
                    return

            #Secure sleep if sleep time is long
            else:
                tic = time.time()
                
                #Perform error checks on system modules
                self.check_error(alarm_room_temperature, temperature_range, number_of_messages)

                #Sleep the rest of the ime
                toc = time.time()
                execute_time = toc - tic
                remain_sleep = period - execute_time
                
                if remain_sleep>0:
                    time.sleep(remain_sleep)
                else:
                    sec += remain_sleep

                sec -= period

#=============================================================================
# Scheduler to perform an experiment
#=============================================================================

    def scheduler(self, function1, function2, remove_experiment=True, log_info_file=True,
                  current_1=None, current_2=None, start_with=None ):
        """
        Scheduler that schedules and performs the experiments on the ROBOFISH
        system depending on the info provided in the info file. The experiment
        number in the database is the que to start the experiment for the 
        scheduler. Update the info file using the ROBOFISH_user_program, enter
        an experiment and start the scheduler.
        The scheduler runs indenfinately and can be given multiple sequential 
        experiments. Keyboard interupt to stop it. To run individual experiments
        set remove_experiment to False and the scheduler will go into save_sleep
        when the experiment is done. 
        Input:
        `function1`(function): Function for the FIRST part of the experiment.
            Usually the first round of the experiment is different because no
            stripping needs to be performed or there are other differences. 
            The function should take the following input: 
            chamber(str) = 'Chamber1' or 'Chamber2'
            cycle(int) = Cycle number
        `fucntion2`(function): Function for the REPEAT part of the experiment.
            The repeat part is the part of the experiment that keeps cycling
            untill all rounds are performed.
            The function should take the following input: 
            chamber(str) = 'Chamber1' or 'Chamber2'
            cycle(int) = Cycle number
        `remove_experiment`(bool): If you are running only one experiment 
            at a time and want to re-use the data in the info file, set 
            to False and the scheduler will not remove all data when the 
            experiment is completed and enter a 2 week long secure_sleep. 
            ONLY USE WHEN RUNNING ONLY ONE EXPERIMENT WITH ONE CHAMBER!!
            Practical when experiments are standardized and only one
            experiment is run at a time.
        `log_info_file`(bool): If true it logs all info in the info file. 
        Restart functionalities:
        Use these parameters when you had to restart the scheduler.
        `current_1`(int): Current cycle of Chamber1. Use this if you want to
            start from a different cycle, for instance when you needed to 
            restart the scheduler. IT WILL GO TO THE NEXT ROUND! 
            So if you want to do round 10, pass 9 to current_1.
        `current_2`(int): Current cycle of Chamber2. Use this if you want to
            start from a different cycle, for instance when you needed to 
            restart the scheduler. IT WILL GO TO THE NEXT ROUND! 
            So if you want to do round 10, pass 9 to current_2.
        `start_with`(int): Number of chamber to start with first. So 1 for
            Chamber1 and 2 for Chamber2.
        """

        #######################################################
        # Functions
        #######################################################

        def get_targets(code):
            """
            Retrieve the targets of a specific chamber and hybridization round.
            Input:
            `code`(str): Identification code for the chamber and hybridization round.
                Example: 'C2H06' for Chamber 2, Hybridization round 6.
            Retruns:
            Dictionary 
    
            """
            try:
                for i in self.Targets:
                    if i['Code'] == code:
                        return i
            except Exception as e:
                #Print error if code could not be found
                print('Could not retrieve target information for {}. Error: {}'.format(code, e))

        def create_info_dict(cur_exp, cur_stain, log=False):
            """
            Create and saves a information dictionary about the completed 
            hybridization round. Should be saved in the output folder of the imaging.
            Input:
            `cur_exp`(dict): Dictionary about the current cycle of the experiment.
            `cur_stain`(int): Number of the chamber that is stained
            `log`(bool): Put the info also in the log file
    
            """
            #Construct the round code of this chamber and hybridization round.
            round_code = 'C{}H{}'.format(cur_stain, str(cur_exp['Current_cycle_{}'.format(cur_stain)]).zfill(2))
    
            #Get the stained targets
            target_dict = get_targets(round_code)
    
            #Get the parameters of this experiment
            info_dict = {
                'round_code' : round_code,
                'experiment_name': cur_exp['EXP_name_{}'.format(cur_stain)],
                'Description': self.Parameters['Description_{}'.format(cur_stain)],
                'Protocols_io': self.Parameters['Protocols_io_{}'.format(cur_stain)],
                'chamber': 'chamber{}'.format(cur_stain),
                'Machine': self.Parameters['Machine'],
                'Operator': self.Parameters['Operator'],
                'Timestamp_robofish': time.strftime("%Y-%m-%d %H-%M-%S"),
                'hybridization_fname': 'Unknown-at-dict-generation-time',
                'hybridization_number': int(cur_exp['Current_cycle_{}'.format(cur_stain)]),
                'Hyb_time_A': self.Parameters['Hyb_time_{}_A'.format(cur_stain)],
                'Hyb_time_B': self.Parameters['Hyb_time_{}_B'.format(cur_stain)],
                'Hyb_time_C': self.Parameters['Hyb_time_{}_C'.format(cur_stain)],
                'Hybmix_volume': self.Parameters['Hybmix_volume'],
                'Imaging_temperature': self.Parameters['Imaging_temperature'],
                'Fluidic_Program': self.Parameters['Program'],
                'Readout_temperature': self.Parameters['Readout_temperature'],
                'Staining_temperature': self.Parameters['Staining_temperature'],
                'Start_date': self.Parameters['Start_date_{}'.format(cur_stain)],
                'Target_cycles': self.Parameters['Target_cycles_{}'.format(cur_stain)],
                'Species': self.Parameters['Species_{}'.format(cur_stain)],
                'Sample': self.Parameters['Sample_{}'.format(cur_stain)],
                'Strain': self.Parameters['Strain_{}'.format(cur_stain)],
                'Age': self.Parameters['Age_{}'.format(cur_stain)],
                'Tissue': self.Parameters['Tissue_{}'.format(cur_stain)],
                'Orientation': self.Parameters['Orientation_{}'.format(cur_stain)],
                'RegionImaged': self.Parameters['RegionImaged_{}'.format(cur_stain)],
                'SectionID': self.Parameters['SectionID_{}'.format(cur_stain)],
                'Position': self.Parameters['Position_{}'.format(cur_stain)],
                'Experiment_type': self.Parameters['Experiment_type_{}'.format(cur_stain)],
                'Chemistry': self.Parameters['Chemistry_{}'.format(cur_stain)],
                'Probes_FASTA': {'DAPI': self.Parameters['Probes_FASTA_DAPI_{}'.format(cur_stain)],
                                'Atto425': self.Parameters['Probes_FASTA_Atto425_{}'.format(cur_stain)],
                                'FITC': self.Parameters['Probes_FASTA_FITC_{}'.format(cur_stain)],
                                'Cy3': self.Parameters['Probes_FASTA_Cy3_{}'.format(cur_stain)],
                                'TxRed': self.Parameters['Probes_FASTA_TxRed_{}'.format(cur_stain)],
                                'Cy5': self.Parameters['Probes_FASTA_Cy5_{}'.format(cur_stain)],
                                'Cy7': self.Parameters['Probes_FASTA_Cy7_{}'.format(cur_stain)],
                                'Europium': self.Parameters['Probes_FASTA_Europium_{}'.format(cur_stain)]},
                'Barcode': self.Parameters['Barcode_{}'.format(cur_stain)],
                'Barcode_length': self.Parameters['Barcode_length_{}'.format(cur_stain)],
                'Codebooks' : {'DAPI': self.Parameters['Codebook_DAPI_{}'.format(cur_stain)],
                               'Atto425': self.Parameters['Codebook_Atto425_{}'.format(cur_stain)],
                               'FITC': self.Parameters['Codebook_FITC_{}'.format(cur_stain)],
                               'Cy3': self.Parameters['Codebook_Cy3_{}'.format(cur_stain)],
                               'TxRed': self.Parameters['Codebook_TxRed_{}'.format(cur_stain)],
                               'Cy5': self.Parameters['Codebook_Cy5_{}'.format(cur_stain)],
                               'Cy7': self.Parameters['Codebook_Cy7_{}'.format(cur_stain)],
                               'Europium': self.Parameters['Codebook_Europium_{}'.format(cur_stain)]},
                'Multicolor_barcode': self.Parameters['Multicolor_barcode_{}'.format(cur_stain)],
                'Stitching_type': self.Parameters['Stitching_type_{}'.format(cur_stain)],
                'StitchingChannel': self.Parameters['StitchingChannel_{}'.format(cur_stain)],
                'Overlapping_percentage': self.Parameters['Overlapping_percentage_{}'.format(cur_stain)],
                'channels': target_dict,
                'roi': self.Parameters['roi_{}'.format(cur_stain)],
                'Pipeline': self.Parameters['Pipeline_{}'.format(cur_stain)],
                'system_log': self.L.logger_path
                }
            if self.Machines['YoctoThermistor'] == 1:
                info_dict['temperature_log'] = self.temp.temp_log_filename

            if log == True:
                self.L.logger.info('\nCycle parameters:\n'+''.join(['{}: {}\n'.format(i, info_dict[i]) for i in info_dict]))

            info_file_name = 'TEMPORARY_{}_{}'.format( cur_exp['EXP_name_{}'.format(cur_stain)], round_code)
            pickle.dump(info_dict, open('{}\\{}.pkl'.format(self.imaging_output_folder, info_file_name), 'wb'))

        def updateCurExp():
            """
            Updates the internal dictionaries from the SQLite3 database and then updates
            the cur_exp dictionary that the FISH2_program uses to run experiments.
    
            """
            self.updateExperimentalParameters(self.db_path, ignore_flags=True)
            for k in cur_exp:
                if k in self.Parameters:
                    cur_exp[k] = self.Parameters[k]

        
        def create_config_file(cur_stain, other):
            """
            Make experiment configuration file.
            Input:
            `cur_stain`(int): Number of the chamber currently staining.
            `other`(int): Number of the other chamber
            """
            fname = '{}\\{}_config.yaml'.format(self.imaging_output_folder, cur_exp['EXP_name_{}'.format(cur_stain)])
            #params = perif.getFISHSystemMetadata('FISH_System_datafile.yaml', table='Parameters')
            #Select only current experiment.
            params = {}
            codebooks = {}
            probe_sets = {}
            for k,i in self.Parameters.items():
                if k.endswith('_{}'.format(cur_stain)):

                    if k.startswith('Codebook_'):
                        k_short = k[:-2]
                        codebooks[k_short] = i
                    elif k.startswith('Probes_FASTA_'):
                        k_short = k[:-2]
                        probe_sets[k_short] = i
                    else:
                        k_short = k[:-2]
                        params[k_short] = i

                #Parameters without camber specific ending
                if not k.endswith('_{}'.format(other)) and not k.endswith('_{}'.format(cur_stain)):
                    params[k] = i

            params['Codebooks'] = codebooks
            params['Probes_FASTA'] = probe_sets

            #Dump params in new .yaml file.
            perif.yamlMake(fname, params)
            self.L.logger.info('Experiment configuration file created: {}'.format(fname))

        #######################################################
        # Scheduler
        #######################################################

        #Information on the current state of the experiment
        cur_exp = {
            'EXP_name_1': 'None',
            'EXP_name_2': 'None',
            'Location_EXP_1': 'None',
            'Location_EXP_2': 'None',
            'Target_cycles_1': 'None',
            'Target_cycles_2': 'None',     
            'Current_cycle_1': 'None',
            'Current_cycle_2': 'None',
            'Current_part_1': 'None',
            'Current_part_2': 'None',
            'Current_staining' : 'None'}
        updateCurExp()

        timing = {
            'tic_1': None,
            'tic_2': None}

        #check exp number to see if there are one or two experiments to run.
        if cur_exp['EXP_name_1'] != 'None' and cur_exp['EXP_name_2'] != 'None':
            cur_exp['Current_staining'] = 1
        elif cur_exp['EXP_name_1'] != 'None':
            cur_exp['Current_staining'] = 1
        elif cur_exp['EXP_name_2'] != 'None':
            cur_exp['Current_staining'] = 2
        self.L.logger.info('Start new experiment, start with chamber {}.'.format(cur_exp['Current_staining']))    


        # Start from different cycle defined by user
        #It will go to the next cycle, so if you enter 10 it will do round 11
        #Current cycle of Chamber 1:
        if current_1 != None:
            cur_exp['Current_cycle_1'] = current_1
            self.L.logger.info('Continuing experiment in Chamber1 from cycle: {}, it will now perform the next cycle, cycle: {}'.format(current_1, current_1+1))
        #Current cycle of Chamber 2:
        if current_2 != None:
            cur_exp['Current_cycle_2'] = current_2
            self.L.logger.info('Continuing experiment in Chamber2 from cycle: {}, it will now perform the next cycle, cycle: {}'.format(current_2, current_2+1))
        #Chamber to stain:
        if start_with != None:
            cur_exp['Current_staining'] = start_with
            self.L.logger.info('Starting with Chamber {}'.format(start_with))
    
        cur_stain = cur_exp['Current_staining']
        other = -cur_stain + 3  #Reverse 1-->2   2-->1

        # Infinite cycle to perform all experiments. Can be left on for multiple experiments.
        while True:

        #Pause or exit if there are no experiments to perform
            updateCurExp()
            if cur_exp['EXP_name_1'] == 'None' and cur_exp['EXP_name_2'] == 'None':
                print('No experiments detected to perform.')
                print('You can resume after preparing a new experiment or stop the program.')
                while True:
                    resume = input('\nEnter "Resume" or "Stop" ')
                    if resume.lower() == 'resume' or resume.lower() == 'stop':
                        break
                    else:
                        print('Invalid input: {}. Choose: "Resume" or "Stop"'.format(resume))
        
                if resume.lower() == 'resume':
                    input('\nPress Enter when ready to resume staining and imaging...')
                    updateCurExp()
                    #check exp number to see if there are one or two experiments to run.
                    if cur_exp['EXP_name_1'] != 'None' and cur_exp['EXP_name_2'] != 'None':
                        cur_exp['Current_staining'] = 1
                    elif cur_exp['EXP_name_1'] != 'None':
                        cur_exp['Current_staining'] = 1
                    elif cur_exp['EXP_name_2'] != 'None':
                        cur_exp['Current_staining'] = 2
                    self.L.logger.info('Start new experiment, start with chamber {}.'.format(cur_exp['Current_staining']))    

                    cur_stain = cur_exp['Current_staining']
                    other = -cur_stain + 3  #Reverse 1-->2   2-->1
            
                elif resume.lower() == 'stop':
                    self.L.logger.info('FISH2 program stopped by user')
                    break
    
        #Does Current_stain exist:
            updateCurExp()
            #No, Current_stain does not exist, Only Other is being stained and imaged:
            if cur_exp['EXP_name_{}'.format(cur_stain)] == 'None':
                self.L.logger.info('No new experiment detected in Chamber{}, waiting untill imaging of Chamber{} is finished'.format(cur_stain, other))
                print('')
                #Wait untill Other is finished with imaging
                self.waitImaging(self.start_imaging_file_path)
                self.L.logger.info('Imaging Experiment: {} Cycle: {} done.\n'.format(cur_exp['EXP_name_{}'.format(other)], cur_exp['Current_cycle_{}'.format(other)]))
                print('')
                #FLIP
                cur_exp['Current_staining'] = other
                cur_stain = cur_exp['Current_staining']
                other = -cur_stain + 3  #Reverse 1-->2   2-->1
    
            #Yes, Current_stain exists:
            else:
            #Is Current_stain a new experiment:
                #Yes, new experiment:
                if cur_exp['Current_cycle_{}'.format(cur_stain)] == 'None':
                    cur_exp['Current_cycle_{}'.format(cur_stain)] = 1
                    #Logging
                    self.L.logger.info('_____')
                    self.L.logger.info('STARTING {}, CYCLE: {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)], cur_exp['Current_cycle_{}'.format(cur_stain)]))
                    #Make config file
                    create_config_file(cur_stain, other)
                    #Record start time
                    timing['tic_{}'.format(cur_stain)] = datetime.now()
                    print('')
                    #################################################################
                    #Perform First Part of experiment
                    function1('Chamber{}'.format(cur_stain), cur_exp['Current_cycle_{}'.format(cur_stain)])
                    #Write info file for this round
                    create_info_dict(cur_exp, cur_stain, log=log_info_file)
        
                #No, old experiment:
                else:
                    cur_exp['Current_cycle_{}'.format(cur_stain)] += 1
                    #Logging
                    self.L.logger.info(' ')
                    self.L.logger.info('_____')
                    self.L.logger.info('STARTING {}, CYCLE: {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)], cur_exp['Current_cycle_{}'.format(cur_stain)]))
                    #Calculate total experiment time
                    if timing['tic_{}'.format(cur_stain)] != None:
                        round_time = datetime.now() - timing['tic_{}'.format(cur_stain)]
                        #Rounds left including current round. 
                        rounds_left = cur_exp['Target_cycles_{}'.format(cur_stain)] - (cur_exp['Current_cycle_{}'.format(cur_stain)] -1)
                        finish_time = datetime.now() + (rounds_left * timedelta(days=round_time.days, seconds=round_time.seconds))
                        print('Expected finish time of cycle {} in Chamber{}: {}'.format(cur_exp['Current_cycle_{}'.format(cur_stain)], cur_stain, datetime.now()+round_time))
                        print('Expected finish time for full experiment in Chamber{}: {}'.format(cur_stain, finish_time))
                    timing['tic_{}'.format(cur_stain)] = datetime.now()
                    print('')
                    #################################################################
                    #Perform Repeat Part of experiment
                    function2('Chamber{}'.format(cur_stain), cur_exp['Current_cycle_{}'.format(cur_stain)])
                    #Update
                    self.updateExperimentalParameters(self.db_path, ignore_flags=False)
                    #Write info file for this round
                    create_info_dict(cur_exp, cur_stain, log=log_info_file)
        
                #Wrappup Current_stain? If all stainings are done, but the last imaging has still to be performed.
                #Yes, wrapup:
                updateCurExp()
                if cur_exp['Current_cycle_{}'.format(cur_stain)] >= cur_exp['Target_cycles_{}'.format(cur_stain)]:
                    #Start the last imaging
                    self.L.logger.info('Start Imaging of Experiment: {} Cycle: {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)], cur_exp['Current_cycle_{}'.format(cur_stain)]))
                    self.startImaging('Chamber{}'.format(cur_stain), self.start_imaging_file_path)
                    #Logging
                    self.L.logger.info('FINISHED {}, Removing from database and FISH_System_datafile.yalm'.format(cur_exp['EXP_name_{}'.format(cur_stain)]))
                    #Log the targets
                    self.L.logger.info('Targets:\n'+''.join('{}\n'.format(i) for i in self.Targets))
                    wrappup = True
                    if remove_experiment == True:    
                        #Notify user
                        short_message = '{} Finished'.format(cur_exp['EXP_name_{}'.format(cur_stain)])
                        long_message = '''Full experiment completed. 
                        All experimental info will be removed from database and FISH_Sytem_datafile.yaml\n
                        You can now add a new EXP_{} to the FISH_Sytem_datafile.yaml, via the user program.'''.format(cur_stain)
                        self.push(short_message, long_message)
                        print(short_message + '\n' + long_message + '\n')
                        #Remove experiment from database and FISH_System_datafile
                        perif.removeExperiment(self.db_path, cur_exp['EXP_name_{}'.format(cur_stain)])
                        cur_exp['Current_cycle_{}'.format(cur_stain)] = 0
                        cur_exp['Current_part_{}'.format(cur_stain)] = 'None' 
                    else:
                        #Notify user
                        short_message = '{} Finished'.format(cur_exp['EXP_name_{}'.format(cur_stain)])
                        long_message = '''Full experiment completed. 
                        Ready to start a new experiment. Starting secure sleep'''.format(cur_stain)
                        self.push(short_message, long_message)
                        print(short_message + '\n' + long_message + '\n')
                        self.secure_sleep(14*24*60*60)

                #Not done yet, more cycles to go:
                else:
                    wrappup = False

                #Check new experiment flag, For new experiment Other
                #Give user oportunity to prepare imaging Other.
                if perif.returnDictDB(self.db_path, 'Flags')[0]['New_EXP_flag_{}'.format(other)] == 1:
                    short_messgage = 'Prepare imaging of {}'.format(cur_exp['EXP_name_{}'.format(other)])
                    long_message = '''Reply with "Pause" if you want to prepare the imaging now (set ROI, focusing etc.).\n
                    There will be another oportunity after the imaging of {}\n
                    Reply: "Pause", reply time 10min'''.format(cur_exp['EXP_name_{}'.format(cur_stain)])
                    self.push(short_message, long_message)
                    print(short_message + '\n' + long_message + '\n')
                    print('\nYou can now prepare the imaging of {}'.format(cur_exp['EXP_name_{}'.format(other)]))

                    #10 minutes reply time
                    time.sleep(60 * 10) 

                    if perif.get_push(self.Parameters['Operator']).lower() == 'pause':
                        short_message = 'Experiment paused'
                        long_message = 'Pause untill user input. Prepare imaging now (set ROI, focusing etc.).'
                        self.push(short_message, long_message)
                        print('\nExperiment paused before imaging {} so that user can prepare the imaging of {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)], cur_exp['EXP_name_{}'.format(other)]))
                        input('Press Enter to continue when ready...')
                        perif.removeFlagDB(self.db_path, 'New_EXP_flag_{}'.format(other))
                        updateCurExp()
                    else:
                        short_messgage = 'Continuing'
                        long_message = 'Experiment not paused, continuing with imaging of {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)])
                        self.push(short_message, long_message)
                        print(short_message + '\n' + long_message + '\n')
                        updateCurExp()

                #Before imaging Current_stain check if imaging has been set for Current_stain
                if perif.returnDictDB(self.db_path, 'Flags')[0]['New_EXP_flag_{}'.format(cur_stain)] == 1:
                    while True:
                        short_messgage = 'Prepare imaging of {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)])
                        long_message = '''Prepare imaging of {} (set ROI, focusing etc.).\n
                        If you already did this reply with: "Continue". Relpy time 10min.'''.format(cur_exp['EXP_name_{}'.format(cur_stain)])
                        self.push(short_message, long_message)
                        print(short_message + '\n' + long_message + '\n')
                        print('If you can not sent push messages: Remove "New_EXP_flag_{}" from the user program'.format(cur_stain))
                        #10 minutes reply time
                        time.sleep(60 * 10)

                        if perif.get_push(self.Parameters['Operator']).lower() == 'continue' or perif.returnDictDB(self.db_path, 'Flags')[0]['New_EXP_flag_{}'.format(cur_stain)] == 0:
                            updateCurExp()
                            break
             
                #Start imaging of Current_Stain, will wait untill the imaging of the other chamber has finished.
                self.L.logger.info('Start Imaging of Experiment: {} Cycle: {}'.format(cur_exp['EXP_name_{}'.format(cur_stain)], cur_exp['Current_cycle_{}'.format(cur_stain)]))
                self.startImaging('Chamber{}'.format(cur_stain), self.start_imaging_file_path)

                #FLIP the conditions of the 2 chambers
                cur_exp['Current_staining'] = other
                cur_stain = cur_exp['Current_staining']
                other = -cur_stain + 3  #Reverse 1-->2  >