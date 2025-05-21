"""
This module is meant to be executed by the user and automatically
treats any .edf file found in the parent folder according to the
settings file also present in that parent folder
TODO : force rad_avg just like q_space
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

import fabio
import h5py
import numpy as np

from . import FONT_TITLE, FONT_BUTTON, FONT_LOG
from . import ICON_PATH, TREATED_PATH, QUEUE_PATH, DTC_PATH
from .class_nexus_file import NexusFile
from .utils import string_2_value, save_data, extract_from_h5, convert


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

    with open(settings_path, "r", encoding="utf-8") as config_file:
        config_dict = json.load(config_file)

    # We build the file name
    # TODO : Think of a better file name template
###########################
### Xeuss specific part ###
###########################
    sample_name_key = config_dict["/ENTRY"]["content"]["/SAMPLE"]["content"]["name"]["value"]
    sample_name = edf_header.get(sample_name_key, "defaultSampleName")
    if is_db:
        sample_name = sample_name + "DB"
    current_time = datetime.now()
    time_stamp = str(current_time.strftime("%Y%m%d%H%M%S"))
    split_edf_name = edf_name.removesuffix(".edf").split("_")

    if is_db:
        final_name = f"{sample_name}_img{split_edf_name[-1]}.h5"
    else:
        final_name = f"{sample_name}_img{split_edf_name[-1]}_{time_stamp}.h5"
###########################
### Xeuss specific part ###
###########################

    hdf5_path = Path(
        os.path.join(
            hdf5_path, final_name
        )
    )

    # We save the data
    if hdf5_path.exists():
        pass

    with h5py.File(hdf5_path, "w") as save_file:
        # TODO : compute real uncertainties here
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
            # TODO : find db_path, extract data, put in file under DATA_DIRECT_BEAM
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
                        hdf5_path.parents[0],
                        settings_path,
                        is_db=True
                    )
                    do_while = False
                except Exception as _:
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
            print(error)
        finally:
            nx_file.nexus_close()

    return str(hdf5_path)


def search_setting_edf(
        recursively: bool = False
) -> tuple[None, None] | tuple[None | str | Path, Path]:
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
    edf_name, settings_name, edf_original_path = None, None, None

    # First, we try to get the settings file
    for file in os.listdir(DTC_PATH):
        if "settings_edf2nx" in file.lower():
            settings_name = file
    if settings_name is None:
        return None, None
    else:
        settings_path = Path(DTC_PATH / settings_name)

    # Second, we build the list of all edf path in the DTC
    treated_edf = []
    for filepath in glob.iglob(str(TREATED_PATH / "**/*.edf"), recursive=True):
        treated_edf.append(Path(filepath))

    # Recursively searching in treatment queue for files to treat
    if recursively:
        for filepath in glob.iglob(str(QUEUE_PATH / "**/*.edf"), recursive=True):
            filepath = Path(filepath)
            result = tree_structure_manager(filepath, settings_path)
            edf_name = filepath.name
            if result[-1] / edf_name not in treated_edf:
                edf_original_path = filepath
    else:
        # Search in data treatment center only
        for file in os.listdir(DTC_PATH):
            if ".edf" in file.lower():
                edf_name = file
                edf_original_path = Path(DTC_PATH / edf_name)

    if edf_original_path is None:
        return None, None

    return Path(edf_original_path), Path(settings_path)


def tree_structure_manager(
        file_path: str | Path,
        settings_path: str | Path
) -> str | tuple[any, any]:
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

    common_path = (
            TREATED_PATH /
            f"instrument - {instrument}" /
            file_path.relative_to(QUEUE_PATH).parent
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
    """
    This class is used to build a GUI for the control panel
    """

    def __init__(self) -> None:
        self.activate_thread = False
        self.line_dict = {}

        super().__init__()
        self.title("Auto Generate Controller")
        self.iconbitmap(ICON_PATH)
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

        # Close Button
        close_button = tk.Button(
            self.control_panel,
            text="Close",
            command=self.close,
            bg="#DBDFAC",
            fg="black",
            padx=10,
            font=FONT_BUTTON
        )
        close_button.grid(pady=10, padx=10, row=7, column=0)

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
        self.log_text.insert(tk.END, message + "\n\n")
        self.log_text.see(tk.END)

    def auto_generate(self) -> None:
        """
        This is a thread that runs continuously
        and tries to export edf files found in the parent folder
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

            file_path, settings_path = search_setting_edf(recursively=True)
            if file_path is None or settings_path is None:
                self.after(
                    0,
                    self.print_log,
                    f"No file found, sleeping for {sleep_time} seconds.\n"
                    f"You can close or stop safely."
                )
                time.sleep(sleep_time)
                continue

            result = tree_structure_manager(file_path, settings_path)
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

            try:
                new_file_path = generate_nexus(file_path, result[0], settings_path)
            except Exception as exception:
                self.after(
                    0,
                    self.print_log,
                    str(exception)
                )
                raise exception
            finally:
                shutil.copy(file_path, result[1] / file_path.name)

            self.after(
                0,
                self.print_log,
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
            self.after(
                0,
                self.print_log,
                f"Opening {Path(new_file_path).name} using {input_group} as base data"
            )
            nx_file = None
            try:
                nx_file = NexusFile([new_file_path], input_data_group=input_group)
                # Do Q space
                self.after(
                    0,
                    self.print_log,
                    "Doing q space..."
                )
                nx_file.process_q_space(save=True)
                self.after(
                    0,
                    self.print_log,
                    "q space done."
                )

                # Do radial average
                self.after(
                    0,
                    self.print_log,
                    "Doing radial integration"
                )
                nx_file.process_radial_average(save=True)
                self.after(
                    0,
                    self.print_log,
                    "radial integration done."
                )
            except Exception as exception:
                self.after(
                    0,
                    self.print_log,
                    str(exception)
                )
                raise Exception
            finally:
                if nx_file is not None:
                    nx_file.nexus_close()

            del nx_file
            gc.collect()
        tracemalloc.stop()
        self.after(
            0,
            self.print_log,
            "The program is done! you can close or start it again."
        )

    def start_thread(self) -> None:
        """Start the auto_generate function in a separate thread."""
        self.activate_thread = True
        thread = threading.Thread(target=self.auto_generate, daemon=True)
        thread.start()
        self.after(
            0,
            self.print_log,
            "Auto-generation started!"
        )

    def stop_thread_func(self) -> None:
        """Stop the auto_generate function."""
        self.activate_thread = False
        self.after(
            0,
            self.print_log,
            "Auto-generation stopped. The program is still processing!"
        )

    def close(self) -> None:
        """
        Properly closes the window
        """
        self.destroy()


if __name__ == "__main__":
    import cProfile
    import pstats

    profiler = cProfile.Profile()
    profiler.enable()
    app = GUI_generator()
    app.mainloop()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats()
