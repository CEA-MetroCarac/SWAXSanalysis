"""
TODO : Add global variable for colormap, .ico path and other parameters
TODO : Add a utils file containing all repeating functions
TODo : change docstring on the structure to specify the fact that we use roll pitch yaw according to the pyfai convention
"""
import os
import sys
import json
from pathlib import Path


def get_desktop_path():
    """Return the path to the user's desktop"""
    if sys.platform == "win32":
        return Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))

    desktop = Path.home() / "Desktop"
    xdg_path = os.popen('xdg-user-dir DESKTOP').read().strip()

    if xdg_path:
        desktop = Path(xdg_path)

    return desktop


# Path to the different folders
BASE_DIR = Path(__file__).parent
DESKTOP_PATH = get_desktop_path()
DTC_PATH = DESKTOP_PATH / "Data Treatment Center"
CONF_PATH = DTC_PATH / "Configs"
TREATED_PATH = DTC_PATH / "Treated Data"
ICON_PATH = BASE_DIR / "Images" / "nxformat_icon.ico"

# Global variables to the file
PLT_CMAP = "magma"
json_path = BASE_DIR / "nexus_standards" / "structure_NXunits.json"
with open(json_path, "r", encoding="utf-8") as file_dict:
    DICT_UNIT = json.load(file_dict)
