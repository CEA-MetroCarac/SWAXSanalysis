"""
This module is meant to be executed by the user and automatically
treats any .edf file found in the parent folder according to the
settings file also present in that parent folder
"""
import gc
import glob
import json
import os
import pathlib
import shutil
import threading
import time
import tkinter as tk
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Tuple

import fabio
from fabio.edfimage import EdfImage
import h5py
import numpy as np

from . import FONT_TITLE, FONT_BUTTON, FONT_LOG
from . import ICON_PATH, TREATED_PATH, QUEUE_PATH, DTC_PATH
from .class_nexus_file import NexusFile
from .utils import string_2_value, save_data, extract_from_h5, convert

import cProfile
import pstats


def treated_data(settings_path):
    with open(settings_path, "r", encoding="utf-8") as config_file:
        config_dict = json.load(config_file)

    # We build the set of existing .h5
    existing_h5 = set()
    for filepath in glob.iglob(str(TREATED_PATH / "**/*.h5"), recursive=True):
        existing_h5.add(filepath)

    edf_to_treat = {}
    for filepath in glob.iglob(str(QUEUE_PATH / "**/*.edf"), recursive=True):
        if len(filepath) >= 256:
            continue
        filepath = Path(filepath).absolute()
        target_dir = tree_structure_manager(filepath, settings_path)
        h5_file_path = generate_h5_path(config_dict, filepath, target_dir).absolute()
        if h5_file_path not in existing_h5:
            edf_to_treat[filepath] = h5_file_path

    if len(edf_to_treat) == 0:
        edf_to_treat = None

    return edf_to_treat


def data_treatment(
        data: np.ndarray,
        h5_file: h5py.File
) -> dict[str, np.ndarray | list[any]]:
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
    x_list = np.linspace(0 - beam_center_x, dim[1] - beam_center_x, dim[1], dtype=np.float32)
    y_list = np.linspace(0 - beam_center_y, dim[0] - beam_center_y, dim[0], dtype=np.float32)

    x_pixel_size = h5_file["/ENTRY/INSTRUMENT/DETECTOR/x_pixel_size"][()]
    y_pixel_size = h5_file["/ENTRY/INSTRUMENT/DETECTOR/y_pixel_size"][()]

    x_list = x_list * x_pixel_size
    y_list = y_list * y_pixel_size

    x_grid, y_grid = np.meshgrid(x_list, y_list)
    r_grid = np.stack((x_grid, y_grid), axis=-1)

    r_grid = np.moveaxis(r_grid, (0, 1, 2), (1, 2, 0))

    data_i = np.array(data, dtype=np.float32)

    logical_mask = np.logical_not(data_i > -1)

    output = {
        "R_data": np.array(r_grid),
        "I_data": np.array(data_i),
        "mask": np.array([logical_mask])
    }

    return output


