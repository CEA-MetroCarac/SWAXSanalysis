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
installation. Alternatively you can import this package in a python script using import saxs_nxformat