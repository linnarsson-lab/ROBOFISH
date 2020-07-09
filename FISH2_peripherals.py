#Python 3 package to manage Peripheral functions of FISH system 2.
#Date: 14 October 2016
#Author: Lars E. Borm
#E-mail: lars.borm@ki.se or larsborm@gmail.com
#Python version: 3.5.1

#Used by both the User program and the Excecute FISH program.

## CONTENT ##
    # FISH_logger class
    # Sending messages using Pushbullet
    # Managing .yaml files
    # Managing sqlite3 database
    # Transport data from .yaml datafile to database
    # User add new data to .yaml datafile and transport to database
    # Remove experiment from .yaml datafile and database

#=============================================================================
# Dependencies       
#=============================================================================

#Logger
import logging
import time
import os
#Sending messages
from pushbullet import Pushbullet
#handle .yaml files
import yaml
#Use ruamel.yaml to dynamically update files (https://yaml.readthedocs.io)
import ruamel.yaml
from ruamel.yaml.util import load_yaml_guess_indent
import collections
#Database
import sqlite3
#User update
from tkinter import *

#=============================================================================
# System specific input, change if needed.      
#=============================================================================

#File indicating if a sample can be imaged.
#If not present please make a text file with a single "0" in it.
#Put the full path to the folder and file here:
start_imaging_file_path = "C:\\Users\\Nikon\\Desktop\\FISH_Sys_2\\FISH_database\\Start_Imaging_File.txt"

#=============================================================================
# Logger     
#=============================================================================

class FISH_logger():
    # Based on the code of Josina A. van Lunteren (2016)
    """Logger for FISH System 2"""
    
    def __init__(self, verbose = True, folder_name = 'log_files', system_name =
                'ROBOFISH', log_level = logging.INFO, console_level = 
                logging.INFO):
        """
        Input:
        `verbose`(bool): If True, prints that is made the logger.
        `folder_name` (str): Folder name (not path) to store the log files.
        `system_name`(str): Name of system used
        `log_level`(logging.___): level to logg, default "logging.DEBUG"
        `console_level`(logging.___): level to print, default "logging.INFO"
        
        """ 
        # Redirect warnings to logger
        logging.captureWarnings(True)

        # Create logger
        self.logger = logging.getLogger()
        self.logger.setLevel(log_level)

        formatter_file = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        formatter_con = logging.Formatter('%(message)s')
        log_path = folder_name

        # Create file
        try:
                os.stat(log_path)
        except:
                os.mkdir(log_path)
                if os.name == 'posix':
                    os.chmod(log_path,0o777) #LINUX UNIX specific!

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        dateTag = time.strftime("%Y-%m-%d %H-%M-%S")
        self.logger_path = '{}/{}_{}.log'.format(log_path, dateTag, system_name)
        self.fh = logging.FileHandler(self.logger_path, mode = 'w')
        if verbose == True:
            print('Logger created. path: ', self.logger_path)

        # Set logger properties
        self.fh.setLevel(log_level)
        self.fh.setFormatter(formatter_file)
        self.logger.addHandler(self.fh)

        # To print the logging to console
        ch = logging.StreamHandler()
        ch.setLevel(console_level)
        ch.setFormatter(formatter_con)
        self.logger.addHandler(ch)


#=============================================================================
# Sending / receiving Push messages      
#=============================================================================

# Prepare and send Push notification via Pushbullet
# Using https://www.pushbullet.com/ together with the python interface https://github.com/randomchars/pushbullet.py

def send_push(pushbullet_address_book, operator = 'lars', short_message = '', long_message = ''):
    """
    Send a push messages to the operator using the Pushbullet service.
    Input:
    `pushbullet_address_book`(dict): Dictionary with the operator(s) and the
        access tokens..
    `operator`(str): name of the operator.
    `short_message`(str): message title
    `long_message`(str): full message
    
    To add operators add their name and Pushbullet Access token to the 
    pushbullet_address_book. Make an account on: https://www.pushbullet.com/, 
    goto settings, create and add."
    
    """
    address = pushbullet_address_book[operator.lower()]
    try:
        pb = Pushbullet(address)
        push = pb.push_note(short_message, long_message)
    except Exception as e:
        print ("Error, Unable to send push message. Error message: ", e)

def get_push(pushbullet_address_book, operator = 'lars', limit=1):
    """
    Get the last X push messages from the operator.
    Input:
    `pushbullet_address_book`(dict): Dictionary with the operator(s) and the
        access tokens.  
    `operator`(str): name of the operator.
    `limit`(int): Number of last messages to receive
    Returns:
    `message body`(str): Retruns the message body. Take note that this is 
    the last message, it can be a message the user send to the computer, 
    but it can also be a previously send message if the user did not reply.
    
    To add operators add their name and Pushbullet Access token to the 
    pushbullet_address_book. Make an account on: https://www.pushbullet.com/, 
    goto settings, create and add."
    
    """
    address = pushbullet_address_book[operator.lower()]
    try:
        pb = Pushbullet(address)
        return pb.get_pushes(limit=1)[0]['body']
    except Exception as e:
        print ("Error, Unable to receive push message. Error message: ", e)


#=============================================================================
# Managing .yaml files    
#=============================================================================

def yamlMake(filepath, new={}):
    """
    Make a .yaml file and dump a dictionary.
    Input:
    `filepath`(str): Full filepath with file name.
    `new`(dict): New dictionary to dump to the file

    """
    with open(filepath, 'w') as new_yaml_file:
        ruamel.yaml.dump(new, new_yaml_file, default_flow_style=False)

def yamlLoader(filepath):
    """
    Loads .yaml datafile into python dictionaries. (without comments)
    Input:
    `filepaht`(str): Path to .yaml datafile
    """
    try:
        with open(filepath, 'r') as file_descriptor:
            data = yaml.load(file_descriptor, Loader=yaml.FullLoader)
        return data
    except Exception as e:
        print('\nCould not correctly open the .yaml file')
        print('''The file needs to be formatted consistently. There needs to 
        be a space between key and value:  key:_value''')
        print('Error code:\n', e)

