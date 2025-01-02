"""
module description
"""
import json
import tkinter as tk
import tkinter.messagebox
import shutil
import threading
import time
import tracemalloc
import re
import os
import sys
from datetime import datetime
import fabio
import numpy as np
import h5py

from nexus_format_generator import dictUnit


def convert(number, unit_start, unit_end, testing=False):
    """
    Converts a value that is expressed in the unitStart into a value expressed in the unitEnd

    Parameters
    ----------
    number :
        the value that needs to be converted
    unit_start :
        the starting unit of the value
    unit_end :
        the unit we want to convert it to
    testing :
        a boolean var to know if we are in testing conditions or not

    Returns
    -------
    number :
        The converted value
    """
    if unit_start == "arbitrary" or unit_end == "arbitrary" or number is None:
        return number
    unit_type1 = None
    unit_type2 = None
    for key, value in dictUnit.items():
        if unit_start in value:
            unit_type1 = key

        if unit_end in value:
            unit_type2 = key

    if unit_type1 is None or unit_type2 is None or unit_type1 != unit_type2 and not testing:
        tkinter.messagebox.showerror("Error",
                                     f"The value {number} {unit_start} could not be converted to "
                                     f"{unit_end} :\n")
    elif unit_type1 is None or unit_type2 is None or unit_type1 != unit_type2 and testing:
        return "fail"

    unit_type = unit_type1

    if unit_type == "NX_ANGLE":
        starting_unit = dictUnit[unit_type][unit_start]
        intermediate_unit = dictUnit[unit_type]["turn"]
        ending_unit = dictUnit[unit_type][unit_end]

        number = number * (intermediate_unit / starting_unit)
        number = number * (ending_unit / intermediate_unit)
    elif unit_type == "NX_TEMPERATURE":
        starting_unit = dictUnit[unit_type][unit_start]
        ending_unit = dictUnit[unit_type][unit_end]
        if unit_end == "C":
            number = number - ending_unit
        else:
            number = number + starting_unit
    else:
        starting_unit = dictUnit[unit_type][unit_start]
        ending_unit = dictUnit[unit_type][unit_end]

        number = number * (starting_unit / ending_unit)

    # print(number_start, unitStart, number, unitEnd)
    return number


def string_2_value(string: str, unit_type: str) -> str | int | float | None:
    """
    Convert a string to a specific data type based on its format.

    The conversion rules are as follows:
    - Converts to `float` if the string matches a floating-point or scientific
    notation format (e.g., "X.Y", "XeY").
    - Converts to `int` if the string matches an integer format (e.g., "XXXX").
    - Converts to `None` if the string is empty or equals "None" (case insensitive).
    - Returns a lowercase version of the string otherwise.

    Parameters
    ----------
    string : str
        The input string to be converted.

    Returns
    -------
    str | int | float | None
        The converted value:
        - A `float` if the string represents a floating-point number.
        - An `int` if the string represents an integer.
        - `None` if the string is empty or equals "None".
        - A lowercase `str` otherwise.
    """
    if string is None:
        if unit_type == "NX_NUMBER":
            return 0.0
        if unit_type == "NX_CHAR":
            return "N/A"
        if unit_type == "NX_DATE_TIME":
            return "0000-00-00T00:00:00"
        else:
            return "None"
    if re.search("(^-?\\d*[.,]\\d*$)|(^-?\\d?[.,]\\d*e[+-]\\d*$)", string):
        value = float(string)
    elif re.search("^-?\\d+$", string):
        value = int(string)
    else:
        value = str(string)

    return value


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

    output = {"R_data": data_r, "I_data": data_i}

    return output


