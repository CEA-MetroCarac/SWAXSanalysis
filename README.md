# User guide to this "package"

## Context

This "package" and all it's content has been created by Adrien Toulouse. It was created as part of my work-study
program that was organized by my college during my second year of my master's degree. \
I worked at the "Commisariat à l'Energie Atomique" in Grenoble, France, and studied at the "Faculté des sciences
de Montpellier".
this work is protected ???

## Goals of this package

This package aims to convert any **European Data Format** file (called EDF or .edf file from now on) into a
**Hierarchical Data Format version 5** (called HDF5 or .h5 file from now on).\
This new HDF5 file is structured according to the NeXus scientific community standard and supports the following
standards :

- NXsas (although a bit modified)
- NXcanSas (to come)

And I would like to add more if it is necessary.

## Install

To install it, you have to download all the python files and put them in the same folder.\
This package will create files in the parent folder. That's why I recommend creating a parent directory with a
name such as "DataTreatment" and put this package in a folder named "python script".\
Both folder can have any names, those are just the ones I recommend the most for clarity purposes.

## Description of the files :

This package contains 6 files :

- A markdown file : This file, README.md... Hi !
- A python file : formatNXsas.py, which contains the NeXus standard for NXsas. Although in later version this file will
  most likely be named NeXusformats and will store all the supported NeXus standards
- A python file : NeXus_Generation.py, which contains all the functions necessary to create the HDF5 file
- A python file : GUI_edf2h5.py (read EDF to H5), which opens a GUI to export EDF file to HDF5 files.
  This will be the first script you'll launch because this is the tool that will generate a settings file.
- A python file : auto_edf2h5.py, which will automatically export a .edf to a .h5 as long as there is a settings file in
  the parent folder. The .edf and .h5 will be automatically moved to a new folder in a neatly organized tree structure
- A python file : NeXus_modify, which will let you modify a .h5 file once it's been created.
- A folder : others, containing the images used in this readMe and other ressources

## First launch

The first launch of this program can be quite tricky for an inexperienced user, that's why I'm going to guide you
through all crucial steps.

### Launching a python file

The first script you want to execute is the GUI_edf2h5.py file. To do so you first need to setup a virtual environement
for python\
(détail du setup du venv à faire)\

### Creating your first settings file

One your virtual environement is setup, you can go ahead and execute the GUI_edf2h5.py script.
This should create a popup like so :

![alt-text](others/image README/firstPopUp.png "first popup")\

This first window is asking you if you want to launch the GUI in advanced mode. \
Advanced mode just mean that you'll have a lot more control over the creation of your .h5 file.
But more importantly, it will allow you to create the precious configuration file that you'll need to
automatically export .edf to .h5.

### Simple mode

![alt-text](others/image README/SimpleMode.png "Simple mode")

This is a preview of the GUI in simple mode, as you can see, you have :

1. A section to enter the **absolute path of the file you want to export** (in lavender), and a browse button if you
   want to enter
   it after searchin for its location in your files
2. A section to enter the **absolute path of the settings file you want to use to export your original file** (in
   lavender),
   and a browse button if you want to enter it after searchin for its location in your files
3. **A "close program" button** (in red) that does exactly what it says
4. **An "export file" button** (in green) that exports the .edf to a .h5 file in the same folder that contained your
   original file.
   Note that this will not erase your original file, only create a new one

You'll know if the export was a success based on the pop-up that will appear after you press export.\
Just know that if the export fail, most of the time it's because the settings file provided does not fill a required
parameter, in which case you'll have to fill it in yourself thanks to the new menu that pops up:

![alt-text](./others/image%20README/SimpleModeNew.png "Simple mode with fillable parameters")

We'll detail this new menu in the next section.

### Advanced mode

![alt-text](others/image README/AdvancedMode.PNG "Simple mode with fillable parameters")

In advanced mode you almost have the same thing as the last picture. Only the following element are added at the start :

- **An "Autofill" button** (in orange) to chose when you want to autofill
- **A "Create autofill settings** (in green) settings" that will open a new window, we'll talk about thta in the next
  section
- 3 columns :
    1. A column that indicates which **nexus parameter** is concerned by this row
    2. A section where you can **enter the value of said parameter** via an entry box or a combobox.
       A red box means that the parameter is required, whereas a yellow box means that the parameter is not required
    3. A combobox that lets you **chose a unit** from a list of allowed units. This is the unit of the value as it is in
       the
       .edf file. You cannot choose the unit in the .h5 file as it is set by NeXus.