def updateDict(dictionary, new):
    """
    Update function for nested dictionaries.
    Input:
    `dictionary`(dict): dictionary to update
    `new`(dict): value to update, including all layers of nested dict. Like:
    {'Level1':{'Level2':{'Level3':{'key1':'new_value'}}}}
    
    """
    #from: http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    for key, value in new.items():
        if isinstance(value, collections.Mapping):
            r = updateDict(dictionary.get(key, {}), value)
            dictionary[key] = r 
        else:
            dictionary[key] = new[key]
    return dictionary

def yamlUpdate(filepath, new, file_extension=None):
    """
    Update function for .yaml files with nested dictionaries.
    Input:
    `filepath`(str): Name of .yaml datafile.
    `new`(dict): value to update, including all layers of nested dict. Like:
    {'Level1':{'Level2':{'Level3':{'key1':'new_value'}}}}
    `file_extension`(str):Optional file extension for new file.
    
    """
    with open(filepath, "r") as yaml_file:
        config, ind, bsi = load_yaml_guess_indent(yaml_file)
    
    #use 'updateDict' function that can update one value in a nested dict.
    updateDict(config, new)

    if file_extension != None:
        new_name = (filepath.split('.')[0] + file_extension +
                    '.' + filepath.split('.')[1])
    else:
        new_name = filepath
        
    with open(new_name, 'w') as updated_yaml_file:
        ruamel.yaml.round_trip_dump(config ,updated_yaml_file, 
                                    indent=ind, block_seq_indent=bsi)

def getFISHSystemMetadata(filename, table=None):
    """
    Get metadata from .yaml datafile.
    Input:
    `filename`(str): Filename of .yamle datafile.
    `table`(str) Optional: Specific table to return as dictionary.
    Returns:
    requested dictionary if table is provided
    Else 10 dictionaries: 
    "Parameters", "Volumes", "Targets", "Ports", "Hybmix", 
    "Machines", "Machine_identification", "Fixed_USB_port", "Operator_address", 
    "Padding", "Alert_volume"
    
    """
    try:
        metadata = yamlLoader(filename)
    except Exception as e:
        print('Unable to load metadata file: {}'.format(filename))
        
    if table == 'Parameters':
        return metadata['FISHSystem']['Parameters']
    elif table == 'Volumes':
        return metadata['FISHSystem']['Volumes']
    elif table == 'Targets':
        return metadata['FISHSystem']['Targets']
    elif table == 'Ports':
        return metadata['FISHSystem']['Ports']
    elif table == 'Hybmix':
        return metadata['FISHSystem']['Hybmix']
    elif table == 'Machines':
        return metadata['FISHSystem']['Machines']
    elif table == 'Machine_identification':
        return metadata['FISHSystem']['Machine_identification']
    elif table == 'Fixed_USB_port':
        return metadata['FISHSystem']['Fixed_USB_port']
    elif table == 'Operator_address':
        return metadata['FISHSystem']['Operator_address']
    elif table == 'Padding':
        return metadata['FISHSystem']['Padding']
    elif table == 'Alert_volume':
        return metadata['FISHSystem']['Alert_volume']
    else:
        return (metadata['FISHSystem']['Parameters'],
                metadata['FISHSystem']['Volumes'], 
                metadata['FISHSystem']['Targets'],
                metadata['FISHSystem']['Ports'],
                metadata['FISHSystem']['Hybmix'],
                metadata['FISHSystem']['Machines'],
                metadata['FISHSystem']['Machine_identification'],
                metadata['FISHSystem']['Fixed_USB_port'],
                metadata['FISHSystem']['Operator_address'],
                metadata['FISHSystem']['Padding'],
                metadata['FISHSystem']['Alert_volume'])


#=============================================================================
# Make a sqlite3 database for FISH2 System
#=============================================================================

