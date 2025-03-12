"""
This module is meant to be executed by the user and automatically
treats any .edf file found in the parent folder according to the
settings file also present in that parent folder
"""
import gc
import json
import os
import re
import shutil
import sys
import threading
import time
import tkinter as tk
import tkinter.messagebox
import tracemalloc
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

import fabio
import h5py
import numpy as np

from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)

from saxs_nxformat import DTC_PATH, TREATED_PATH, BASE_DIR, ICON_PATH, DICT_UNIT
from saxs_nxformat.class_nexus_file import NexusFile
from saxs_nxformat.utils import string_2_value, convert, replace_h5_dataset


def data_treatment(data, h5_file):
    """
    This function is used to treat data such that it can be put in
    the hf5 file.

    Parameters
    ----------
    data :
        Data that need treatment
    h5_file :
        File containing additional info

    Returns
    -------
    output :
        A dictionary containing the relevant data
    """
    # We get the metadata we need
    beam_center_x = h5_file["/ENTRY/INSTRUMENT/DETECTOR/beam_center_x"][()]
    beam_center_y = h5_file["/ENTRY/INSTRUMENT/DETECTOR/beam_center_y"][()]

    dim = np.shape(data)
    x_list = np.linspace(0 - beam_center_x, dim[1] - beam_center_x, dim[1])
    y_list = np.linspace(0 - beam_center_y, dim[0] - beam_center_y, dim[0])

    x_pixel_size = h5_file["/ENTRY/INSTRUMENT/DETECTOR/x_pixel_size"][()]
    y_pixel_size = h5_file["/ENTRY/INSTRUMENT/DETECTOR/y_pixel_size"][()]

    x_list = x_list * x_pixel_size
    y_list = y_list * y_pixel_size

    x_grid, y_grid = np.meshgrid(x_list, y_list)

    data_r = np.stack((x_grid, y_grid), axis=-1)
    data_i = data

    logical_mask = np.logical_not(data_i >= 0)

    output = {"R_data": data_r, "I_data": data_i, "mask": logical_mask}

    return output


def generate_nexus(edf_path, hdf5_path, settings_path):
    """
    The main function. it creates the hdf5 file and fills all it's content
    automatically using a settings file.

    Parameters
    ----------
    edf_path :
        Path of the original file

    hdf5_path :
        Path where the new file is supposed to go

    settings_path :
        Path of the settings file
    """
    edf_path = Path(edf_path)
    edf_name = edf_path.name
    edf_file = fabio.open(edf_path)
    edf_header = edf_file.header
    edf_data = edf_file.data

    def fill_hdf5(file, dict_content, parent_element=None):
        for key, value in dict_content.items():
            clean_key = key.strip("/").strip("@")

            if parent_element is None:
                parent_element = file

            content = value.get("content")
            element_type = value.get("element type")

            current_element = None
            if element_type == "group":
                current_element = parent_element.create_group(clean_key)
                if content:
                    fill_hdf5(file, content, current_element)

            elif element_type == "dataset":
                dataset_value = edf_header.get(value["value"], value["value"])
                dataset_value = string_2_value(str(dataset_value), value["type"])
                if content:
                    unit_attribute = content.get("@units")
                    if unit_attribute:
                        dataset_value = convert(dataset_value,
                                                unit_attribute["value"][0],
                                                unit_attribute["value"][1])
                current_element = parent_element.create_dataset(clean_key,
                                                                data=dataset_value)
                if content:
                    fill_hdf5(file, content, current_element)

            elif element_type == "attribute":
                if not (isinstance(value["value"], list)):
                    attribute_value = edf_header.get(value["value"], value["value"])
                else:
                    attribute_value = value["value"][1]
                attribute_value = string_2_value(str(attribute_value), value["type"])
                parent_element.attrs[clean_key] = attribute_value

            if current_element:
                current_element.attrs["EX_required"] = value["EX_required"]
                current_element.attrs["type"] = value["type"]
                current_element.attrs["docstring"] = value["docstring"]

    with open(settings_path, "r", encoding="utf-8") as config_file:
        config_dict = json.load(config_file)

    # We build the file name
    # TODO : Think of a better file name template
    sample_name_key = config_dict["/ENTRY"]["content"]["/SAMPLE"]["content"]["name"]["value"]
    sample_name = edf_header.get(sample_name_key, "defaultSampleName")
    current_time = datetime.now()
    time_stamp = str(current_time.strftime("%Y%m%d%H%M%S"))
    split_edf_name = edf_name.removesuffix(".edf").split("_")
    hdf5_path = os.path.join(hdf5_path, f"{sample_name}_img{split_edf_name[-1]}_{time_stamp}.h5")

    # We save
    with h5py.File(hdf5_path, "w") as save_file:
        fill_hdf5(save_file, config_dict)

        treated_data = data_treatment(edf_data, save_file)
        replace_h5_dataset(save_file, "ENTRY/DATA/Q", treated_data["R_data"])
        replace_h5_dataset(save_file, "ENTRY/DATA/I", treated_data["I_data"])
        replace_h5_dataset(save_file, "ENTRY/DATA/mask", treated_data["mask"])
    return hdf5_path


