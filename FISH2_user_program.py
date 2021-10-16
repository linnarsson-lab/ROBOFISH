#Python 3 program to manage User function for FISH system 2.
#Date: 02 February 2017
#Author: Lars E. Borm
#E-mail: lars.borm@ki.se or larsborm@gmail.com
#Python version: 3.5.1

#Creates the FISH_System2_db
#Asks the user to input all data realated to one or two experiments
#Constant loop where the user can update the .yaml datafile which gets exported
#to the database.

import FISH2_peripherals as perif
import time
from sys import platform

color = True
try:
    from colorama import Fore, Back, Style, init
except ImportError:
    color = False

if color == True:
    if platform == 'win32':
        init()



#Make FISH system 2 database
db_path = perif.newFISHdb('FISH_System2_db')
time.sleep(5)
print('db_path: ', db_path)
#Fill .yaml datafile and export to datbase
perif.datafileUserUpdateAll(db_path)

#When required the user can update the datafile which gets exported to the database.
#Or the program can be paused.
while True:
    while True:
        print('\n'*5)
        if color == True:
            print('Do you want to:\n' + Fore.BLACK + Back.WHITE + '* update (all / part) ' + Style.RESET_ALL + ' of the experiment data \n' + Fore.BLACK + Back.WHITE + '* pause ' + Style.RESET_ALL + ' the experiment\n' + Fore.BLACK + Back.WHITE + '* prime ' +  Style.RESET_ALL + ' the buffer line(s) \n' + Fore.BLACK + Back.WHITE + '* new exp ' +  Style.RESET_ALL + ' Add a new experiment \n' + Fore.BLACK + Back.WHITE + '* remove New_EXP_Flag ' + Style.RESET_ALL + ' If imaging settings have been prepared \n' + Style.RESET_ALL + '\n')
            print('Enter: ' + Fore.BLACK+Back.WHITE +' all ' + Style.RESET_ALL + ', ' + Fore.BLACK+Back.WHITE +' part ' + Style.RESET_ALL + ', ' + Fore.BLACK+Back.WHITE +' pause ' + Style.RESET_ALL + ', ' + Fore.BLACK+Back.WHITE +' prime '+ Style.RESET_ALL + ', ' + Fore.BLACK+Back.WHITE +' new ' + Style.RESET_ALL + ' or ' + Fore.BLACK+Back.WHITE +' remove ' + Style.RESET_ALL + '...')
            awnser = input('...').lower()
        else:
            awnser = input('''Do you want to update (all / part), pause, add new, remove New_EXP_Flag?\nEnter "all", "part" or "pause"...''').lower()
        if awnser == 'all' or awnser == 'part' or awnser == 'pause' or awnser == 'prime' or awnser =='new' or awnser == 'remove':
            break
        else:
            print('Invalid input, choose between "all", "part", "pause", "new" or "remove"')
            time.sleep(1)

    if awnser == 'all':
        perif.DBToYaml(db_path)
        print('Buffer volumes & machines coppied to .yaml info file.')
        perif.datafileUserUpdateAll(db_path)
        print('All data updated.')

    elif awnser == 'part':
        perif.DBToYaml(db_path)
        print('Buffer volumes & machines coppied to .yaml info file.')
        perif.datafileUserUpdateParts(db_path)
        print('Requested data updated.')

    elif awnser == 'pause':
        perif.setFlagDB(db_path, 'Pause_flag')
        print('Experiment paused.\n')
        input('Press enter to continue with experiment...')
        perif.removeFlagDB(db_path, 'Pause_flag')
        print('Experiment will resume. \n')

    elif awnser == 'prime':
        perif.userPrime(db_path)

    elif awnser == 'new':
        perif.setFlagDB(db_path, 'Pause_flag')
        print('Experiment paused.\n')
        perif.DBToYaml(db_path)
        print('Buffer volumes & machines coppied to .yaml info file.')
        perif.datafileUserUpdateAll(db_path)
        input('Press enter if new experiment is connected and ready to be stained...')
        
        
        print('\nIf possible, prepare the imaging now (set ROI, focus etc.)')
        print('If not possible, you will be reminded when the current imaging is done.')
        while True:
            img_prep = input('Is the imaging already prepared? Y/N: ').lower()
            if img_prep == 'y' or img_prep == 'n':
                break
            else:
                print('Invalid input: {}. Choose: "Y" '.format(img_prep))
         
        while True:
            chamber = input('For which chamber is the imaging prepared, "1" or "2": ')
            try:
                chamber = int(chamber)
                if chamber == 1 or chamber == 2:
                    break
                else:
                    print('Invalid input: {}. Choose between "1" or "2"'.format(chamber))
            except Exception as e:
                print('Invalid input: {}. Choose between "1" or "2"'.format(chamber))
           
        if img_prep == 'y':            
            perif.removeFlagDB(db_path, 'New_EXP_flag_{}'.format(chamber))
            print('Imaging prepared, New_EXP_flag_{} removed\n'.format(chamber))
                    
        elif img_prep == 'n':
            perif.setFlagDB(db_path, 'New_EXP_flag_{}'.format(chamber))
            print('Imaging not yet prepared, New_EXP_flag_{} set'.format(chamber))
            print('You will be notified when you can prepare the imaging\n')

        perif.removeFlagDB(db_path, 'Pause_flag')
        print('Experiment will resume. \n')

    elif awnser == 'remove':
        while True:
                chamber = input('For which chamber is the imaging prepared, "1" or "2": ')
                try:
                    chamber = int(chamber)
                    if chamber == 1 or chamber == 2:
                        break
                except Exception as e:
                    print('Invalid input: {}. Choose between "1" or "2"'.format(chamber))
        perif.removeFlagDB(db_path, 'New_EXP_flag_{}'.format(chamber))

    print('#'*80)