def newFISHdb(db_name):
    """
    Make a new database for the FISH2 system.
    Creates tables for: Flags, Parameters, Volumes, Targets, Ports, Hybmix and
    Padding. Fills them with empty values, and if the db already exists, it 
    deletes all values.
    Input:
    `db_name`(str): Name of the database.
    Returns:
    `FISH_db_path`(str): Path to the (newly created) database.
    
    """
    #Check if db folder exists, otherwise create
    cwd = os.getcwd() #Current working directory
    FISH_db_folder = cwd + '\FISH_database' #Backslash for Windows
    if not os.path.exists(FISH_db_folder):    
        os.makedirs(FISH_db_folder)

    #Database name
    if not db_name.endswith('.sqlite'):
        db_name = db_name + '.sqlite'

    #Check if FISH_exp_db exists, otherwise create 
    FISH_db_path = FISH_db_folder + '\\' +  db_name
        
    if not os.path.isfile(FISH_db_path):
        print('No existing database found in location {}. New will be made...'.format(FISH_db_path))
        
        conn = sqlite3.connect(FISH_db_path)
        with conn:
            cursor = conn.cursor()
            
        #Flags
            cursor.execute("""CREATE TABLE Flags
                            (Pause_flag INTEGER,  
                            New_EXP_flag_1 INTEGER,
                            New_EXP_flag_2 INTEGER,
                            Parameters_flag INTEGER,
                            Volumes_flag INTEGER,
                            Targets_flag INTEGER,
                            Ports_flag INTEGER,
                            Hybmix_flag INTEGER,
                            Machines_flag INTEGER,
                            Machine_identification_flag INTEGER,
                            Fixed_USB_port_flag INTEGER,
                            Operator_address_flag INTEGER,
                            Padding_flag INTEGER,
                            Alert_volume_flag INTEGER,
                            RunningBuffer INTEGER,
                            P1 INTEGER,
                            P2 INTEGER,
                            P3 INTEGER,
                            P4 INTEGER,
                            P5 INTEGER,
                            P6 INTEGER,
                            P7 INTEGER,
                            P8 INTEGER,
                            P9 INTEGER,
                            P10 INTEGER,
                            P11 INTEGER,
                            P12 INTEGER,
                            P13 INTEGER,
                            P14 INTEGER,
                            P15 INTEGER,
                            P16 INTEGER,
                            P17 INTEGER,
                            P18 INTEGER,
                            P19 INTEGER,
                            P20 INTEGER)""")
            cursor.execute("INSERT INTO Flags DEFAULT VALUES")

        #Parameters
            cursor.execute("""CREATE TABLE Parameters
                            (Operator TEXT,
                            Machine TEXT,
                            EXP_number_1 TEXT,
                            Start_date_1 TEXT,
                            Chamber_EXP_1 TEXT,
                            Hyb_time_1_A REAL,
                            Hyb_time_1_B REAL,
                            Hyb_time_1_C REAL,
                            Chemistry_1 TEXT,
                            Target_cycles_1 INTEGER,
                            Barcode_1 TEXT,
                            Codebook_1 TEXT,
                            Barcode_length_1 INT,
                            Species_1 TEXT,
                            Strain_1 TEXT,
                            Sample_1 TEXT,
                            Age_1 TEXT,
                            Tissue_1 TEXT,
                            Orrientation_1 TEXT,
                            RegionImaged_1 TEXT,
                            SectionID_1 TEXT,
                            Position_1 TEXT,
                            StitchingChannel_1 TEXT,
                            Overlapping_percentage_1 TEXT,
                            roi_1 TEXT,
                            EXP_number_2 TEXT,
                            Start_date_2 TEXT,
                            Chamber_EXP_2 TEXT,
                            Hyb_time_2_A REAL,
                            Hyb_time_2_B REAL,
                            Hyb_time_2_C REAL,
                            Chemistry_2 TEXT,
                            Target_cycles_2 INTEGER,
                            Barcode_2 TEXT,
                            Codebook_2 TEXT,
                            Barcode_length_2 INT,
                            Species_2 TEXT,
                            Strain_2 TEXT,
                            Sample_2 TEXT,
                            Age_2 TEXT,
                            Tissue_2 TEXT,
                            Orrientation_2 TEXT,
                            RegionImaged_2 TEXT,
                            SectionID_2 TEXT,
                            Position_2 TEXT,
                            StitchingChannel_2 TEXT,
                            Overlapping_percentage_2 TEXT,
                            roi_2 TEXT,
                            Program TEXT,
                            Hybmix_volume INTEGER,
                            Staining_temperature REAL,
                            Readout_temperature REAL,
                            Heatshock_temperature REAL,
                            Stripping_temperature REAL,
                            Imaging_temperature REAL)""")
            cursor.execute("INSERT INTO Parameters DEFAULT VALUES")

        #Buffer volumes
            cursor.execute("""CREATE TABLE Volumes
                            (RunningBuffer REAL, 
                            P1 REAL,
                            P2 REAL,
                            P3 REAL,
                            P4 REAL,
                            P5 REAL,
                            P6 REAL,
                            P7 REAL,
                            P8 REAL,
                            P9 REAL,
                            P10 REAL,
                            P11 REAL,
                            P12 REAL,
                            P13 REAL,
                            P14 REAL,
                            P15 REAL,
                            P16 REAL,
                            P17 REAL,
                            P18 REAL,
                            P19 REAL,
                            P20 REAL)""")
            cursor.execute("INSERT INTO Volumes DEFAULT VALUES")

        #Ports
            cursor.execute("""CREATE TABLE Ports
                            (RunningBuffer TEXT,
                            P1 TEXT,
                            P2 TEXT,
                            P3 TEXT,
                            P4 TEXT,
                            P5 TEXT,
                            P6 TEXT,
                            P7 TEXT,
                            P8 TEXT,
                            P9 TEXT,
                            P10 TEXT,
                            P11 TEXT,
                            P12 TEXT,
                            P13 TEXT,
                            P14 TEXT,
                            P15 TEXT,
                            P16 TEXT,
                            P17 TEXT,
                            P18 TEXT,
                            P19 TEXT,
                            P20 TEXT)""")
            cursor.execute("INSERT INTO Ports DEFAULT VALUES")

        #Hyb mix, couples port code (PX) with Hybridization code (Cx_Y)X=chamber number, Y=cycle
            cursor.execute("""CREATE TABLE Hybmix
                            (P1 TEXT,
                            P2 TEXT,
                            P3 TEXT,
                            P4 TEXT,
                            P5 TEXT,
                            P6 TEXT,
                            P7 TEXT,
                            P8 TEXT,
                            P9 TEXT,
                            P10 TEXT,
                            P11 TEXT,
                            P12 TEXT,
                            P13 TEXT,
                            P14 TEXT,
                            P15 TEXT,
                            P16 TEXT,
                            P17 TEXT,
                            P18 TEXT,
                            P19 TEXT,
                            P20 TEXT)""")
            cursor.execute("INSERT INTO Hybmix DEFAULT VALUES")

        #Targets, genes/channel
            cursor.execute("""CREATE TABLE Targets
                            (Code TEXT,
                            Chamber INTEGER,
                            Hybridization TEXT,
                            DAPI TEXT,
                            Atto425 TEXT,
                            FITC TEXT,
                            Cy3 TEXT,
                            TxRed TEXT,
                            Cy5 TEXT,
                            Cy7 TEXT,
                            QDot TEXT,
                            BrightField TEXT,
                            Europium TEXT)""")
            cursor.execute("INSERT INTO Targets DEFAULT VALUES")

        #Machines
            cursor.execute("""CREATE TABLE Machines
                            (CavroXE1000 INTEGER,
                            CavroXCalibur INTEGER,
                            MXValve1 INTEGER,
                            MXValve2 INTEGER,
                            Degassi INTEGER,
                            ThermoCube1 INTEGER,
                            ThermoCube2 INTEGER,
                            YoctoThermistor INTEGER,
                            TC720 INTEGER)""")
            cursor.execute("INSERT INTO Machines DEFAULT VALUES")

         #Machine_identification
            cursor.execute("""CREATE TABLE Machine_identification
                            (CavroXE1000 TEXT,
                            CavroXCalibur TEXT,
                            MXValve1 TEXT,
                            MXValve2 TEXT,
                            Degassi TEXT,
                            ThermoCube1 TEXT,
                            ThermoCube2 TEXT,
                            YoctoThermistor TEXT,
                            TC720 TEXT)""")
            cursor.execute("INSERT INTO Machine_identification DEFAULT VALUES")
            
         #Fixed_USB_port
            cursor.execute("""CREATE TABLE Fixed_USB_port
                            (CavroXE1000 TEXT,
                            CavroXCalibur TEXT,
                            MXValve1 TEXT,
                            MXValve2 TEXT,
                            Degassi TEXT,
                            ThermoCube1 TEXT,
                            ThermoCube2 TEXT,
                            YoctoThermistor TEXT,
                            TC720 TEXT)""")
            cursor.execute("INSERT INTO Fixed_USB_port DEFAULT VALUES")

        #Pushbullet address book
            cursor.execute("""CREATE TABLE Operator_address
                            (lars TEXT,
                            alejandro TEXT,
                            simone TEXT,
                            operator4 TEXT,
                            operator5 TEXT,
                            operator6 TEXT,
                            operator7 TEXT,
                            operator8 TEXT,
                            operator9 TEXT,
                            operator10 TEXT)""")
            cursor.execute("INSERT INTO Operator_address DEFAULT VALUES")
        
        #Padding (distances between valve and component)
            cursor.execute("""CREATE TABLE Padding
                            (Degass INTEGER,
                            P1 INTEGER,
                            P2 INTEGER,
                            P3 INTEGER,
                            P4 INTEGER,
                            P5 INTEGER,
                            P6 INTEGER,
                            P7 INTEGER,
                            P8 INTEGER,
                            P9 INTEGER,
                            P10 INTEGER,
                            P11 INTEGER,
                            P12 INTEGER,
                            P13 INTEGER,
                            P14 INTEGER,
                            P15 INTEGER,
                            P16 INTEGER,
                            P17 INTEGER,
                            P18 INTEGER,
                            P19 INTEGER,
                            P20 INTEGER)""")
            cursor.execute("INSERT INTO Padding DEFAULT VALUES")

         #Alert volume
            cursor.execute("""CREATE TABLE Alert_volume
                            (RunningBuffer REAL, 
                            P1 REAL,
                            P2 REAL,
                            P3 REAL,
                            P4 REAL,
                            P5 REAL,
                            P6 REAL,
                            P7 REAL,
                            P8 REAL,
                            P9 REAL,
                            P10 REAL,
                            P11 REAL,
                            P12 REAL,
                            P13 REAL,
                            P14 REAL,
                            P15 REAL,
                            P16 REAL,
                            P17 REAL,
                            P18 REAL,
                            P19 REAL,
                            P20 REAL)""")
            cursor.execute("INSERT INTO Alert_volume DEFAULT VALUES")
            print('New database created.')
        
    else:
        print('FISH DB already exists, all content will be deleted')
        
        conn = sqlite3.connect(FISH_db_path)
        with conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM Flags")
            cursor.execute("INSERT INTO Flags DEFAULT VALUES")
            cursor.execute("DELETE FROM Parameters")
            cursor.execute("INSERT INTO Parameters DEFAULT VALUES")
            cursor.execute("DELETE FROM Volumes")
            cursor.execute("INSERT INTO Volumes DEFAULT VALUES")
            cursor.execute("DELETE FROM Targets")
            cursor.execute("INSERT INTO Targets DEFAULT VALUES")
            cursor.execute("DELETE FROM Ports")
            cursor.execute("INSERT INTO Ports DEFAULT VALUES")
            cursor.execute("DELETE FROM Hybmix")
            cursor.execute("INSERT INTO Hybmix DEFAULT VALUES")
            cursor.execute("DELETE FROM Machines")
            cursor.execute("INSERT INTO Machines DEFAULT VALUES")
            cursor.execute("DELETE FROM Machine_identification")
            cursor.execute("INSERT INTO Machine_identification DEFAULT VALUES")
            cursor.execute("DELETE FROM Fixed_USB_port")
            cursor.execute("INSERT INTO Fixed_USB_port DEFAULT VALUES")
            cursor.execute("DELETE FROM Operator_address")
            cursor.execute("INSERT INTO Operator_address DEFAULT VALUES")
            cursor.execute("DELETE FROM Padding")
            cursor.execute("INSERT INTO Padding DEFAULT VALUES")
            cursor.execute("DELETE FROM Alert_volume")
            cursor.execute("INSERT INTO Alert_volume DEFAULT VALUES")


    return FISH_db_path

