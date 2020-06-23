#Script to rename the TEMPORARY pickeled dictionary with the experiment info 
#And link it with the Count of the Nikon imaging software
import sys
import os

#Get the input arguments
#The format is [script, count, output_folder]
i = sys.argv

#Get the count and format it correctly
count = int(i[1])
count = 'Count{0:05d}'.format(count)

#Get folder where the Nikon software is saving
imaging_output_folder = i[2]

#Rename the TEMPORARY file with Count0000X
for filename in os.listdir(imaging_output_folder):
    if filename.startswith("TEMPORARY"):
        #Reformat the file name
        fn = filename.split('_')
        fn[0] = count
        fn = '_'.join(fn)
        #Rename the file
        org_fp = os.path.join(imaging_output_folder, filename)
        new_fp = os.path.join(imaging_output_folder, fn)
        os.rename(org_fp, new_fp)

