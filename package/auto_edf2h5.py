"""
This module can be run one time in a python venv to automatically convert edf
files that are in the parent folder into an .h5 file. It will also classify the
input and output in an organized tree structure.
"""

import shutil
import threading
import time
import tracemalloc
import ast
import re
import copy
import os
import sys
import fabio

from .nexus_format import dictParamNXsas
from .nexus_generation import generate_nxsas_file


def string_2_value(string: str) -> str | int | float | None:
    """
    This function convert a string to a :
        - A float if it has the format X.Y or XeY
        - An int if it has the format XXXX
        - A None if the string is "" or "None"
        - A lowered version of the string otherwise
    Parameters
    ----------
    string
        The string that is to be converted

    Returns
    -------

    """
    if re.search("(^-?\\d*[.,]\\d*$)|(^-?\\d?[.,]\\d*e[+-]\\d*$)", string):
        value = float(string)
    elif re.search("^-?\\d+$", string):
        value = int(string)
    elif string.lower().strip() in ["none", ""]:
        value = None
    else:
        value = str(string).lower()

    return value


def load_edf(file_path):
    """
    Loads the EDF file

    Returns
    -------
    file_edf
        The file that needed to be loaded
    """
    file_edf = fabio.open(file_path)
    return file_edf


def load_autofill(settings_path):
    """
    Loads the settings file and store the settings in a variable
    """
    with open(settings_path, "r", encoding="UTF-8") as settings_file:
        autofill_settings = ast.literal_eval(f"{settings_file.readline()}")
    return autofill_settings


def autofill(file_path, settings_path):
    """
    Autofill the parameters if a settings file is provided
    """
    filled_dict = copy.deepcopy(dictParamNXsas)

    # We load the settings file for the autofill
    autofill_settings = load_autofill(settings_path)

    file_edf = load_edf(file_path)

    edf_header = file_edf.header
    edf_header = dict(edf_header)
    edf_data = file_edf.data

    for key_nx in dictParamNXsas:
        if key_nx in autofill_settings.keys():
            key_edf = str(autofill_settings[key_nx][0])
            unit_edf = str(autofill_settings[key_nx][1])

            filled_dict[key_nx][1] = string_2_value(edf_header[key_edf].lower())

            if "units" in filled_dict[key_nx][3].keys():
                filled_dict[key_nx][3]["units"] = unit_edf

    return filled_dict, edf_data


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
    for file in os.listdir("./.."):
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
    Eitjer :
        - The folder we want to put the h5 file in and the folder we to put the old edf file in

        - "perm error" if there is a permission error
    """
    # File splitting
    split_string = file.split("_")
    sample_name = split_string[0]
    experiment_type = split_string[1]
    if ".edf" in experiment_type:
        experiment_type = experiment_type.strip(".edf")

    # Settings splitting
    settings.strip("settings_")
    useless1, origin2ending, instrument, date_txt = settings.split("_")
    origin_format, ending_format = origin2ending.split("2")
    date = date_txt.strip(".txt")

    target_dir = "./.." + \
                 f"/instrument - {instrument}" + \
                 f"/config - {date}" + \
                 f"/sample - {sample_name}" + \
                 f"/experiment - {experiment_type}" + \
                 f"/format - {ending_format}/"
    other_dir = "./.." + \
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


def auto_generate():
    """
    This is a thread that runs continuously and tries to export edf files found in the parent folder
    into h5 files using the settings file found in the same folder.
    """
    condition = True
    tracemalloc.start()
    while condition:
        current, peak = tracemalloc.get_traced_memory()
        if peak / (1024 ** 2) > 20 or current / (1024 ** 2) > 20:
            condition = False

        file, settings = search_setting_edf()
        if file is None or settings is None:
            time.sleep(300)
            continue

        header, data = autofill("./../" + file, "./../" + settings)
        result = tree_structure_manager(file, settings)
        if result[0] == "perm error":
            sys.exit()
        generate_nxsas_file(header, data, result[0])

        shutil.move("./../" + file, result[1] + file)
        time.sleep(300)
    tracemalloc.stop()


if __name__ == '__main__':
    thread = threading.Thread(target=auto_generate)
    thread.daemon = False
    thread.start()