def newRowDB(db_path, table, new_row):
    """
    Insert a new row into a table of a SQLite3 database.
    Input:
    `db_path`(str): Full path to database.
    `table`(str): Name of table to insert into.
    `new_row`(tuple): Tuple of items to insert. Like: ('text1', 'text2', 3, 4)
    WARNING: The function does not check if the input is valid and executed.
    
    """
    conn = sqlite3.connect(db_path)
    with conn:
        cursor = conn.cursor()
        
        q_marks = ('?,'* len(new_row))[:-1]
        cursor.execute("INSERT INTO {} VALUES ({})".format(table, q_marks), new_row)

def returnRowDB(db_path, table, criteria_column=None, criteria=None):
    """
    Return a (specific) row of a database table.
    Input:
    `db_path`(str): Full path to database.
    `table`(str): Name of table to retrieve from.
    Optional, select specific row:
    `criteria_column`(str): Name of column to select row by. Example: 'ID'
    `cirteria`: criteria value in the specified criteria_column. Example: '2' (where ID=2)
    Returns:
    Tuple of the retrieved row form selected table and selected row.
    
    """
    conn = sqlite3.connect(db_path)
    with conn:
        cursor = conn.cursor()

        if criteria_column is not None:
            cursor.execute("SELECT * FROM {} WHERE {}='{}'".format(table,
                                                                   criteria_column,
                                                                   criteria))
        else:
            cursor.execute("SELECT * FROM {}".format(table))
        row = cursor.fetchone()
        return row

