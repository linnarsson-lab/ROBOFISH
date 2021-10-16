#The files/folders that need to be in the executing folder are:
# yocto_api.py
# yocto_temperature.py
# folder: cdll
#Available from the Yoctopuce website:
#http://www.yoctopuce.com/EN/libraries.php Python libraries

#TODO:
#Make plotting function
    #Buffer creation is commented out.


import os,sys
import time
import threading
import csv
import numpy as np
import collections

from yocto_api import *
from yocto_temperature import *

class FISH_thermistor():
    """
    Class to initiate and read the temperature of a Yoctopuce Maxi Thermistor

    """

    temperature = []

    def __init__(self, logical_name = None, serial_number = None, **kwargs):
        """
        Instatiate sensor, check if it works and opens temperature channels
        Input:
        `logical_name`: Logical name of the sensor (set in the Yoctopuce 
            software)
        `serial_number`: Unchangable serial number of the sensor (can be found 
            in the Yoctopuce software) 
        One of the two is required.

        """

        self.logical_name = logical_name
        self.serial_number = serial_number
        self.errmsg=YRefParam()

        # Setup the API to use local USB devices
        if YAPI.RegisterHub("usb", self.errmsg)!= YAPI.SUCCESS:
            sys.exit("init error"+self.errmsg.value)

        if self.logical_name != None:
            self.target = self.logical_name
        elif self.serial_number != None:
            self.target = self.serial_number
        elif self.serial_number == None and self.logical_name == None:
            self.thermistor_die('Specify logical name or serial number')

        #Instantiate sensor
        self.sensor= YTemperature.FindTemperature(self.target + '.temperature1')

        #Check if sensor is valid and live
        if self.sensor is None :
            self.thermistor_die('No module connected, check connection and name')
        if not(self.sensor.isOnline()):
            self.thermistor_die('device not connected')

        #Get sensor serial number
        self.serial=self.sensor.get_module().get_serialNumber()

        #Initiate channels
        self.init_channels()


    def thermistor_die(self, msg):
       sys.exit(msg+' (check name or USB cable)')

    def init_channels(self):
        global channel1, channel2, channel3, channel4, channel5, channel6
        channel1 = YTemperature.FindTemperature(self.serial + '.temperature1')
        channel2 = YTemperature.FindTemperature(self.serial + '.temperature2')
        channel3 = YTemperature.FindTemperature(self.serial + '.temperature3')
        channel4 = YTemperature.FindTemperature(self.serial + '.temperature4')
        channel5 = YTemperature.FindTemperature(self.serial + '.temperature5')
        channel6 = YTemperature.FindTemperature(self.serial + '.temperature6')

    def read_temperature(self):
        """
        get the temperature values of the 6 channels.
        returns the 6 temperatures individualy (not as list).
        
        """
        temp1 = channel1.get_currentValue()
        temp2 = channel2.get_currentValue()
        temp3 = channel3.get_currentValue()
        temp4 = channel4.get_currentValue()
        temp5 = channel5.get_currentValue()
        temp6 = channel6.get_currentValue()

        return temp1, temp2, temp3, temp4, temp5, temp6



    def pr(self, time):

        for i in range(time):
            print(self.read_temperature())
            YAPI.Sleep(1000)


class FISH_temperature_deamon():
    """
    Class that can run the Yoctopuse Maxi Thermistor in the background
    on a seperate thread and real live plot the data. All data will be
    sved to a .csv file. 
    Input:
    `logical_name`(str): logical name of the sensor
    `serial_number(str): serial number of sensor
    `exp_name`(str): Experiment name to track files 
    `buffer_size`(int): number of hours to plot in graph (default=2) 
    `log_interval`(int): Interval in seconds to save the temperature data.
        default = 1 second

    """
    def __init__(self, logical_name = None, serial_number = None, 
                 exp_name = None, buffer_size=2, log_interval=1):
        #Initiate sensor using the FISH_thermistor class
        if logical_name != None:
            self.sensor = FISH_thermistor(logical_name = logical_name)
        if serial_number != None:
            self.sensor = FISH_thermistor(serial_number = serial_number)
        #Setup log file and exp name
        self.exp_name = exp_name
        #Creates log file and returns the file name
        self.temp_log_filename = self.temp_log_file(self.exp_name)
        #make buffers for graph with length in hours
        #self.make_buffers(buffer_size)
        self.log_interval = log_interval
        
