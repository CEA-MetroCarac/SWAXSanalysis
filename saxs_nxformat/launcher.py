"""
Tests the presence of some required files o nthe desktop then
opens a GUI allowing the user to:
- Build a config
- Convert to the NeXus format
- Process data
"""

import os
import sys
import shutil
import ctypes
import tkinter as tk

# Adds the package to the python path
# The version used is not the local one but the one installed in metro-carac !!!
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
myappid = 'CEA.nxformat.launcher'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


# We build the environment
from saxs_nxformat import DTC_PATH, CONF_PATH, TREATED_PATH, ICON_PATH, BASE_DIR, IPYNB_PATH
from saxs_nxformat.create_config import Setting
from saxs_nxformat.data_processing import GUI_process
from saxs_nxformat.nxfile_generator import GUI_generator


# Launch commands
def launch_app(old_root, selection):
    """
    Launches the selected application and then closes the old one

    Parameters
    ----------
    selection :
        selected application

    old_root :
        old window that will be destroyed
    -------

    """
    old_root.destroy()

    if selection == "settings":
        app = Setting()
        app.mainloop()
    elif selection == "convert":
        app = GUI_generator()
        app.mainloop()
    elif selection == "process":
        app = GUI_process()
        app.mainloop()


# GUI
def launcher_gui():
    """
    Function allowing the nxformat.exe to launch this GUI
    """
    # We create the file if they do not exist
    DTC_PATH.mkdir(parents=True, exist_ok=True)
    CONF_PATH.mkdir(parents=True, exist_ok=True)
    TREATED_PATH.mkdir(parents=True, exist_ok=True)
    IPYNB_PATH.mkdir(parents=True, exist_ok=True)

    # We move the notebook, jupyter launcher and settings into the DTC
    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "nexus_file_processing.ipynb",
        IPYNB_PATH
    )

    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "jupyter_launcher.bat",
        IPYNB_PATH
    )

    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "settings_EDF2NX_XEUSS_202503101406.json",
        CONF_PATH
    )

    root = tk.Tk()
    root.title("Launcher")
    root.iconbitmap(ICON_PATH)

    normal_font = ("Arial", 12)

    prompt = tk.Label(
        root,
        font=("Arial", 14, "bold"),
        text="What would you like to do ?"
    )
    prompt.grid(row=0, column=0, columnspan=3, pady=5, padx=5, sticky="we")

    button_config = tk.Button(
        root,
        font=normal_font,
        text="Create config",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_app(root, "settings")
    )
    button_config.grid(row=1, column=0, sticky="news", pady=5, padx=5)

    button_convert = tk.Button(
        root,
        font=normal_font,
        text="Convert to NeXus",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_app(root, "convert")
    )
    button_convert.grid(row=1, column=1, sticky="news", pady=5, padx=5)

    button_process = tk.Button(
        root,
        font=normal_font,
        text="Process data",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_app(root, "process")
    )
    button_process.grid(row=1, column=2, sticky="news", pady=5, padx=5)

    button_close = tk.Button(
        root,
        font=normal_font,
        text="Close",
        padx=5,
        pady=5,
        command=lambda: root.destroy()
    )
    button_close.grid(row=2, column=0, columnspan=3, pady=5, padx=5)

    root.mainloop()


if __name__ == "__main__":
    import cProfile, pstats

    profiler = cProfile.Profile()
    profiler.enable()
    launcher_gui()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('tottime')
    stats.print_stats()