def returnValueDB(db_path, table, column, criteria_column, criteria):
    """
    Return a single value from a database table.
    Input:
    `db_path`(str): Full path to database.
    `table`(str): Name of table to retrieve from.
    `column`(str): Column to retrieve from.
    `criteria_column`(str): Name of column to select row by. Example: 'ID'
    `cirteria`: criteria value in the specified column. Example: '2' (where ID=2)
    Returns:
    Retrieved value from selected table, column and row.
    WARNING: The function does not check if the input is valid.
    
    """
    conn = sqlite3.connect(db_path)
    with conn:
        cursor = conn.cursor()
    
        cursor.execute("SELECT {} FROM {} WHERE {}='{}'".format(column,table,
                                                                criteria_column,
                                                                criteria))
        try:
            row = cursor.fetchone()[0]
            return row
        except Exception as e:
            print('Error, could not select a valid value from sqlite3 db')
            print('Error message: ', e)

def updateValueDB(db_path, table, column, new_value=None, criteria_column=None, 
                  criteria=None, operation=None, value=None):
    """
    Update a single value from a database table.
    Input:
    `db_path`(str): Full path to database.
    `table`(str): Name of table to update.
    `column`(str): Column to update.
    `new_value`: new value.
    `criteria_column`(str): Name of column to select row by. Example: 'ID'
    `criteria`: criteria value in the specified column. Example: '2' (where ID=2)
    `operation`(str): '+' or '-', add or substract from a value. (atomic)
    `value`(int/flt): value to add or substract.
    WARNING: The function does not check if the input is valid and executed.
    
    """
    if returnRowDB(db_path, table) == None:
        newRowDB(db_path, table, (None, None))
    
    conn = sqlite3.connect(db_path)
    with conn:
        cursor = conn.cursor()
        

        if operation == None and criteria == None:
            cursor.execute("UPDATE {} SET {} = '{}'".format(table, 
                                                            column,
                                                            new_value))
                                                                  
        elif operation == None:
            cursor.execute("UPDATE {} SET {} = '{}' WHERE {} = '{}'".format(
                                                                    table, 
                                                                    column, 
                                                                    new_value,
                                                                    criteria_column,
                                                                    criteria))  
        elif operation != None:
            cursor.execute("UPDATE {} SET {} = {} {} {}".format(table, 
                                                                column,
                                                                column,
                                                                operation,
                                                                value))

def deleteRowDB(db_path, table, criteria_column, criteria, startswith=False):
    """
    Delete row(s) where the criteria matches a row in the criteria_column.
    The criteria can be the beginning of a string if "startswith"=True
    Input:
    `db_path`(str): Full path to database.
    `table`(str): Name of table to update.
    `criteria_column`(str): Name of column to select row by. Example: 'ID'
    `criteria`: Value in the specified column. Example:'2' (where ID=2)
    `startswith`(bool): If False uses full criteria. If True selects rows that
        start with the criteria. Default = False
        Example: 'Left_12' will be selected if criteria is 'Left'
    WARNING: The function does not check if the input is valid and executed.
    
    """
    conn = sqlite3.connect(db_path)
    with conn:
        cursor = conn.cursor()
        if startswith==False:
            cursor.execute("DELETE FROM {}  WHERE {} = '{}'".format(table, 
                                                                    criteria_column,
                                                                    criteria ))
        elif startswith==True:
            start = criteria + '%'
            cursor.execute("DELETE FROM {}  WHERE {} like '{}'".format(table, 
                                                                    criteria_column,
                                                                    start ))

def setFlagDB(db_path, flag):
    """
    Set a flag in the DB to indicate that data needs to be read and coppied.
    
    """
    updateValueDB(db_path, 'Flags', flag, new_value=1)
    
def removeFlagDB(db_path, flag):
    """
    Remove a flag in DB to indicate that data is read and coppied.
    
    """
    updateValueDB(db_path, 'Flags', flag, new_value=0)

#=============================================================================
# Move data from .yaml file to database
#=============================================================================

def yamlToDB_Parameters(db_path, to_update='All'):
    """
    Copy data from the Parameters dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    `to_update` Options: 
        'All' - All variables
        1 - Only variables of EXP 1
        2 - Only variables of EXP 2
        'optProg' - Operator and Program
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Para_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Parameters')

    if to_update == 'All':
        for k in Para_dict:
                updateValueDB(db_path, 'Parameters', k, new_value=Para_dict[k])
    elif to_update == 1:
        for k in Para_dict:
            if k.endswith('1'):
                updateValueDB(db_path, 'Parameters', k, new_value=Para_dict[k])
    elif to_update == 2:
        for k in Para_dict:
            if k.endswith('2'):
                updateValueDB(db_path, 'Parameters', k, new_value=Para_dict[k])
    elif to_update == 'opProg':
        updateValueDB(db_path, 'Parameters', 'Operator', new_value=Para_dict['Operator'])
    setFlagDB(db_path, 'Parameters_flag')

def yamlToDB_Volumes(db_path):
    """
    Copy data from the Volumes dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Buf_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Volumes')

    for k in Buf_dict:
        updateValueDB(db_path, 'Volumes', k, new_value=Buf_dict[k]) 
    setFlagDB(db_path, 'Volumes_flag')

def yamlToDB_Targets(db_path):
    """
    Copy data from the Targets dictionary of the yaml file to the database.
    If row already exists it gets updated otherwise a new is made.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Tar_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Targets')
    
    # Iterate through levels: chamber, Hybridization & items
    for chamber in Tar_dict:
        for hybridization in Tar_dict[chamber]:
            # Code to identify chamber and hybridization round
            code = 'C{}H{}'.format(chamber[-1], hybridization[-2:])
            
            # Check if row already exisits 
            if returnRowDB(db_path, 'Targets', criteria_column='Code', criteria=code) is not None:
                
                # Update existing row
                for item in Tar_dict[chamber][hybridization]:
                    updateValueDB(db_path, 'Targets', item, new_value=Tar_dict[chamber][hybridization][item], criteria_column='Code', criteria=code)
            
            # New row
            else:
                new_row = [code,
                           int(chamber[-1]), 
                           hybridization,
                           Tar_dict[chamber][hybridization]['DAPI'],
                           Tar_dict[chamber][hybridization]['Atto425'],
                           Tar_dict[chamber][hybridization]['FITC'],
                           Tar_dict[chamber][hybridization]['Cy3'], 
                           Tar_dict[chamber][hybridization]['TxRed'],
                           Tar_dict[chamber][hybridization]['Cy5'],
                           Tar_dict[chamber][hybridization]['Cy7'], 
                           Tar_dict[chamber][hybridization]['QDot'],
                           Tar_dict[chamber][hybridization]['BrightField'],
                           Tar_dict[chamber][hybridization]['Europium']]
                newRowDB(db_path, 'Targets', new_row)
                
    setFlagDB(db_path, 'Targets_flag')

def yamlToDB_Ports(db_path):
    """
    Copy data from the Ports dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Por_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Ports')
    
    for k in Por_dict:
        updateValueDB(db_path, 'Ports', k, new_value=Por_dict[k]) 
    setFlagDB(db_path, 'Ports_flag')

