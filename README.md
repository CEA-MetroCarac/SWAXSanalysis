# User guide to Edf2Nxsas
Table of contents :
- [General info](#General Info)
  - [Context](#context)
  - [Goals of the package](#goals-of-the-package)
  - [Installation](#installation)
- [Content](#content)
___
# General Info
## Context
This package, and all it's content, has been created by Adrien Toulouse (adrien.toulouse@cea.fr). It was created as a
part of a work-study program that was organized during the second year of my Master's degree in computational physics.
## Goals of the package
This package aims to convert any data stored in **European Data Format** file (called EDF or .edf file from now on) 
into data stored as a **Hierarchical Data Format version 5** (called HDF5 or .h5 file from now on).\
This new HDF5 file is structured according to the NXcanSAS format from the NeXus scientific community standard.
## Installation
You can install this package via pip using the command pip install git+ and copy/pasting the link to the github 
after the +. This should create an executable called "nxformat.exe" in the Scripts environment of your python 
installation. Alternatively you can import this package in a python script using import saxs_nxformat.
___
# Content
This repository contains the following : 
- README.md : This file
- pyproject.toml : File used to execute pip install git+
- saxs_nxformat
  - \_\_init\_\_.py : A script containing the basis of the package and the environment setup
  - class_nexus_file.py : A script containing the main class used to process data
  - create_config.py : A script containing the GUI's class and functions to create a settigs file
  - data_processing.py : A script containing the GUI's class and function to process data
  - launcher.py : Script used to create the executable and launch all the other GUI
  - nxfile_generator.py : A script containing the GUI's class and function to automatically convert edf files to 
    hdf5 files with the nexus standard
  - nexus_standards :
    - structure_NXcanSAS.json : A json containing the structure of the NXcanSAS standard
    - structure_NXunits.json : A json containing the structure to support different units.
___
# Additionnal info
As soon as you launch nxformat.exe, a folder named "Data Treatment Center" will be created on your desktop. This is 
where you should put the EDF files that have to be converted. There is also a configs file in that folder, this is 
where you should keep your config files for the programme and where they will be saved.
___
# Creating a settings file
This package converts .edf files to .hdf5 automatically but requires a settings file to do so.\
To create your very own settings file you have to click "create config" in the launcher.
## Step 1 : Providing a template .edf
As soon as you launch the script, this window will pop up :\
![Step 1](https://i.imgur.com/g5uDN5P.png)\
This is your first step, provide the most recent file produced by your machine (so you're sur it's up-to-date). This 
provided EDF file will act as a template.

## Step 2 : filtering the edf content
Once you've provided the file, you'll have a new field that pops up. This field will help you visualize the 
structure of your EDF header. Here is how it's organized :\
![Step 2](https://i.imgur.com/g0jQjes.png)\
In the first column you have the name of the parameters in the header of your .edf file, those are what we call "the 
keys". 
In the second column, you have the value corresponding to this key, i.e. the value associated to the name of the 
header variable.
Finally, you have a checkbox that lets you choose which parameters you want to keep. If the box is checked, the key 
will be saved for the next step. Be sure you selected all the values in the EDF header you want to keep.

Once you have checked all the parameters you want to keep, you can click next step. There will be a pop-up window 
listing all the keys you selected, make sure that they're all here. Confirming will take you to the next step, but if 
you want to go back to this step, you can always reload your file, but you'll have to reselect everything.

## Step 3 : matching edf keys and Nexus parameters
After clicking next step, you get this new window :\
![step 3](https://i.imgur.com/iz11wSU.png)\
This window shows the structure of the HDF5 that will be generated :
- Groups in red : These kind of work like folder in which you put datasets
- Datasets in blue : These kind of work like a file, they are where your variables and arrays are
- Attributes in green : These are like properties, they describe groups and datasets
- Descriptions in grey : A short description of what each field does.

Each of those fields are associated to a combobox. You can either :
- Fill in the combobox manually (static) : This will set the value you entered as a default for all generated files. 
- Fill in the combobox via selection (dynamic) : The options of the combobox are the edf keys you selected in the 
  previous step. if you choose one of those keys, when the creation of the hdf5 happens, the value associated to this 
  key in the edf will be used to fill the corresponding dataset in the hdf5. \
  For example if you kept the EDF key "wav" that was associated to the wavelength of the experiment you can select 
  "wav" in the "incident_wavelength" field to tell the settings file to associate the EdF key "wav" to the 
  HDF5 field "incident_wavelength" when converting files.

For the units, you cannot input your own unit, there are only the most common units. But you can always put the 
"arbitrary" unit which will prevent any and every subsequent conversion. Although this WILL have an impact on the 
analysis.

Once everything is filled out you can input a name for your settings file and click save (DO NOT USE "_" in the name 
of the file). 
Once that's done a new .json file should pop up in the configs folder that is in the Data Treatment Center folder on 
your desktop.

You're now done with the settings file. you can close the app if it's not already and proceed with the next steps.
___
# Generating the hdf5 files
Once you have setup your config file, put it in the "Data treatment Center" folder along with the files you want to 
convert. Once everything is ready, you can execute nxformat.exe again, this window should pop up : \
![Control panel](https://i.imgur.com/TpPoXoh.jpg) \
You can press start to start the automatic process of converting edf files to hdf5 using the settings file, all of 
which are supposed to be in the Data Treatment Center directory.\
Once the start button is pressed, the program will try to convert a file every 10 seconds. You can also stop the 
program or simply close it. \
Information regarding the current process of conversion are going to be displayed in the bottom window, you can 
always scroll to go back in time and see what happened.

With the conversion 3 things occur :
1. Your raw data will be saved in a group called DATA along with a array containing the naive positions.
2. Your raw data will be treated to be properly put into fourier space
3. Your raw data will be reduced to 1D via radial averaging
___
# Further processing
If you want to do more processing to your data you can write your own script and import saxs_nxformat but this 
package also has some processing options. Reexecute nxformat.exe and click on Process Data. A new window will pop-up :
![Processing panel1](https://i.imgur.com/Vs0oiMW.jpg) \
This window is used to do some more processing. Upload some files you'd like to process via the selec files button. 
The list of files you uploaded will then show up. You can click each of those file to choose which ones are going to 
be processed. You can select multiple files.\
On the right you can choose which process to apply to your data, by clicking one of them the frame under the 
selected files will display the parameter of the selected process.   
Once you click confirm each file will go through the process individually. 

Here is a completed panel :
![Processing panel2](https://i.imgur.com/0U0ZllJ.jpg)

Some general info on the parameters :
- Display will display the result of each process, close the plot to proceed to the next file. Use the save option 
  on the plot to save it as an image instead of data.
- Save will save the process to the h5 file under the group name. Another group called PROCESS_... will be created, 
  describing briefly what has been done to the data. I recommend you use the save option only when you're sure you 
  have the desired result
- Putting NONE in the entry boxes will put a default value. But If true or false is present by default you must put true or false in (not case sensitive).
- It is recommended to have the group names follow the UPPER_SNAKE_CASE convention.