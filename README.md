# General Info

---
## Context
This package, and all it's content, has been created by Adrien Toulouse (adrien.toulouse@cea.fr). It was created as a
part of a work-study program that was organized during the second year of my Master's degree in computational physics.
## Goals of the package
This package aims to convert any data stored in **European Data Format** file (called EDF or .edf file from now on) 
into data stored as a **Hierarchical Data Format version 5** (called HDF5 or .h5 file from now on).\
This new HDF5 file is structured according to the NXcanSAS format from the NeXus scientific community standard.
## Installation
You can install this package via pip using the command :
```bash
pip install git+https://github.com/CEA-MetroCarac/saxs_nxformat.git
```
This should create an executable called "nxformat.exe" in the Scripts folder of your python virtual 
environment. You can create a shortcut to that executable on your desktop or wherever you'd like.\
Alternatively you can import this package in a python script using :
```python
import saxs_nxformat as sxf
```

# Using this tool

---
## Via executable
As mentioned earlier an executable called **nxformat.exe** can be found in the Scripts folder of your python virtual 
environment.\
Upon launching this executable, 2 new folders will be created on your desktop, they need to stay there for the 
program to work :
- Treatment Queue : That's where the data with the edf format is supposed to go
- Data Treatment Center : That's where the converted / treated data will end up

Once you've placed the data you want to process in Treatment Queue you have to put a config file in the data 
treatment center (there is an example settings file inside the configs folder in the Data Treatment Center). After 
that you're all good to go.

## Via Notebook
There's also some well documented example jupyter notebook into the notebooks folder along with a jupyter launcher to 
install and 
launch jupyter on your PC.

## Via scripting
In case you'd like to use the code directly, you could use the import as stated earlier but the main element of this 
package is the NexusFile class :  
```python
from saxs_nxformat.class_nexus_file import NexusFile
```
Here are some commands that are usefull:
```python
# Opening a file and guarantee the files are closed properly after doing processes on it
file_paths = ["./some/path/to/file.h5", "./some/other/path/to/file.h5"]
nx_file_object = NexusFile(file_paths)
try:
    nx_file_object.show_process()
except Exception as error:
    raise error
finally:
    nx_file_object.close()
```
1. NexusFile opens the the file in the list of paths. The paths have to be in a list, even if you enter one path only.
2. show_process() shows the available processes and their docstrings
3. close() closes the files properly, don't forget to use it
the try/except/finally guarantees that the files are properly closed