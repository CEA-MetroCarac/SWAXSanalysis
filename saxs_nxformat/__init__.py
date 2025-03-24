"""
TODO : Add global variable for colormap, .ico path and other parameters, font, fontsize...
"""
import os
import sys
import json
from pathlib import Path
import matplotlib.pyplot as plt


def get_desktop_path() -> Path:
    """Returns the path to the user's desktop"""
    if sys.platform == "win32":
        return Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))

    desktop = Path.home() / "Desktop"
    xdg_path = os.popen('xdg-user-dir DESKTOP').read().strip()

    if xdg_path:
        desktop = Path(xdg_path)

    return desktop


# Path to the different folders
DESKTOP_PATH: Path  = get_desktop_path()

ENV_PATH: Path      = DESKTOP_PATH
DTC_PATH: Path      = ENV_PATH / "Data Treatment Center"
CONF_PATH: Path     = DTC_PATH / "Configs"
TREATED_PATH: Path  = DTC_PATH / "Treated Data"
IPYNB_PATH: Path    = DTC_PATH / "Notebooks"

QUEUE_PATH: Path    = ENV_PATH / "Treatment Queue"

BASE_DIR: Path      = Path(__file__).parent
ICON_PATH: Path     = BASE_DIR / "Images" / "nxformat_icon.ico"

# Global variables to the file
PLT_CMAP: str   = "plasma"
PLT_CMAP_OBJ    = plt.get_cmap(PLT_CMAP)
json_path: Path = BASE_DIR / "nexus_standards" / "structure_NXunits.json"
with open(json_path, "r", encoding="utf-8") as file_dict:
    DICT_UNIT: dict = json.load(file_dict)

# Fonts for the GUI
FONT_TITLE: tuple   = ("Microsoft Sans Serif", 18, "bold")
FONT_TEXT: tuple    = ("Microsoft Sans Serif", 10)
FONT_NOTE: tuple    = ("Microsoft Sans Serif", 8)
FONT_BUTTON: tuple  = ("Microsoft Sans Serif", 12)
FONT_LOG: tuple     = ("Lucida Console", 10)