def search_setting_edf():
    """
    This function searches an edf file and a settings file
    in the parent folder.

    Returns
    -------
    edf_path : Path
        Path of the edf file.

    settings_path : Path
        Path of the settings file.
    """
    edf_name, settings_name = None, None

    for file in os.listdir(DTC_PATH):
        if ".edf" in file.lower():
            edf_name = file
        elif "settings_edf2nx" in file.lower():
            settings_name = file

    if edf_name is None or settings_name is None:
        return None, None

    edf_path = DTC_PATH / edf_name
    settings_path = DTC_PATH / settings_name

    return edf_path, settings_path


def tree_structure_manager(file: str, settings: str):
    """
    Creates a structured folder hierarchy based on the EDF file name and settings file.

    Parameters
    ----------
    file : str
        Name of the EDF file to be converted.
    settings : str
        Name of the settings file used for conversion.

    Returns
    -------
    tuple[str, str] | str
        - The paths where FDH5 and EDF5 files should be saved.
        - An error message in case of a permission issue.
    """
    # Dissecting the settings file name
    settings = settings.removeprefix("settings_")
    current_time = datetime.now()
    year = str(current_time.strftime("%Y"))
    try:
        origin2ending, instrument, date_txt = settings.rsplit("_", 2)
    except ValueError:
        return "Invalid settings file format"

    origin_format, ending_format = origin2ending.split("2")
    date = date_txt.removesuffix(".json")

    # Dissecting the data file name
    split_file_name = file.removesuffix(".edf").split("_")
    exp_name = split_file_name[0]
    if split_file_name[1] == "0":
        detector = "SAXS"
    elif split_file_name[1] == "1":
        detector = "WAXS"
    else:
        detector = "other"

    common_path = (
            TREATED_PATH /
            f"instrument - {instrument}" /
            f"year - {year}" /
            f"config ID - {date}" /
            f"experiment - {exp_name}" /
            f"detector - {detector}"
    )

    target_dir = common_path / f"format - {ending_format}"
    other_dir = common_path / f"format - {origin_format}"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        other_dir.mkdir(parents=True, exist_ok=True)
        return target_dir, other_dir
    except PermissionError:
        return "Permission to create directory denied"


