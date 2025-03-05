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
from datetime import datetime
from pathlib import Path

import fabio
import h5py
import numpy as np

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
    time_stamp = str(current_time.strftime("%Y-%m-%dT%H-%M-%S"))
    split_edf_name = edf_name.removesuffix(".edf").split("_")
    hdf5_path = os.path.join(hdf5_path, f"{sample_name}_img{split_edf_name[-1]}_{time_stamp}.h5")

    # We save
    with h5py.File(hdf5_path, "w") as save_file:
        fill_hdf5(save_file, config_dict)

        treated_data = data_treatment(edf_data, save_file)
        replace_h5_dataset(save_file, "ENTRY/DATA/R", treated_data["R_data"])
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
            f"config - {date}" /
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


STOP_THREAD = False


def print_to_gui(message):
    """Function to print logs in the Tkinter Text widget."""
    log_text.insert(tk.END, message + "\n\n")
    log_text.see(tk.END)


def auto_generate():
    """
    This is a thread that runs continuously and tries to export edf files found in the parent folder
    into h5 files using the settings file found in the same folder.
    """
    global STOP_THREAD
    tracemalloc.start()
    sleep_time = 10
    while not STOP_THREAD:
        current, peak = tracemalloc.get_traced_memory()
        root.after(
            0,
            print_to_gui,
            f"Memory used:\n"
            f"  - Current: {current / (1024 ** 2):.2f} MB\n"
            f"  - Peak: {peak / (1024 ** 2):.2f} MB"
        )

        if peak / (1024 ** 2) > 500 or current / (1024 ** 2) > 500:
            root.after(
                0,
                print_to_gui,
                f"Too much memory used: {current}, {peak}"
            )
            break

        file_path, settings_path = search_setting_edf()
        if file_path is None or settings_path is None:
            root.after(
                0,
                print_to_gui,
                f"No file found, sleeping for {sleep_time} seconds."
            )
            time.sleep(sleep_time)
            continue

        result = tree_structure_manager(file_path.name, settings_path.name)
        if result[0] == "perm error":
            root.after(
                0,
                print_to_gui,
                "The program could not create the file due to a permission error"
            )
            sys.exit()

        root.after(
            0,
            print_to_gui,
            f"Converting : {file_path.name}, please wait"
        )

        new_file_path = generate_nexus(file_path, result[0], settings_path)
        shutil.move(file_path, result[1] / file_path.name)

        nx_file = NexusFile([new_file_path])
        # TODO : when the user chooses processes they should be executed here
        nx_file.process_q_space(save=True)
        nx_file.process_radial_average(save=True)
        nx_file.nexus_close()

        del nx_file
        gc.collect()

        root.after(
            0,
            print_to_gui,
            f"{file_path.name} has been converted successfully\n"
        )
    tracemalloc.stop()
    root.after(
        0,
        print_to_gui,
        "The program is done sleeping! you can start it again."
    )


def start_thread():
    """Start the auto_generate function in a separate thread."""
    global STOP_THREAD
    STOP_THREAD = False
    thread = threading.Thread(target=auto_generate, daemon=True)
    thread.start()
    root.after(
        0,
        print_to_gui,
        "Auto-generation started!"
    )


def stop_thread_func():
    """Stop the auto_generate function."""
    global STOP_THREAD
    STOP_THREAD = True
    root.after(
        0,
        print_to_gui,
        "Auto-generation stopped. The program is still sleeping!"
    )


def create_gui():
    """Create the GUI with a Start and Stop button."""
    global root, log_text
    root = tk.Tk()
    root.title("Auto Generate Controller")
    root.iconbitmap(ICON_PATH)

    # Label
    label = tk.Label(root, text="Auto conversion control panel", font=("Arial", 18, "bold"))
    label.grid(pady=10, padx=10, row=0, column=0, columnspan=2)

    # Start Button
    start_button = tk.Button(root,
                             text="Start",
                             command=start_thread,
                             bg="#25B800",
                             fg="white",
                             padx=10,
                             font=("Arial", 16, "bold")
                             )
    start_button.grid(padx=10, pady=10, row=1, column=0)

    # Stop Button
    stop_button = tk.Button(root,
                            text="Stop",
                            command=stop_thread_func,
                            bg="#D9481C",
                            fg="white",
                            padx=10,
                            font=("Arial", 16, "bold")
                            )
    stop_button.grid(padx=10, pady=10, row=1, column=1)

    # Close Button
    close_button = tk.Button(root,
                             text="Close",
                             command=lambda: root.destroy(),
                             bg="#DBDFAC",
                             fg="black",
                             padx=10,
                             font=("Arial", 16, "bold")
                             )
    close_button.grid(pady=10, padx=10, row=2, column=0, columnspan=2)

    # Log output area
    log_text = tk.Text(root, height=10, width=75, font=("Arial", 12))
    log_text.grid(pady=10, padx=10, row=3, column=0, columnspan=2)
    log_text.config(state=tk.NORMAL)

    # Run the GUI loop
    root.mainloop()


if __name__ == "__main__":
    create_gui()
