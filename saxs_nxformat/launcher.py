"""
Tests the presence of some required files o nthe desktop then
opens a GUI allowing the user to:
- Build a config
- Convert to the NeXus format
- Process data
"""

import ctypes
import shutil
import tkinter as tk
from tkinter import ttk

from . import CONF_PATH, QUEUE_PATH, ICON_PATH, BASE_DIR
from . import DTC_PATH, IPYNB_PATH, TREATED_PATH
from . import FONT_TITLE, FONT_BUTTON
from .create_config import GUI_setting
from .data_processing import GUI_process
from .nxfile_generator import GUI_generator

# To manage icon of the app
myappid: str = 'CEA.nxformat.launcher'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


# Launch commands
def launch_app(old_root: tk.Tk, selection: str) -> None:
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
        app: GUI_setting = GUI_setting()
        app.mainloop()
    elif selection == "convert":
        app: GUI_generator = GUI_generator()
        app.mainloop()
    elif selection == "process":
        app: GUI_process = GUI_process()
        app.mainloop()


# GUI
def launcher_gui() -> None:
    """
    Function allowing the nxformat.exe to launch this GUI
    """
    # We create the file if they do not exist
    DTC_PATH.mkdir(parents=True, exist_ok=True)
    CONF_PATH.mkdir(parents=True, exist_ok=True)
    TREATED_PATH.mkdir(parents=True, exist_ok=True)
    IPYNB_PATH.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.mkdir(parents=True, exist_ok=True)

    # We move the notebook, jupyter launcher and settings into the DTC
    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "nexus_file_processing.ipynb",
        IPYNB_PATH
    )

    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "traitement GC.ipynb",
        IPYNB_PATH
    )

    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "jupyter_launcher.bat",
        IPYNB_PATH
    )

    shutil.copy(
        BASE_DIR / "machine_configs" / "XEUSS" / "settings_EDF2NX_XEUSS_202504090957.json",
        CONF_PATH
    )

    root: tk.Tk = tk.Tk()
    root.title("Launcher")
    root.iconbitmap(ICON_PATH)

    prompt: tk.Label = tk.Label(
        root,
        font=FONT_TITLE,
        text="What would you like to do ?"
    )
    prompt.grid(row=0, column=0, columnspan=3, pady=5, padx=5, sticky="we")

    button_config: tk.Button = tk.Button(
        root,
        font=FONT_BUTTON,
        text="Create config",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_app(root, "settings")
    )
    button_config.grid(row=1, column=0, sticky="news", pady=5, padx=5)

    button_convert: tk.Button = tk.Button(
        root,
        font=FONT_BUTTON,
        text="Convert to NeXus",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_app(root, "convert")
    )
    button_convert.grid(row=1, column=1, sticky="news", pady=5, padx=5)

    button_process: tk.Button = tk.Button(
        root,
        font=FONT_BUTTON,
        text="Process data",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_app(root, "process")
    )
    button_process.grid(row=1, column=2, sticky="news", pady=5, padx=5)

    button_close: tk.Button = tk.Button(
        root,
        font=FONT_BUTTON,
        text="Close",
        padx=5,
        pady=5,
        command=lambda: root.destroy()
    )
    button_close.grid(row=2, column=0, columnspan=3, pady=5, padx=5)

    root.mainloop()

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("edf2NeXus")
        self.geometry("800x600")
        self.iconbitmap(ICON_PATH)
        self.focus_force()

        style = ttk.Style()
        style.configure("TNotebook.Tab", font=FONT_BUTTON)

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)

        tab1 = GUI_generator(notebook)
        tab2 = GUI_process(notebook)
        tab3 = GUI_setting(notebook)

        notebook.add(
            tab1,
            text="NeXus file generation"
        )
        notebook.add(
            tab2,
            text="Data processing"
        )
        notebook.add(
            tab3,
            text="Settings generator"
        )



if __name__ == "__main__":
    # import cProfile, pstats
    #
    # profiler = cProfile.Profile()
    # profiler.enable()
    app = MainApp()
    app.mainloop()
    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('cumtime')
    # stats.print_stats()