def generate_nexus(
        edf_path: str | Path,
        hdf5_path: str | Path,
        settings_path: str | Path,
        is_db: bool = False
) -> str:
    """
    The main function. it creates the hdf5 file and fills all it's content
    automatically using a settings file.

    Parameters
    ----------
    is_db :
        flag to know if the data is a direct beam data

    edf_path :
        Path of the original file

    hdf5_path :
        Path of the directory where the new file is supposed to go

    settings_path :
        Path of the settings file
    """
    edf_path = Path(edf_path)
    edf_name = edf_path.name
    edf_file = fabio.open(edf_path)
    edf_header = edf_file.header
    edf_data = edf_file.data

    def fill_hdf5(file, dict_content, parent_element=None):
        utf8_dtype = h5py.string_dtype(encoding="utf-8")

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
                if isinstance(dataset_value, str):
                    dtype = utf8_dtype
                    current_element = parent_element.create_dataset(
                        clean_key,
                        dtype=dtype,
                        data=dataset_value
                    )
                else:
                    current_element = parent_element.create_dataset(
                        clean_key,
                        data=dataset_value
                    )
                if content:
                    fill_hdf5(file, content, current_element)

            elif element_type == "attribute":
                if not (isinstance(value["value"], list)):
                    attribute_value = edf_header.get(value["value"], value["value"])
                else:
                    attribute_value = value["value"][1]
                if clean_key != "version":
                    attribute_value = string_2_value(str(attribute_value), value["type"])
                parent_element.attrs[clean_key] = attribute_value

    # We save the data
    if hdf5_path.exists():
        if is_db:
            string_hdf5_path = str(hdf5_path)
            string_hdf5_path = string_hdf5_path.removesuffix(".h5")
            hdf5_path = Path(string_hdf5_path + "_DB.h5")
        else:
            raise Exception(f"{hdf5_path} already exists")

    target_dir = hdf5_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "r", encoding="utf-8") as config_file:
        config_dict = json.load(config_file)

    with h5py.File(hdf5_path, "w") as save_file:
        fill_hdf5(save_file, config_dict)

        treated_data = data_treatment(edf_data, save_file)

        save_data(
            save_file,
            "DATA",
            "Q",
            treated_data["R_data"],
            treated_data["I_data"],
            treated_data["mask"]
        )

        del save_file["ENTRY/DATA"].attrs["I_axes"]
        save_file["ENTRY/DATA"].attrs["I_axes"] = ["Q", "Q"]
        del save_file["ENTRY/DATA"].attrs["Q_indices"]
        save_file["ENTRY/DATA"].attrs["Q_indices"] = [0, 1]
        del save_file["ENTRY/DATA"].attrs["mask_indices"]
        save_file["ENTRY/DATA"].attrs["mask_indices"] = [0, 1]

        do_absolute = extract_from_h5(save_file, "ENTRY/COLLECTION/do_absolute_intensity")
        if do_absolute and not is_db:
            db_path = Path(extract_from_h5(
                save_file,
                "ENTRY/COLLECTION/do_absolute_intensity",
                "attribute",
                "dbpath")
            )
            db_path = pathlib.Path(*db_path.parts[1:])

            # trick : we don't know when the path is going to be valid, so we strip the first part
            # of the path util there is a match
            do_while = True
            while len(db_path.parts[1:]) != 0 and do_while:
                try:
                    db_hdf5_path = generate_nexus(
                        QUEUE_PATH / db_path,
                        hdf5_path,
                        settings_path,
                        is_db=True
                    )
                    do_while = False
                except Exception as exception:
                    db_path = pathlib.Path(*db_path.parts[1:])

    if do_absolute == 1 and not is_db:
        nx_file = NexusFile([hdf5_path], do_batch=False)
        try:
            nx_file.process_absolute_intensity(
                db_hdf5_path,
                group_name="DATA_ABS",
                save=True
            )
        except Exception as error:
            raise error
        finally:
            nx_file.nexus_close()

    return str(hdf5_path)


def search_setting() -> None | Path:
    """
    This function searches the settings file
    in the DTC folder

    Returns
    -------
    settings_path : Path
        Path of the settings file.
    """
    settings_name = None
    for file in os.listdir(DTC_PATH):
        if "settings_edf2nx" in file.lower():
            settings_name = file
    if settings_name is None:
        return None
    else:
        settings_path = Path(DTC_PATH / settings_name)

    return Path(settings_path)


def generate_h5_path(
        config_dict,
        edf_path,
        destination_folder
):
    """
    Extremely dependent of how the files are named

    Parameters
    ----------
    edf_path :
        Path of the edf file to convert

    destination_folder :
        Folder where the h5 file is to be saved

    Returns
    -------
    h5_file_path :
        The complete h5 file path

    """
    edf_name = edf_path.name
    edf_file = EdfImage()
    edf_file.read(edf_path)
    edf_header = edf_file.header

    sample_name_key = config_dict["/ENTRY"]["content"]["/SAMPLE"]["content"]["name"]["value"]
    sample_name = edf_header.get(sample_name_key, "defaultSampleName")

    #######################
    ### Xeuss dependent ###
    #######################
    split_edf_name = edf_name.removesuffix(".edf").split("_")

    if split_edf_name[-2] == "0":
        detector = "SAXS"
    elif split_edf_name[-2] == "1":
        detector = "WAXS"
    else:
        detector = "other"

    final_name = f"{sample_name}_{detector}_img{split_edf_name[-1]}.h5"
    #######################
    ### Xeuss dependent ###
    #######################

    h5_file_path = Path(destination_folder) / final_name

    return Path(h5_file_path)