def replace_h5_dataset(file, dataset_path, new_data):
    """
    Function used to replace a dataset that's already been created
    in a hdf5 file

    Parameters
    ----------
    file :
        File containing the dataset

    dataset_path :
        Path of the dataset in the hdf5 file

    new_data :
        new value for the dataset
    """
    old_dataset = file[dataset_path]
    attributes = dict(old_dataset.attrs)

    del file[dataset_path]

    new_dataset = file.create_dataset(dataset_path, data=new_data)

    for key, value in attributes.items():
        new_dataset.attrs[key] = value


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
                current_element = parent_element.create_dataset(clean_key, data=dataset_value)
                if content:
                    fill_hdf5(file, content, current_element)

            elif element_type == "attribute":
                if isinstance(value["value"], list):
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

    sample_name_key = config_dict["/ENTRY"]["content"]["/SAMPLE"]["content"]["name"]["value"]
    sample_name = edf_header[sample_name_key]
    current_time = datetime.now()
    time_stamp = str(current_time.strftime("%Y-%m-%dT%H-%M-%S"))
    exp_type = "SAXS"
    hdf5_path = os.path.join(hdf5_path, f"{sample_name}_{exp_type}_{time_stamp}.h5")
    with h5py.File(hdf5_path, "w") as save_file:
        fill_hdf5(save_file, config_dict)

        treated_data = data_treatment(edf_data, save_file)
        replace_h5_dataset(save_file, "ENTRY/DATA/R", treated_data["R_data"])
        replace_h5_dataset(save_file, "ENTRY/DATA/I", treated_data["I_data"])


def search_setting_edf():
    """
    This function searches an edf file and a settings file
    in the parent folder

    Returns
    -------
    edf_name
        path of the edf file

    settings_name
        path of the settings file
    """
    edf_name, settings_name = None, None
    for file in os.listdir("./../"):
        if ".edf" in file.lower():
            edf_name = file
        elif "settings_edf2nxsas" in file.lower():
            settings_name = file
    return edf_name, settings_name


def tree_structure_manager(file, settings):
    """
    This function creates a tree structure of folder to organise the files based
    on the names of the edf file and the datafile

    Parameters
    ----------
    file
        The name of the edf file that's going to be converted

    settings
        The name of the settings file that's used to do the conversion

    Returns
    -------
    Either :
        - The path where the fdh5 should be saved and he path where the edf5 is supposed to go
        - An error message
    """
    # File splitting
    split_string = file.split("_")
    sample_name = split_string[0]
    experiment_type = split_string[1]
    if ".json" in experiment_type:
        experiment_type = experiment_type.strip(".json")

    # Settings splitting
    settings.strip("settings_")
    _, origin2ending, instrument, date_txt = settings.split("_")
    origin_format, ending_format = origin2ending.split("2")
    date = date_txt.strip(".txt")

    target_dir = "./../treated data" + \
                 f"/instrument - {instrument}" + \
                 f"/config - {date}" + \
                 f"/sample - {sample_name}" + \
                 f"/experiment - {experiment_type}" + \
                 f"/format - {ending_format}/"
    other_dir = "./../treated data" + \
                f"/instrument - {instrument}" + \
                f"/config - {date}" + \
                f"/sample - {sample_name}" + \
                f"/experiment - {experiment_type}" + \
                f"/format - {origin_format}/"
    try:
        os.makedirs(target_dir)
        os.makedirs(other_dir)
        return target_dir, other_dir
    except FileExistsError:
        return target_dir, other_dir
    except PermissionError:
        print("Permission to create directory denied")
        return "perm error"


STOP_THREAD = False


def auto_generate():
    """
    This is a thread that runs continuously and tries to export edf files found in the parent folder
    into h5 files using the settings file found in the same folder.
    """
    global STOP_THREAD
    tracemalloc.start()
    while not STOP_THREAD:
        current, peak = tracemalloc.get_traced_memory()
        if peak / (1024 ** 2) > 50 or current / (1024 ** 2) > 50:
            break

        file, settings = search_setting_edf()
        if file is None or settings is None:
            time.sleep(300)
            continue

        result = tree_structure_manager(file, settings)
        if result[0] == "perm error":
            sys.exit()
        generate_nexus("./../" + file, result[0], "./../" + settings)

        shutil.move("./../" + file, result[1] + file)
        time.sleep(300)
    tracemalloc.stop()
    print("The program is done sleeping! you can start it again.")


def start_thread():
    """Start the auto_generate function in a separate thread."""
    global STOP_THREAD
    STOP_THREAD = False
    thread = threading.Thread(target=auto_generate, daemon=True)
    thread.start()
    print("Auto-generation started!")


def stop_thread_func():
    """Stop the auto_generate function."""
    global STOP_THREAD
    STOP_THREAD = True
    print("Auto-generation stopped. The program is still sleeping!")


def create_gui():
    """Create the GUI with a Start and Stop button."""
    root = tk.Tk()
    root.title("Auto Generate Controller")

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

    # Run the GUI loop
    root.mainloop()


if __name__ == "__main__":
    create_gui()