Note that a value set to None will be set to an adequate default value in the .h5 file, here are the default
value possible:

- 0.0 for a number
- N/A for a text
- 0000-00-00T00-00-00 for a timestamp
- none otherwise

After you made sure all the parameters you want to have been filled, you can press the export button and a .h5 file will
appear where the .edf file is.

### The create autofill settings window

To open the window to create your autofill settings, you have to provide a template edf file, it can be the file
you want to export. After providing the file you can click the button, wich will open this window :

![alt-text](others/image README/AutoffilSettings.PNG "The first autofill settings window")

This first step displays all the metadata available in the header, that is the **name of the metadata (1), and it's
value (2)**.
You can select which header metadata you want to use
for the autofilling. Don't worry about selecting too much metadata it doesn't have any impact on the next step.\
To select which matadata you want to keep you can simply check the box right next to the value of your choosing,
it's in the third column.

Once all the desired metadata have been selected, **you can click next step (in green)**, **confirm** all the parameters
you want to keep
are on hte pop-up, and then it will show another step :

![alt-text](others/image README/Autofillsettings2.PNG "The first autofill settings window")

Here you can match the name of each metadata (1) to a NeXus parameters (2). Don't forget to specify the unit of the
metadata value (3) if there is one, otherwise, just put nothing. If you don't understand a parameter you can go check
their meaning by following this link : https://manual.nexusformat.org/classes/applications/index.html
and navigating to the desired NeXus standard.

Once you're done matching header and NeXus parameters, you can specify the name of the instrument that produced
the experimental data in the .edf file (in orange). I recommend to be as precise as possible, use only alphanumerical
caracters
(letters and numbers), and **DO NOT USE UBDERSCORES "_"**  otherwise some of the features might break.

Once everything is set up, you can click "save settings" (in green) and it will do exactly that.
A new settings file should appear in the same folder as the program.

## Testing your settings file

Before you proceed to the automatic generation of HDF5 files, I **HIGHLY** recommend testing your settings file. To do
so you just need to take an EDF file you'd like to export and launch the app in simple mode.\
Enter the EDF file and the settings file and try to export. Here are some results to expect and what to do :

- The export doesn't work because a required parameter has not been filled : to automatically export files to HDF5 your
  autofill settings **NEED** to autofill all required parameters, otherwise it won't be able to export automatically.
- The export doesn't work because a value could not be converted : you forgot, our put the wrong unit during the
  creation
  of the autofill settings

## Automatically generating HDF5 files

After generating and testing your settings file, and you are positive this is the one you want to keep, you can move it
to the parent folder, the one I call "Data treatment".\
In the same folder you can put all the EDF files you want to export into HDF5. You can also configure the instrument
that collects data to save the EDF file into the "Data treatment" folder.\
The EDF files have to start with a chain of caracter that resembles "nameOfSample_nameOfExperiment_..."
you can then replace... with anything you'd like or whatever the instrument would like.

Once that's done you can launch the program called "**auto_edf2h5.py**" this will launch a program that runs
continuously to check every 5 minutes if there are any edf files in the parent folder. If there are, it will :

- Create a tree structure of folder to classify your data files
- Move the .edf file into this tree structure so that it doesn't get treated and get stuck in a loop
- Move the .h5 file into another folder.

That way, the only thing that's supposed to be in your parent folder is the package, and the configuration file

## Side notes

- The generated settings file should have a name similar to the txt file present in the "others" folder of this package.
- All files generated by this package will have a timestamp in its name that indictaes when the file was generated. It
  in **ISO 8601**
- while choosing name avoid using special caracters like " ' * + / \ # ~ & | ^ @ and **DO NOT USE UNDERSCORES _**
- If you want to capture a broader spectrum of value and do multiple measurement with

## FAQ

#### Q : What do I do if the header of my file changes ?

A : You can simply regenerate a settings file by following the procedure described in the section "First launch"

#### Q : What if I want to view the content of my file ?

A : I suggest you either use the NeXus_modify.py (see next question) or you can download HDF5 viewer via this link:
https://www.hdfgroup.org/download-hdfview/

#### Q : What if I want to change my HDF5 file after creating it ?

A : You can use the NeXus_modify.py and provide it with the file you want to change



