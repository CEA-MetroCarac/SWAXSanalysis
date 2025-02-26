"""
teste l'existence des dossier requis sur le bureau puis
Ouvre une interface graphique qui permet à l'user de choisir si il veut:
- faire une config
- convertir de edf à hdf5
- traiter des données
"""

import tkinter as tk

# We build the environment
from saxs_nxformat import DTC_PATH, CONF_PATH, TREATED_PATH
from saxs_nxformat.create_config import Setting
from saxs_nxformat.data_processing import GUI_process
from saxs_nxformat.nxfile_generator import create_gui


# Launch commands

def launch_config(old_root):
    old_root.destroy()
    app = Setting()
    app.mainloop()


def launch_converter(old_root):
    old_root.destroy()
    create_gui()


def launch_process(old_root):
    old_root.destroy()
    app = GUI_process()
    app.mainloop()


# GUI
def launcher_gui():
    DTC_PATH.mkdir(parents=True, exist_ok=True)
    CONF_PATH.mkdir(parents=True, exist_ok=True)
    TREATED_PATH.mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    root.title("Launcher")

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
        command=lambda: launch_config(root)
    )
    button_config.grid(row=1, column=0, sticky="news", pady=5, padx=5)

    button_convert = tk.Button(
        root,
        font=normal_font,
        text="Convert to NeXus",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_converter(root)
    )
    button_convert.grid(row=1, column=1, sticky="news", pady=5, padx=5)

    button_treat = tk.Button(
        root,
        font=normal_font,
        text="Treat data",
        width=20,
        padx=5,
        pady=5,
        command=lambda: launch_process(root)
    )
    button_treat.grid(row=1, column=2, sticky="news", pady=5, padx=5)

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
    launcher_gui()