# Worker that reads the temp form the sensor, saves it to file, plots and makes it available, every second.

    def worker(self): #Can not pass the sensor as argument here, threading will complain
        """
        thread worker function. Reads the temperature, saves it to a file
        and makes the data available for other programs using the get_temp()
        funciton.
        
        """
        thread_name = threading.currentThread().getName()
        print('Started FISH_temperature_deamon in the backround on thread: {}'.format(thread_name))
        global current_temp
        current_temp = []  
        count = 0

        while True:
            tic = time.time()
            event_flag.clear()
          #Get current temperature
            current_temp = self.background_get_temp(self.sensor)
          #write to file every interval
            if count % self.log_interval == 0:
                self.write_temp_log_file(self.temp_log_filename, current_temp)
                count = 0
          #updata data for plot
            #self.update_temp_data_buffer(current_temp)
          #update plot

            count += 1
            event_flag.set()
            toc = time.time()
            execute_time = toc - tic
            if execute_time > 1:
                execute_time = 0.001  
            time.sleep(1 - execute_time)
        return current_temp

# Low level funcitons used in __init__

    def temp_log_file(self, exp_name):
        """Make temperature log file, return file name"""
        if not os.path.exists('Temperature_log_files'):
            os.makedirs('Temperature_log_files')
        if exp_name != None:
            file_name = ('Temperature_log_files/' + exp_name + '_temp_log_' + 
                        str(time.strftime('%d-%m-%Y_%H-%M-%S')) + '.csv')
        else:
            file_name = ('Temperature_log_files/' +'temp_log_' + 
                        time.strftime('%d-%m-%Y_%H-%M-%S') + '.csv')
        print(file_name)
        self.logger_path = file_name
        with open(file_name, 'w', newline='') as temp_log:
            writer = csv.writer(temp_log)
            header = [['Timestamp','Sensor1','Sensor2','Sensor3','Sensor4',
                       'Sensor5','Sensor6']]
            writer.writerows(header)
        return file_name

    def make_buffers(self, buffer_size):
        """
        Make 7 buffers for time and temperature
        Input:
            `buffer_size`(int): number of hours to buffer (default=2)
        Buffers are fixed size 'deque' objects   
 
        """        
        buffer_size = buffer_size * 60 * 60 #buffer size in seconds

        self.time_data = collections.deque([None], maxlen=buffer_size)
        self.sensor1_data = collections.deque([None], maxlen=buffer_size)
        self.sensor2_data = collections.deque([None], maxlen=buffer_size)
        self.sensor3_data = collections.deque([None], maxlen=buffer_size)
        self.sensor4_data = collections.deque([None], maxlen=buffer_size)
        self.sensor5_data = collections.deque([None], maxlen=buffer_size)
        self.sensor6_data = collections.deque([None], maxlen=buffer_size)


# Low level funcitons used in the worker

    def background_get_temp(self, sensor):
        """Get the current time and temperature from sensor"""
        data = []
        now = time.strftime('%d-%m-%Y_%H:%M:%S')
        temperature = self.sensor.read_temperature()
        data.append(now)
        data += temperature
        return data

    def write_temp_log_file(self, file_name, data):
        """Write new data to temperature log file"""
        with open(file_name, 'a', newline='') as temp_log:
            writer = csv.writer(temp_log)
            writer.writerows([data])

    def update_temp_data_buffer(self, new_data):
        """Append new data to the data buffers"""
        self.time_data.append(new_data[0])
        self.sensor1_data.append(new_data[1]) 
        self.sensor2_data.append(new_data[2]) 
        self.sensor3_data.append(new_data[3]) 
        self.sensor4_data.append(new_data[4]) 
        self.sensor5_data.append(new_data[5]) 
        self.sensor6_data.append(new_data[6]) 

# Starting the deamon in seperate thread

    def deamon_start(self):
        global event_flag
        event_flag = threading.Event()
        temp_thread = threading.Thread(target=self.worker)#, args = self.sensor)
        temp_thread.setDaemon(True) #It will end the thread when the main process is done or quit
        temp_thread.start()
        time.sleep(1)

# Function to get the temperature from the main thread without interfeering with the worker.

    def get_temp(self):
        """Get the current time and temperature from deamon"""
        while not event_flag.isSet():
            event_is_set = event_flag.wait(0.1)
        return current_temp


if __name__ == "__main__":
    x = FISH_temperature_deamon(serial_number = 'THRMSTR2-629D5')
    x.deamon_start()
    print('This is a test function that will print the temp every sec for the next 10 seconds')
    for i in range (10):
        print(x.get_temp())
        #print('data buffer: ', x.sensor1_data[-20:])
        time.sleep(1)


