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

Once the configuration file has been created you can put it in the Data Treatment Center folder that's been created 
on your desktop.

You can also use the package directly in a python script by importing the main class :
```
from SWAXSanalysis.class_nexus_file import NexusFile
```

In any case, an example notebook along with a jupyter notebook launcher is present in the Data Treatment Center.
## How to install
___
You can use your favorite IDE and/or open a terminal and type the following command :
```
pip install SWAXSanalysis
```
This should install the package. if you want to use the GUI, it should be in the Scripts folder of your Virtual 
environment under the name `SWAXSanalysis.exe`

## Changing the location of the Data Treatment Center
___
By default, the Data Treatment Center and Treatment Queue folder will be created on your desktop. To change the 
location of the Data Treatment Center, go to :
```
path\to\your\venv\Lib\site-packages\saxs_nxformat
 ```
and open the `__init__.py` file. In this file, find the line (should be line N°28) :
```
ENV_PATH: Path = DESKTOP_PATH
```
And change it to
```
ENV_PATH: Path = Path(r"path\where\Data Treatment Center\should\be")
```

## Known issues
___
- Changing the `ENV_PATH` by changing the `__init__.py` script is impractical.
- While creating the configuration file, there is no way to choose the NeXus definition, meaning that you have to 
  change the loaded definition in the python script directly.
- The program can't handle anything other than EDF file with one header and one dataset
- Azimuthal angle range is behaving weirdly when 0 is not in the range