def yamlToDB_Hybmix(db_path):
    """
    Copy data from the Hybmix dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Hyb_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Hybmix')
    for k in Hyb_dict:
        updateValueDB(db_path, 'Hybmix', k, new_value=Hyb_dict[k]) 
    setFlagDB(db_path, 'Hybmix_flag')

def yamlToDB_Machines(db_path):
    """
    Copy data from the Machines dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'

    """
    Machines_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Machines')

    for k in Machines_dict:
        updateValueDB(db_path, 'Machines', k, new_value=Machines_dict[k]) 
    setFlagDB(db_path, 'Machines_flag')   

def yamlToDB_Machine_identification(db_path):
    """
    Copy data from the Machine_identification dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'

    """
    Machine_identification_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Machine_identification')

    for k in Machine_identification_dict:
        updateValueDB(db_path, 'Machine_identification', k, new_value=Machine_identification_dict[k]) 
    setFlagDB(db_path, 'Machine_identification_flag')   

def yamlToDB_Fixed_USB_port(db_path):
    """
    Copy data from the Fixed_USB_port dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'

    """
    Fixed_USB_port_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Fixed_USB_port')

    for k in Fixed_USB_port_dict:
        updateValueDB(db_path, 'Fixed_USB_port', k, new_value=Fixed_USB_port_dict[k]) 
    setFlagDB(db_path, 'Fixed_USB_port_flag')   

def yamlToDB_Operator_address(db_path):
    """
    Copy data from the Operator_address dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'

    """
    Operator_address_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Operator_address')

    for k in Operator_address_dict:
        updateValueDB(db_path, 'Operator_address', k, new_value=Operator_address_dict[k]) 
    setFlagDB(db_path, 'Operator_address_flag')   

def yamlToDB_Padding(db_path):
    """
    Copy data from the Padding dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Pad_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Padding')
    
    for k in Pad_dict:
        updateValueDB(db_path, 'Padding', k, new_value=Pad_dict[k]) 
    setFlagDB(db_path, 'Padding_flag')

def yamlToDB_Alert_volume(db_path):
    """
    Copy data from the Alert_volume dictionary of the yaml file to the database.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    Pad_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Alert_volume')
    
    for k in Pad_dict:
        updateValueDB(db_path, 'Alert_volume', k, new_value=Pad_dict[k]) 
    setFlagDB(db_path, 'Alert_volume_flag')

def yamlToDB_All(db_path):
    """
    Coppy all the data from the .yaml datafile to the working DB.
    Flags will be put to "1" for all changed DB tables.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """    
    # Update all tables (Excluding flags)
    yamlToDB_Parameters(db_path, to_update='All')
    yamlToDB_Volumes(db_path)
    yamlToDB_Targets(db_path)
    yamlToDB_Ports(db_path)
    yamlToDB_Hybmix(db_path)
    yamlToDB_Machines(db_path)
    yamlToDB_Machine_identification(db_path)
    yamlToDB_Fixed_USB_port(db_path)
    yamlToDB_Operator_address(db_path)
    yamlToDB_Padding(db_path)
    yamlToDB_Alert_volume(db_path)
    

#=============================================================================
# Move data from database to .yaml datafile
#=============================================================================

def dict_factory(cursor, row):
    """Used in returnDictBD"""
    #Docs: https://docs.python.org/2/library/sqlite3.html (row_factory)
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def returnDictDB(db_path, table):
    """
    Returns a dictionary of a sqlite table in the DB of db_path.
    Input:
    `db_path`(str): Full path to database.
    `table`(str): Name of table to return as dictionary.
    
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM {}".format(table))
        return cursor.fetchall()

def DBToYaml(db_path):
    """
    Function to copy all buffer volumes and active machines from the database to 
    the .yaml datafile.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    
    """
    #Update current buffer volumes
    current_Volumes = returnDictDB(db_path, 'Volumes')[0]
    yamlUpdate('FISH_System_datafile.yaml', {'FISHSystem':{'Volumes': current_Volumes}})

    #Update active machines
    active_machines = returnDictDB(db_path, 'Machines')[0]
    yamlUpdate('FISH_System_datafile.yaml', {'FISHSystem':{'Machines': active_machines}})


#=============================================================================
# User add new info to .yaml file and export to database
#=============================================================================

def userPrime(db_path):
    """
    Asks the user via a checkbox window which buffers need to be primed.
    Flags will be set and priming will happen once the "functionwrap" decorator
    checks the flags.
    Input:
    `db_path`(str): Full path to database.
    
    """
    #Set the Pause flag so that the FISH Program waits untill the user is done.
    setFlagDB(db_path, 'Pause_flag')
    print('A popup window will apprear. Check the boxes of the buffers that need to be primed.\n')

    Por_dict = getFISHSystemMetadata('FISH_System_datafile.yaml', table='Ports')

    #Let user select the ports to prime. 
    buttons = {}
    master = Tk()
    Label(master, text="Prime:").grid(row=0, sticky=W)
    for i, p in enumerate(['RunningBuffer', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10', 
                           'P11', 'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18', 'P19', 'P20']):
        buttons[p] = IntVar()
        Checkbutton(master, text='Port: {:15} Buffer:   {}'.format(p, Por_dict[p]), variable=buttons[p]).grid(row=i+1, sticky=W)
    mainloop()
    response = {k: buttons[k].get() for k in buttons.keys()}

    #Set the prime flag for the selected ports
    for k, v in response.items():
        if v == 1:
            setFlagDB(db_path, k)

    #Remove pause flag so that the FISH program can use it again
    removeFlagDB(db_path, 'Pause_flag')

