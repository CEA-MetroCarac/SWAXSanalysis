# SWAXSanalysis
___
This package is used to convert edf files that contain one header and one dataset into an HDF5 file that contains 
information selected by the user.

Versioning Y.X1.X2.X3 :
- Y : year of release
- X1 : Big update (refactoring, new GUI, new way to use...)
- X2 : Update including new functionality.
- X3 : If 0, stable release, if not, it's a work in progress

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

In any case, an example notebook along with a jupyter notebook launcher is present in 
`SWAXSanalysis/machine_configs/XEUSS`. Otherwise, a copy of this jupyter launcher / notebook is also present in the 
Data Treatment center once the app has been launched.
## How to install
___
You have to activate a python virtual environment (more info on how to activate a Venv 
[here](https://docs.python.org/3/library/venv.html)) and type the following command :
```PowerShell
pip install SWAXSanalysis
```
After SWAXSanalysis is installed you need to install this branch of smi_analysis via the following command
```PowerShell
pip install git+https://github.com/gfreychet/smi-analysis.git@master
```
This wraps up the installation of the package in the activated virtual environment. If you want to use the GUI, you 
only need to type
```PowerShell
SWAXSanalysis
```
in the same activated virtual environment

The conversion process can be automated if the `launcher.py` has been launched with the argument `--no-gui "true"` like so :
```PowerShell
python3 -m SWAXSanalysis.launcher --nogui true 
```

## Changing the location of the Data Treatment Center
___
By default, the Data Treatment Center and Treatment Queue folder will be created on your desktop. To change the 
location of the Data Treatment Center, go to :
```
path\to\your\venv\Lib\site-packages\SWAXSanalysis
 ```
and open the `__init__.py` file. In this file, find this line (should be line N°28) :
```python
ENV_PATH: Path = DESKTOP_PATH
```
And change it to
```python
ENV_PATH: Path = Path(r"path\where\Data Treatment Center\should\be")
```

## Implementing new code
___
### New process
To add a new process to the code, simply go to the class_nexus_file.py and in the class NexusFile, you can define a 
new method. There are some things you should know :
1. If you want your process to be used only in script, there is no special condition. However if you want it to be 
   picked up by the GUI, the method's name must start with `process_...`.
2. If you want the process to be available in the GUI. You have to follow this signature standard :
```python
def process_example(
            self,
            param1: type1 = default1,
            param2: type2 = default2,
            param3: type3 = default3
    ) -> None:
    pass
```
You need to type your variables and give it a default value. You can put any default value but `None` or `""` are 
the most generic ones. Don't hesitate to look at the other processes to guide you.

To learn more about typing :\
https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
3. A process must include a for loop to apply the process to all files :
```python
for index, smi_data in enumerate(self.list_smi_data):
    pass
```
Usually, we iterate over `self.list_smi_data` since it's the pre-processed data and it was corrected via pyFAI. But 
should you want to iterate over the HDF5 files directly you can use `self.nx_files`.\
This loop should encompass al the code that actually treats and manipulate the smi_data.

4. If you want to add a way to save data you need to use the `save_data` function, present in the same file.
5. If you want to add a way to display data you need to use the `_display_data` method. This method is quite complex 
   so don't hesitate to look at other processes to see how to use it properly.

## Testing new implementation
___
When implementing new code in the package, you should always test if you broke something. To do so, you have a few 
test that you can conduct. Those test are present in the `tests` folder of the github project. In this folder you have :
- test_conversion : which is a test that should always be run
- test_new_nexus_def : this test should be run in case you have implemented a new NeXus definition 

## Known issues
___
- Changing the `ENV_PATH` by changing the `__init__.py` script is impractical.
- While creating the configuration file, there is no way to choose the NeXus definition, meaning that you have to 
  change the loaded definition in the python script directly.
- The program can't handle anything other than EDF file with one header and one dataset
- Azimuthal angle range is behaving weirdly when 0 is not in the range
- 2 param intensity is still a bit of a work in progress but should work as long as you do not use it with the batch 
  option enabled
- While processing something in the `data processing` tab, the windows stops responding but everything is still 
  processing.

## Prospects
___
- Manage uncertainty
- 