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
This package, and all it's content, has been created by Adrien Toulouse. It was created as part of a work-study 
program that was organized during the second year of a Master's degree.
## Goals of the package
This package aims to convert any data stored in **European Data Format** file (called EDF or .edf file from now on) 
into data stored as a
**Hierarchical Data Format version 5** (called HDF5 or .h5 file from now on).\
This new HDF5 file is structured according to a modified version of the NXsas format from the NeXus scientific 
community standard. We use a modified version because we would like to convert this same file to an NXcanSAS file 
containing the reduced data in the reciprocal space.
## Installation
To install this package you have to download the compressed version from this gitHub and then extract all it's 
content into a directory I'll call **Main directory**. 
___
# Content
This repository contains the following : 
- README.md : This file
- configs folder
  - settings_example.json :  contains an example of a settings file used to do the conversion
- edf2nxsas folder
  - nexus_format folder
    - structure_NXsas.json : contains the structure used to generate the .hdf5 file following the 
      modified NXsas standard
    - structure_NXcanSAS.json : contains the structure used to generate the .hdf5 file following the 
      NXcanSAS standard
    - structure_NXunits.json : contains the NeXus units supported by this package
  - create_config.py : Python script that allows the user to create a settings file suited to his machine
  - nexus_file_generator.py : Python script that, once executed, will automatically find .edf files in the parent 
    folder (the one I call main directory), convert them to .hdf5 with the NXsas standard and move both file to a 
    suited folder.
___
# Creating a settings file
This package converts .edf files to .hdf5 automatically but requires a settings file to do so.\
To create your very own settings file you have to launch the create_config.py script. We will go through all the steps.
## Step 1 : Providing a template .edf
As soon as you launch the script, this window will pop up :\
![Step 1](https://i.imgur.com/g5uDN5P.png)\
This is your first step, you have to provide an edf file, with the browse button, that your machine produces that will 
serve as a template. 

## Step 2 : filtering the edf content
Once you've provided the file, you'll have a new field that pops up :\
![Step 2](https://i.imgur.com/g0jQjes.png)\
In the first column you have the name of the parameters in the .edf file, those are the keys. 
In the second column, you have the value corresponding to this key.
Finally, you have a checkbox that lets you choose which parameters you want to keep.

Once you have checked all the parameters you want to keep, you can click next step. If you want to go back to this 
step, you can always reload your file.

## Step 3 : matching edf keys and Nexus parameters
After clicking next step, you get this :\
![step 3](https://i.imgur.com/iz11wSU.png)\
And you have multiple field, all of which are not meant to be 100% filled, although if you can, it's perfect.\
You have three types of elements :
- Groups in red : These kind of work like folder in which you put datasets
- Datasets in blue : These kind of work like a file, they are where your variables are
- Attributes in green : These are like properties, they describe groups and datasets
- Descriptions in grey : A short description of what each field does.

Each of those fields are associated to a combobox, you can put your own value which will be the default value, or you 
can choose one from the combobox. \
The options of the combobox are the edf keys you selected in the previous step. if you choose one of those keys, 
when the creation of the hdf5 happens, the value associated to this key in the edf will be used to fill the 
corresponding dataset in the hdf5. \
However if you choose to enter your own thing into the combobox, this value will be considered as a default value.

For the units, you cannot input your own unit. But you can put the "arbitrary" unit which will prevent any 
subsequent conversion.

Once everything is filled out you can input a name for your settings file and click save. Once that's done a new .
json file should pop up in the current directory. You can put it in the config folder.
___
# Generating the hdf5 files
Once you have setup your config file, put it in the main directory along with the files you want to convert. Once 
everything is ready, you can launch the nexus_file_generator.py script, this window should pop up : \
![Control panel](https://i.imgur.com/0SXCFHf.png) \
You can press start to start the automatic process of converting edf files to hdf5 using the settins file, all of 
which are supposed to be in the main directory.\
Once the start button is pressed, the program will try to convert a file every 5 minutes. You can also stop the 
program or simply close it.