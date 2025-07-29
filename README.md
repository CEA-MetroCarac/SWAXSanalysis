# SWAXSanalysis
___
This package is used to convert edf files that contain one header and one dataset into an HDF5 file that contains 
information selected by the user. This process can be automated if the `launcher.py` has been launched with the 
argument `--jenkins "true"`

## How it works
___
To convert the EDF file, the program uses a configuration file created by the user. To help create said file, a GUI 
is provided. This same GUI can be used to do basic processes to an HDF5 file that follows the NXcanSAS definition, 
as described by the NeXus Foundation : https://manual.nexusformat.org/classes/applications/NXcanSAS.html#nxcansas 

Once the configuration file has been created it should be saved in the "configs" folder inside the Data Treatment 
Center. You need to move the config file inside the Data Treatment Center directly for it to be detected and used in 
the conversion of file. By default, the Data Treatment Center is created on your desktop.

Once the config file is moved, you can put the EDF files you want to convert to hdf5 in the Treatment Queue folder.

You can also use the package directly in a python script by importing the main class and some utility functions :
```python
from SWAXSanalysis.class_nexus_file import NexusFile
from SWAXSanalysis.utils import save_data, extract_from_h5, delete_data
```

In any case, an example notebook along with a jupyter notebook launcher is present in the Data Treatment Center.
## How to install
___
You have to activate a python virtual environment (more info on how to activate a Venv 
[here](https://docs.python.org/3/library/venv.html)) and type the following command :
```PowerShell
pip install SWAXSanalysis
```
After SWAXSanalysis is install you need to install this branch of smi_analysis via the following command
```
pip install git+https://github.com/gfreychet/smi-analysis.git@master
```
This wraps up the install the package in the activated virtual environment. If you want to use the GUI, it should be in 
the Scripts folder of your Virtual environment under the name `SWAXSanalysis.exe`

## Changing the location of the Data Treatment Center
___
By default, the Data Treatment Center and Treatment Queue folder will be created on your desktop. To change the 
location of the Data Treatment Center, go to :
```
path\to\your\venv\Lib\site-packages\saxs_nxformat
 ```
and open the `__init__.py` file. In this file, find the line (should be line N°28) :
```python
ENV_PATH: Path = DESKTOP_PATH
```
And change it to
```python
ENV_PATH: Path = Path(r"path\where\Data Treatment Center\should\be")
```

## Known issues
___
- Changing the `ENV_PATH` by changing the `__init__.py` script is impractical.
- While creating the configuration file, there is no way to choose the NeXus definition, meaning that you have to 
  change the loaded definition in the python script directly.
- The program can't handle anything other than EDF file with one header and one dataset
- Azimuthal angle range is behaving weirdly when 0 is not in the range