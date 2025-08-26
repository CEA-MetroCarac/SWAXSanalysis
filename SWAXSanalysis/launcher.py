"""
Tests the presence of some required files on the desktop then
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

from . import QUEUE_PATH, ICON_PATH, BASE_DIR
from . import DTC_PATH, ENV_PATH
from . import FONT_TITLE, FONT_BUTTON
from .create_config import GUI_setting
from .data_processing import GUI_process
from .nxfile_generator import GUI_generator, auto_generate

# To manage icon of the app
myappid: str = 'CEA.nxformat.launcher'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


# GUI
class MainApp(tk.Tk):
    def __init__(self, ):
        super().__init__()
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

        self.tab1 = GUI_generator(notebook)
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
        if not DTC_PATH.exists():
            shutil.copy(
                BASE_DIR / "Data Treatment Center",
                ENV_PATH
            )
        QUEUE_PATH.mkdir(parents=True, exist_ok=True)

        app = MainApp(False)
        app.mainloop()
    except Exception as e:
        print("An error as occured", e)
        import traceback
        traceback.print_exc()
        input("Press enter to quit")


if __name__ == "__main__":
    try:
        if not DTC_PATH.exists():
            shutil.copytree(
                BASE_DIR / "Data Treatment Center",
                ENV_PATH / "Data Treatment Center",
                dirs_exist_ok=True
            )

        if not QUEUE_PATH.exists():
            QUEUE_PATH.mkdir(parents=True, exist_ok=True)

        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument("--nogui", type=str)
        arguments = arg_parser.parse_args()

        if arguments.nogui:
            arg_nogui = arguments.nogui.lower()
        else:
            print("The argument --nogui was not filled and has been set to false by default.")
            arg_nogui = "false"

        if arg_nogui == "false":
            NO_GUI = False
        elif arg_nogui == "true":
            NO_GUI = True
        else:
            raise ValueError("The argument --nogui must be true or false")

        if NO_GUI:
            auto_generate()
        else:
            app = MainApp()
            app.mainloop()
    except Exception as e:
        print("An error as occured", e)
        import traceback

        traceback.print_exc()
        input("Press enter to quit")