class GUI_generator(tk.Tk):

    def __init__(self):
        self.activate_thread = False

        super().__init__()
        self.title("Auto Generate Controller")
        self.iconbitmap(ICON_PATH)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.control_panel = tk.Frame(self, padx=5, pady=5, border=5, relief="ridge")
        self.control_panel.grid(column=0, row=0, padx=5, pady=5, sticky="news")
        self._build_control_frame()

        self.plot_panel = tk.Frame(self, padx=5, pady=5, border=5, relief="ridge")
        self.plot_panel.grid(column=1, row=0, padx=5, pady=5, sticky="news")
        self._build_plot_frame()

        self.log_panel = tk.Frame(self, padx=5, pady=5, border=5, relief="ridge")
        self.log_panel.grid(column=2, row=0, padx=5, pady=5, sticky="news")
        self.log_panel.rowconfigure(1, weight=1)
        self._build_log_frame()

    def _build_control_frame(self):
        # Label
        title = tk.Label(self.control_panel, text="Auto conversion control panel", font=("Arial", 18, "bold"))
        title.grid(pady=10, padx=10, row=0, column=0)

        # Start Button
        start_button = tk.Button(self.control_panel,
                                 text="Start",
                                 command=self.start_thread,
                                 bg="#25B800",
                                 fg="white",
                                 padx=10,
                                 font=("Arial", 16, "bold")
                                 )
        start_button.grid(padx=10, pady=10, row=1, column=0)

        # Stop Button
        stop_button = tk.Button(self.control_panel,
                                text="Stop",
                                command=self.stop_thread_func,
                                bg="#D9481C",
                                fg="white",
                                padx=10,
                                font=("Arial", 16, "bold")
                                )
        stop_button.grid(padx=10, pady=10, row=2, column=0)

        # Close Button
        close_button = tk.Button(self.control_panel,
                                 text="Close",
                                 command=lambda: self.destroy(),
                                 bg="#DBDFAC",
                                 fg="black",
                                 padx=10,
                                 font=("Arial", 16, "bold")
                                 )
        close_button.grid(pady=10, padx=10, row=3)

    def _build_plot_frame(self):
        self.fig, self.ax = plt.subplots(1, 1, figsize=(5, 4), dpi=100, layout="constrained")
        self.ax.set_xlabel("$q_r (A^{-1})$")
        self.ax.set_ylabel("Intensity (A.U.)")
        self.ax.grid()
        self.ax.set_xscale("log")
        self.ax.set_yscale("log")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_panel)
        self.canvas.draw()

        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_panel, pack_toolbar=False)
        toolbar.update()

        toolbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)

    def _build_log_frame(self):
        # Label
        title = tk.Label(self.log_panel, text="Console log", font=("Arial", 18, "bold"))
        title.grid(pady=10, padx=10, row=0, column=0)

        # Log output area
        self.log_text = tk.Text(self.log_panel, height=20, width=50, font=("Arial", 12))
        self.log_text.grid(pady=10, padx=10, row=1, column=0, sticky="news")
        self.log_text.config(state=tk.NORMAL)

    def print_log(self, message):
        """Function to print logs in the Tkinter Text widget."""
        self.log_text.insert(tk.END, message + "\n\n")
        self.log_text.see(tk.END)

    def auto_generate(self):
        """
        This is a thread that runs continuously and tries to export edf files found in the parent folder
        into h5 files using the settings file found in the same folder.
        """
        tracemalloc.start()
        sleep_time = 10
        while self.activate_thread:
            current, peak = tracemalloc.get_traced_memory()
            self.after(
                0,
                self.print_log,
                f"Memory used:\n"
                f"  - Current: {current / (1024 ** 2):.2f} MB\n"
                f"  - Peak: {peak / (1024 ** 2):.2f} MB"
            )

            if peak / (1024 ** 2) > 500 or current / (1024 ** 2) > 500:
                self.after(
                    0,
                    self.print_log,
                    f"Too much memory used: {current}, {peak}"
                )
                break

            file_path, settings_path = search_setting_edf()
            if file_path is None or settings_path is None:
                self.after(
                    0,
                    self.print_log,
                    f"No file found, sleeping for {sleep_time} seconds."
                )
                time.sleep(sleep_time)
                continue

            result = tree_structure_manager(file_path.name, settings_path.name)
            if result[0] == "perm error":
                self.after(
                    0,
                    self.print_log,
                    "The program could not create the file due to a permission error"
                )
                self.destroy()

            self.after(
                0,
                self.print_log,
                f"Converting : {file_path.name}, please wait"
            )

            new_file_path = generate_nexus(file_path, result[0], settings_path)
            shutil.move(file_path, result[1] / file_path.name)

            nx_file = NexusFile([new_file_path])
            # TODO : when the user chooses processes they should be executed here
            nx_file.process_q_space(save=True)
            nx_file.process_radial_average(save=True)

            dict_Q, dict_I = nx_file.get_raw_data("DATA_RAD_AVG")
            for index, (name, param) in enumerate(dict_Q.items()):
                self.ax.loglog(param, dict_I[name])
                self.canvas.draw()

            nx_file.nexus_close()

            del nx_file
            gc.collect()

            self.after(
                0,
                self.print_log,
                f"{file_path.name} has been converted successfully\n"
            )
        tracemalloc.stop()
        self.after(
            0,
            self.print_log,
            "The program is done sleeping! you can start it again."
        )

    def start_thread(self):
        """Start the auto_generate function in a separate thread."""
        self.activate_thread = True
        thread = threading.Thread(target=self.auto_generate, daemon=True)
        thread.start()
        self.after(
            0,
            self.print_log,
            "Auto-generation started!"
        )

    def stop_thread_func(self):
        """Stop the auto_generate function."""
        self.activate_thread = False
        self.after(
            0,
            self.print_log,
            "Auto-generation stopped. The program is still sleeping!"
        )


if __name__ == "__main__":
    app = GUI_generator()
    app.mainloop()
