"""
Tests the presence of some required files o nthe desktop then
opens a GUI allowing the user to:
- Build a config
- Convert to the NeXus format
- Process data
"""

import argparse
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


# GUI
class MainApp(tk.Tk):
    def __init__(self, jenkins):
        super().__init__()
        self.jenkins = jenkins

        self.title("edf2NeXus")

        # Setup geometry
        window_width = 1500
        window_height = 800

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.iconbitmap(ICON_PATH)
        self.focus_force()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("TNotebook.Tab", font=FONT_BUTTON)

        notebook = ttk.Notebook(self)
        notebook.grid(sticky="news", row=0)

        self.tab1 = GUI_generator(notebook, jenkins)
        self.tab2 = GUI_process(notebook)
        self.tab3 = GUI_setting(notebook)

        notebook.add(
            self.tab1,
            text="NeXus file generation"
        )
        notebook.add(
            self.tab2,
            text="Data processing"
        )
        notebook.add(
            self.tab3,
            text="Settings generator"
        )

        close_button = tk.Button(
            self,
            text="Close",
            command=self.close,
            bg="#DBDFAC",
            fg="black",
            padx=10,
            font=FONT_BUTTON
        )
        close_button.grid(sticky="w", pady=10, padx=10, row=1)

    def close(self) -> None:
        """
        Properly closes the window
        """
        self.destroy()


def launcher_gui():
    """Launches the GUI"""
    try:
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
    
        app = MainApp(False)
        app.mainloop()
    except Exception as e:
        print("An error as occured", e)
        import traceback
        traceback.print_exc()
        input("Press enter to quit")


if __name__ == "__main__":
    try:
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
    
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument("--jenkins", type=str)
        arguments = arg_parser.parse_args()
    
        if arguments.jenkins:
            arguments.jenkins.lower()
            if arguments.jenkins == "false":
                JENKINS = False
            elif arguments.jenkins == "true":
                JENKINS = True
            else:
                raise ValueError("The argument --jenkins must be true or false")
        else:
            raise ValueError("The argument --jenkins was not filled")
    
        if JENKINS:
            app = GUI_generator(jenkins=JENKINS)
            app.activate_thread = True
            app.auto_generate()
        else:
            app = MainApp(JENKINS)
            app.mainloop()
    except Exception as e:
        print("An error as occured", e)
        import traceback
        traceback.print_exc()
        input("Press enter to quit")