def datafileUserUpdateAll(db_path):
    """
    Ask user to update the data file and exports the info to the DB.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    Template: 'FISH_System_datafile_template.yaml'
    
    """
    #Set the Pause flag so that the FISH Program waits untill the user is done.
    setFlagDB(db_path, 'Pause_flag')

    #check if file exists, otherwise make new one from template
    if not os.path.isfile('FISH_System_datafile.yaml'):
        print('No "FISH_System_datafile.yaml" found, creating new from template.')
        print(os.path.realpath('FISH_System_datafile.yaml')) #incase user needs to relocate file
        #Open template file including comments
        with open('FISH_System_datafile_template.yaml', "r") as yaml_file:
            config, ind, bsi = load_yaml_guess_indent(yaml_file)
        #Copy Template and use as working file
        with open('FISH_System_datafile.yaml', 'w') as new_yaml_file:
            ruamel.yaml.round_trip_dump(config ,new_yaml_file, 
                                        indent=ind, block_seq_indent=bsi) 

    #Open file for user to edit
    print('\nIn the Notepad edit the experimental info, save.')
    os.system('start Notepad++ FISH_System_datafile.yaml')
    input('Press Enter if all experiment metadata is correct and saved...')
    print('Updating database')
    
    yamlToDB_All(db_path)
    print('\nAll data copied from FISH_System_datafile.yaml to {}.\n'.format(db_path))
    
    userPrime(db_path)

    #Remove pause flag so that the program can use it again
    removeFlagDB(db_path, 'Pause_flag')

def checkboxUpdateDatafile():
    print('\nA checkbox will appear, tick the boxes of the updated tables, close.\n')
    master = Tk()
    Label(master, text="Updated tables:").grid(row=0, sticky=W)
    Label(master, text="Options").grid(row=0, column=3, sticky=W)
    var1 = IntVar()
    Checkbutton(master, text="Parameters", variable=var1).grid(row=1, sticky=W)
    var11 = IntVar()
    Checkbutton(master, text="All", variable=var11).grid(row=1,column=2, sticky=W)
    var12 = IntVar()
    Checkbutton(master, text="EXP1", variable=var12).grid(row=1,column=3, sticky=W)
    var13 = IntVar()
    Checkbutton(master, text="EXP2", variable=var13).grid(row=1,column=4, sticky=W)
    var14 = IntVar()
    Checkbutton(master, text="optProg", variable=var14).grid(row=1,column=5, sticky=W)
    var2 = IntVar()
    Checkbutton(master, text="Volumes", variable=var2).grid(row=2, sticky=W)
    var3 = IntVar()
    Checkbutton(master, text="Targets", variable=var3).grid(row=3, sticky=W)
    var4 = IntVar()
    Checkbutton(master, text="Ports", variable=var4).grid(row=4, sticky=W)
    var5 = IntVar()
    Checkbutton(master, text="Hybmix", variable=var5).grid(row=5, sticky=W)
    var6 = IntVar()
    Checkbutton(master, text="Machines", variable=var6).grid(row=6, sticky=W)
    var7 = IntVar()
    Checkbutton(master, text="Machine_identification", variable=var7).grid(row=7, sticky=W)
    var8 = IntVar()
    Checkbutton(master, text="Fixed_USB_port", variable=var8).grid(row=8, sticky=W)
    var9 = IntVar()
    Checkbutton(master, text="Operator_address", variable=var9).grid(row=9, sticky=W)
    var10 = IntVar()
    Checkbutton(master, text="Padding", variable=var10).grid(row=10, sticky=W)
    var11 = IntVar()
    Checkbutton(master, text="Alert_volume", variable=var11).grid(row=11, sticky=W)
    #Button(master, text='Quit', command=master.quit).grid(row=3, sticky=W, pady=4)
    mainloop()
    return ((var1.get(), var11.get(), var12.get(), var13.get(), var14.get()), 
            var2.get(), var3.get(), var4.get(), var5.get(), var6.get(), var7.get(),
            var8.get(), var9.get(), var10.get(), var11.get())

def datafileUserUpdateParts(db_path):
    """
    Ask user to update parts of the data file and exports only that part to
    the DB.
    Input:
    `db_path`(str): Full path to database.
    Fixed input:
    Working data file: 'FISH_System_datafile.yaml'
    Template: 'FISH_System_datafile_template.yaml'
    
    """
    #Set the Pause flag so that the FISH Program waits untill the user is done.
    setFlagDB(db_path, 'Pause_flag')

    #check if file exists, otherwise make new one from template
    if not os.path.isfile('FISH_System_datafile.yaml'):
        raise Exception('"FISH_System_datafile.yaml" does not exist, create first.')
    
    #Open file for user to edit
    print('\nIn the Notepad edit the experimental info, save.')
    print(os.path.realpath('FISH_System_datafile.yaml')) #incase user needs to relocate file
    os.system('start Notepad++ FISH_System_datafile.yaml')
    input('Press Enter if all experiment metadata is correct and saved...')
    
    #Ask which tables are updated using Tkinter checkboxes
    response = checkboxUpdateDatafile()
    
    if response[0][0]==1 or 1 in response[0][1:]:
        if response[0][1:].count(1) > 1:
            to_update = 'All'
        elif response[0][1:][0] == 1:
            to_update = 'All'
        elif response[0][1:][1] == 1:
            to_update = 1
        elif response[0][1:][2] == 1:
            to_update = 2
        elif response[0][1:][3] == 1:
            to_update = 'optProg'
        else: #If none specified, update All
            to_update = 'All'
        print('Updating database')
        yamlToDB_Parameters(db_path, to_update=to_update)
        print('Updated "Parameters, {}"'.format(to_update))
    if response[1] == 1:
        yamlToDB_Volumes(db_path)
        userPrime(db_path)
        print('Updated "Volumes"')
    if response[2] == 1:
        yamlToDB_Targets(db_path)
        print('Updated "Targets"')
    if response[3] == 1:
        yamlToDB_Ports(db_path)
        print('Updated "Ports"')
    if response[4] == 1:
        yamlToDB_Hybmix(db_path)
        print('Updated "Hybmix"')
    if response[5] == 1:
        yamlToDB_Machines(db_path)
        print('Updated "Machines"')    
    if response[6] == 1:
        yamlToDB_Machine_identification(db_path)
        print('Updated "Machine_identification"')   
    if response[7] == 1:
        yamlToDB_Fixed_USB_port(db_path)
        print('Updated "Fixed_USB_port"')   
    if response[8] == 1:
        yamlToDB_Operator_address(db_path)
        print('Updated "Operator_address"')   
    if response[9] == 1:
        yamlToDB_Padding(db_path)
        print('Updated "Padding"')
    if response[10] == 1:
        yamlToDB_Alert_volume(db_path)
        print('Updated "Alert_volume"')
    print('\nData copied from FISH_System_datafile.yaml to {}.\n'.format(db_path))

    #Remove pause flag so that the FISH program can use it again
    removeFlagDB(db_path, 'Pause_flag')