def tree_structure_manager(
        file_path: str | Path,
        settings_path: str | Path
) -> str | Path:
    """
    Creates a structured folder hierarchy based on the EDF file path and settings file.

    Parameters
    ----------
    file_path : str
        Name of the EDF file to be converted.
    settings_path : str
        Name of the settings file used for conversion.

    Returns
    -------
    tuple[str, str] | str
        - The paths where FDH5 and EDF5 files should be saved.
        - An error message in case of a permission issue.
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    if not isinstance(settings_path, Path):
        settings_path = Path(settings_path)

    settings = settings_path.name

    # Dissecting the settings file name
    settings = settings.removeprefix("settings_")
    try:
        origin2ending, instrument, _ = settings.rsplit("_", 2)
    except ValueError:
        return "Invalid settings file format"

    origin_format, ending_format = origin2ending.split("2")

    target_dir = (
            TREATED_PATH /
            f"instrument - {instrument}" /
            file_path.relative_to(QUEUE_PATH).parent
    )

    try:
        return target_dir
    except Exception as exception:
        raise exception


class GUI_generator(tk.Frame):
    """
    This class is used to build a GUI for the control panel
    """

    def __init__(self, parent=None, jenkins=False) -> None:
        self.jenkins = jenkins

        self.activate_thread = False
        self.line_dict = {}

        if not self.jenkins:
            super().__init__(parent)
            self.columnconfigure(1, weight=2)
            self.rowconfigure(0, weight=1)

            self.control_panel = tk.Frame(self, padx=5, pady=5, border=5, relief="ridge")
            self.control_panel.grid(column=0, row=0, padx=5, pady=5, sticky="news")
            self.columnconfigure(0, weight=1)
            self._build_control_frame()

            self.log_panel = tk.Frame(self, padx=5, pady=5, border=5, relief="ridge")
            self.log_panel.grid(column=1, row=0, padx=5, pady=5, sticky="news")
            self.log_panel.rowconfigure(1, weight=1)
            self._build_log_frame()

    def _build_control_frame(self) -> None:
        self.control_panel.columnconfigure(0, weight=1)

        # Label
        title = tk.Label(
            self.control_panel,
            text="Auto conversion control panel",
            font=FONT_TITLE
        )
        title.grid(pady=10, padx=10, row=0, column=0)

        # Start Button
        start_button = tk.Button(
            self.control_panel,
            text="Start",
            command=self.start_thread,
            bg="#25B800",
            fg="white",
            padx=10,
            font=FONT_BUTTON
        )
        start_button.grid(padx=10, pady=10, row=1, column=0)

        # Stop Button
        stop_button = tk.Button(
            self.control_panel,
            text="Stop",
            command=self.stop_thread_func,
            bg="#D9481C",
            fg="white",
            padx=10,
            font=FONT_BUTTON
        )
        stop_button.grid(padx=10, pady=10, row=2, column=0)

    def _build_log_frame(self) -> None:
        self.log_panel.columnconfigure(0, weight=1)
        self.log_panel.rowconfigure(1, weight=1)

        # Label
        title = tk.Label(
            self.log_panel,
            text="Console log",
            font=FONT_TITLE
        )
        title.grid(pady=10, padx=10, row=0, column=0)

        # Log output area
        self.log_text = tk.Text(
            self.log_panel,
            height=20,
            width=50,
            font=FONT_LOG
        )
        self.log_text.grid(pady=10, padx=10, row=1, column=0, sticky="news")
        self.log_text.config(state=tk.NORMAL)

    def print_log(
            self,
            message: str
    ) -> None:
        """Function to print logs in the Tkinter Text widget."""

        def generate_message():
            self.log_text.insert(tk.END, message + "\n\n")
            self.log_text.see(tk.END)

        if self.jenkins:
            print(message)
        else:
            self.after(
                0,
                generate_message()
            )

    def auto_generate(self) -> None:
        """
        This is a thread that runs continuously
        and tries to export edf files found in the parent folder
        into h5 files using the settings file found in the same folder.
        """
        # profiler = cProfile.Profile()
        # profiler.enable()

        tracemalloc.start()
        start_time = time.time()
        sleep_time = 10

        settings_path = search_setting()
        self.print_log(
            "Building list of files to process. This may take a while"
        )
        edf_to_treat = treated_data(settings_path)
        self.print_log(
            "The list of files to process has been built."
        )

        while self.activate_thread:
            if self.jenkins and time.time() - start_time > 600:
                break
            current, peak = tracemalloc.get_traced_memory()

            self.print_log(
                f"Memory used:\n"
                f"  - Current: {current / (1024 ** 2):.2f} MB\n"
                f"  - Peak: {peak / (1024 ** 2):.2f} MB"
            )

            if peak / (1024 ** 2) > 500 or current / (1024 ** 2) > 500:
                self.print_log(
                    f"Too much memory used: {current}, {peak}"
                )
                break

            if settings_path is None:
                self.print_log(
                    f"No settings file found, sleeping for {sleep_time} seconds.\n"
                    f"You can close or stop safely."
                )
                time.sleep(sleep_time)
                continue

            if edf_to_treat is None:
                self.print_log(
                    f"No edf file found, sleeping for {sleep_time} seconds.\n"
                    f"You can close or stop safely."
                )
                time.sleep(sleep_time)
                continue

            file_path, h5_file_path = next(iter(edf_to_treat.items()))

            self.print_log(
                f"Converting : {file_path.name}, please wait"
            )

            try:
                new_file_path = generate_nexus(file_path, h5_file_path, settings_path)
            except Exception as exception:
                self.print_log(
                    str(exception)
                )
                continue

            self.print_log(
                f"{file_path.name} has been converted successfully\n"
            )

            # We decide whether we want to do absolute intensity treatment or not
            with h5py.File(new_file_path, "r") as h5obj:
                do_absolute = h5obj.get("/ENTRY/COLLECTION/do_absolute_intensity", False)[()]
            if do_absolute == 1:
                input_group = "DATA_ABS"
            else:
                input_group = "DATA"

            # We then do the absolute treatment
            self.print_log(
                f"Opening {Path(new_file_path).name} using {input_group} as base data"
            )
            nx_file = None
            try:
                nx_file = NexusFile([new_file_path], input_data_group=input_group)
                # Do Q space
                self.print_log(
                    "Doing q space..."
                )
                nx_file.process_q_space(save=True)
                self.print_log(
                    "q space done."
                )

                # Do radial average
                self.print_log(
                    "Doing radial integration"
                )
                nx_file.process_radial_average(save=True)
                self.print_log(
                    "radial integration done."
                )
            except Exception as exception:
                self.print_log(
                    str(exception)
                )
                continue
            finally:
                if nx_file is not None:
                    nx_file.nexus_close()

            del nx_file
            del edf_to_treat[file_path]
            gc.collect()
            # print(time.time() - start_time)

        tracemalloc.stop()
        self.print_log(
            "The program is done! you can close or start it again."
        )

        # profiler.disable()
        # stats = pstats.Stats(profiler).sort_stats('cumtime')
        # stats.print_stats()

    def start_thread(self) -> None:
        """Start the auto_generate function in a separate thread."""
        self.activate_thread = True
        thread = threading.Thread(target=self.auto_generate, daemon=True)
        thread.start()
        self.print_log(
            "Auto-generation started!"
        )

    def stop_thread_func(self) -> None:
        """Stop the auto_generate function."""
        self.activate_thread = False
        self.print_log(
            "Auto-generation stopped. The program is still processing!"
        )
