"""
# TODO : Add global variable for colormap, .ico path and other parameters
"""
import os
import sys
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