#=============================================================================
# Remove experiment from .yaml file and database
#=============================================================================

def countdown(seconds):
    """
    Countdown, printing on same line.
    Input:
    `seconds`(int): Seconds to count down.

    """
    #From: http://stackoverflow.com/questions/3419984/print-to-the-same-line-and-not-a-new-line-in-python
    def pre(seconds):
        n = seconds
        while n > -1:
            counter = '< {} > seconds'.format(n)
            counter = '\r'+ counter
            print(counter, end='')
            yield n
            n-=1
    
    for i in pre(seconds-1):
        time.sleep(1)


def removeExperiment(db_path, exp_number):
    """
    Removes all data related to "exp_number" from the datafile and loads the
    remaining info to the DB
    To prevent reading/writing to the same file Notepad++.exe will be closed.
    Input:
    `db_path`(str): Full path to database.
    `exp_number`(str): Experiment number
    
    """

    print('''!!WARNING!!
    Done with {}. All data will be erased from .yaml datafile and database.
    To prevent reading/writing to the same file, Notepad++.exe will be closed in:'''.format(exp_number))
    countdown(30)
    try:
        os.system('Taskkill /IM Notepad++.exe')
        print('Closed down Notepad++.exe')
    except Exception as e:
        print('Not possible to close Notepad++.exe')
        print('Error message: ', e)
    
    print('You will be notified when Notepad++.exe can be used again')


    with open('FISH_System_datafile.yaml', "r") as yaml_file:
        config, ind, bsi = load_yaml_guess_indent(yaml_file)
    
    #Use EXP number to get location and whether it is 1 or 2
    if exp_number == config['FISHSystem']['Parameters']['EXP_number_1']:
        one_two = 1
        chamber = 'Chamber1'
        HYB_code = 'C' + chamber[-1]
    elif exp_number == config['FISHSystem']['Parameters']['EXP_number_2']:
        one_two = 2
        chamber = 'Chamber2'
        HYB_code = 'C' + chamber[-1]
    else:
        raise Exception('Invalid Experiment number to remove from datafile.')
    print('Will remove "{}" with number: {} located: {}.'.format(exp_number, one_two, chamber))
        
    #Remove all "Parameters" info of experiement 1 or 2
    for k,v in config['FISHSystem']['Parameters'].items():
        if k.endswith(str(one_two)):
            config['FISHSystem']['Parameters'][k] = None
    
    #Remove all "Hybmix" info of experiment Left or Right
    for k,v in config['FISHSystem']['Hybmix'].items():
        try:
            if v.lower().startswith(HYB_code.lower()): #catch upper and lower case
                print(v)
                config['FISHSystem']['Hybmix'][k] = None
        except AttributeError:
            pass
    
    #Replace Targets by empty dictionary
    with open('FISH_System_datafile_template.yaml', "r") as yaml_file:
        Targets_template, ind2, bsi2 = load_yaml_guess_indent(yaml_file)
        Targets_template = Targets_template['FISHSystem']['Targets']

    config['FISHSystem']['Targets'][chamber] = Targets_template[chamber]
    config['FISHSystem']['Targets']

    #Replace working datfile with the striped version
    with open('FISH_System_datafile.yaml', 'w') as new_yaml_file:
        ruamel.yaml.round_trip_dump(config ,new_yaml_file, 
                                    indent=ind, block_seq_indent=bsi) 
    #Upload striped datafile to DB
    yamlToDB_All(db_path)

    print('''\nRemoved {} from .yaml datafile and database.\n
    Ready for new experiment.\n
    Notepad++.exe can be used again.'''.format(exp_number))

def removeHybmix(db_path, HYB_port):
    """
    Remove the Hybmix from the port after it has been used.
    Input:
    `db_path`(str): Full path to database.
    `HYB_port`(str): Port where the Hybmix was located. Like: "HYB01"
    
    """
    print('''!!WARNING!! To prevent reading/writing to the same file, Notepad++.exe will be closed in:''')
    countdown(2)
    try:
        os.system('Taskkill /IM Notepad++.exe')
        print('Closed down Notepad++.exe')
    except Exception as e:
        print('Not possible to close Notepad++.exe')
        print('Error message: ', e)
    
    print('You will be notified when Notepad++.exe can be used again')

    with open('FISH_System_datafile.yaml', "r") as yaml_file:
        config, ind, bsi = load_yaml_guess_indent(yaml_file)
        
    config['FISHSystem']['Hybmix'][HYB_port] = None
    
    print('Removed Hybmix code from {}'.format(HYB_port))
    
    #Replace working datfile with the striped version
    with open('FISH_System_datafile.yaml', 'w') as new_yaml_file:
        ruamel.yaml.round_trip_dump(config ,new_yaml_file, 
                                    indent=ind, block_seq_indent=bsi) 
    #Upload striped datafile to DB
    yamlToDB_Hybmix(db_path)
    
    print('Notepad++.exe can be used again')