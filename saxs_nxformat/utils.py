"""
Package-wide functions and classes
"""
import pathlib
import re
import tkinter as tk
from tkinter import ttk
from typing import Any

import h5py
import numpy as np
from . import DICT_UNIT


def string_2_value(
        string: str,
        unit_type: str = None
) -> str | int | float | None:
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
    unit_type :
        unit type according to NeXus

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
    if unit_type is not None and string == "":
        if unit_type == "NX_NUMBER":
            value = 0.0
        elif unit_type == "NX_CHAR":
            value = "N/A"
        elif unit_type == "NX_DATE_TIME":
            value = "0000-00-00T00:00:00"
        elif unit_type == "NX_BOOLEAN":
            value = False
        else:
            value = "None"

    elif re.search("(^none$)|(^defaul?t$)|(^$)", string.lower()):
        value = None

    elif re.search("(^-?\\d*[.,]?\\d*$)|([+-]?\\d+(\\.\\d*)?e[+-]?\\d+$)", string.lower()):
        value = float(string)

    elif re.search("^-?\\d+$", string):
        value = int(string)

    elif re.search("^true$", string.lower()):
        value = True

    elif re.search("^false$", string.lower()):
        value = False

    elif re.search("^[a-z]+_[a-z]+(_[a-z]+)*$", string.lower()):
        value = string.upper()

    else:
        value = string

    return value


def convert(
        number: float | int,
        unit_start: str,
        unit_end: str,
        testing: bool = False
) -> None | str | float | int | Any:
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
    if unit_start == "arbitrary" or unit_end == "arbitrary" or type(number) not in [int, float]:
        return number
    unit_type1 = None
    unit_type2 = None
    for key, value in DICT_UNIT.items():
        if unit_start in value:
            unit_type1 = key

        if unit_end in value:
            unit_type2 = key

    if unit_type1 is None or unit_type2 is None or unit_type1 != unit_type2 and not testing:
        tk.messagebox.showerror("Error",
                                f"The value {number} {unit_start} could not be converted to "
                                f"{unit_end} :\n")
    elif unit_type1 is None or unit_type2 is None or unit_type1 != unit_type2 and testing:
        return "fail"

    unit_type = unit_type1

    if unit_type == "NX_ANGLE":
        starting_unit = DICT_UNIT[unit_type][unit_start]
        intermediate_unit = DICT_UNIT[unit_type]["turn"]
        ending_unit = DICT_UNIT[unit_type][unit_end]

        number = number * (intermediate_unit / starting_unit)
        number = number * (ending_unit / intermediate_unit)
    elif unit_type == "NX_TEMPERATURE":
        starting_unit = DICT_UNIT[unit_type][unit_start]
        ending_unit = DICT_UNIT[unit_type][unit_end]
        if unit_end == "C":
            number = number - ending_unit
        else:
            number = number + starting_unit
    else:
        starting_unit = DICT_UNIT[unit_type][unit_start]
        ending_unit = DICT_UNIT[unit_type][unit_end]

        # print(number, starting_unit, ending_unit)
        number = number * (starting_unit / ending_unit)

    return number


def explore_file(group, explore_group=False, explore_dataset=False, level=0, base_path=""):
    paths = []

    for key in group.keys():
        item = group[key]
        full_path = f"{base_path}/{key}"

        if isinstance(item, h5py.Group):
            paths.append(full_path)
            paths.extend(explore_file(item, explore_group, explore_dataset, level + 1, full_path))
        elif isinstance(item, h5py.Dataset) and explore_group:
            paths.append(full_path)
            if item.attrs and explore_dataset:
                for key_attribute in item.attrs.keys():
                    paths.append(f"{full_path}/{key_attribute}")

    return paths


def extract_from_h5(
        nx_file: h5py.File,
        h5path: str,
        data_type: str = "dataset",
        attribute_name: str | None = None
) -> Any:
    """
    Method used to extract a dataset or attribute from the .h5 file

    Parameters
    ----------
    nx_file :
        file object

    h5path :
        h5 path of the dataset

    data_type :
        type of the value extracted (attribute or dataset)

    attribute_name :
        if it's an attribute, give its name

    Returns
    -------
    Either the attribute or dataset selected

    """
    # IF the path is correct We get the dataset and its attributes
    if h5path in nx_file:
        dataset = nx_file[h5path]
        attributes = dataset.attrs
    else:
        raise Exception(f"{h5path} is not in the file {nx_file}")

    # We detect if the dataset is a scalar, an array, bytes, or an attribute
    if data_type == "dataset" and np.shape(dataset) == ():
        return dataset[()]
    elif data_type == "dataset" and np.shape(dataset) != ():
        return dataset[:]
    elif data_type == "attribute" and attribute_name in attributes.keys():
        return attributes[attribute_name]
    else:
        return None


def replace_h5_dataset(
        hdf5_file: h5py.File,
        old_h5path: str,
        new_dataset: int | float | np.ndarray,
        new_h5path: None | str = None
) -> None:
    """
    Function used to replace a dataset that's already been created
    in a hdf5 file without changing the attributes

    Parameters
    ----------
    hdf5_file :
        File containing the dataset

    old_h5path :
        Path of the dataset to replace in the hdf5 file

    new_dataset :
        new value for the dataset

    new_h5path :
        default is None. Change to change the name of the dataset as you replace it
    """
    # We get the old dataset and it's attributes and then delete it
    if old_h5path in hdf5_file:
        old_dataset = hdf5_file[old_h5path]
        attributes = dict(old_dataset.attrs)
        del hdf5_file[old_h5path]
    else:
        attributes = {}

    # We create the new dataset with the new data provided
    if new_h5path:
        h5path = new_h5path
    else:
        h5path = old_h5path
    if isinstance(new_dataset, np.ndarray):
        new_dataset = hdf5_file.create_dataset(
            name=h5path,
            data=new_dataset,
            compression="gzip",
            compression_opts=9
        )
    else:
        new_dataset = hdf5_file.create_dataset(
            name=h5path,
            data=new_dataset
        )

    # We add the attributes to the new dataset so that we do not lose them
    for attr_name, attr_value in attributes.items():
        new_dataset.attrs[attr_name] = attr_value


def save_data(
        nx_file: h5py.File,
        new_group_name: str,
        parameter_symbol: str,
        parameter_data: np.ndarray,
        value_data: np.ndarray,
        mask: np.ndarray
) -> None:
    """
    Method used to save a dataset in the h5 file

    Parameters
    ----------
    mask :
        mask used for data treatment

    nx_file :
        file object

    parameter_symbol :
        Symbol of the parameter. will be the name of its dataset

    parameter_data :
        Contains the parameter data

    new_group_name :
        Name of the group containing all the data

    value_data :
        Contains the data
    """
    # We create the dataset h5path and if it exists we delete what was previously there
    new_group_name = new_group_name.upper()
    group_path = f"/ENTRY/{new_group_name}"
    if group_path in nx_file and new_group_name != "DATA":
        del nx_file[group_path]
    if new_group_name != "DATA":
        nx_file.copy("ENTRY/DATA", nx_file["/ENTRY"], new_group_name)

    # we replace the raw data with the new data
    # TODO : propagate uncertainties
    # Concerning Q
    replace_h5_dataset(
        nx_file,
        f"{group_path}/Q",
        parameter_data,
        f"{group_path}/{parameter_symbol}"
    )
    replace_h5_dataset(
        nx_file,
        f"{group_path}/Qdev",
        np.zeros(np.shape(parameter_data))
    )
    replace_h5_dataset(
        nx_file,
        f"{group_path}/Qmean",
        np.mean(parameter_data)
    )
    # Concerning I
    replace_h5_dataset(
        nx_file,
        f"{group_path}/I",
        value_data
    )
    replace_h5_dataset(
        nx_file,
        f"{group_path}/Idev",
        np.zeros(np.shape(value_data))
    )
    # Concerning the mask
    replace_h5_dataset(
        nx_file,
        f"{group_path}/mask",
        mask
    )

    dim = len(np.shape(value_data))
    if dim == 1:
        if f"{group_path}/mask" in nx_file:
            del nx_file[f"{group_path}/mask"]

        if f"{group_path}" in nx_file:
            del nx_file[f"{group_path}"].attrs["I_axes"]
            del nx_file[f"{group_path}"].attrs["Q_indices"]
            del nx_file[f"{group_path}"].attrs["mask_indices"]

        nx_file[f"{group_path}"].attrs["I_axes"] = "Q"
        nx_file[f"{group_path}"].attrs["Q_indices"] = [0]
        nx_file[f"{group_path}"].attrs["mask_indices"] = [0]
    elif dim == 2:
        if f"{group_path}/Qdev" in nx_file:
            del nx_file[f"{group_path}/Qdev"]


def delete_data(
        nx_file: h5py.File,
        group_name: str
) -> None:
    """
    Method used to properly delete data from the h5 file

    Parameters
    ----------
    nx_file :
        file object

    group_name :
        Name of the data group to delete
    """
    # We delete the data
    group_name = group_name.upper()
    if group_name in nx_file["/ENTRY"]:
        del nx_file[f"/ENTRY/{group_name}"]
    else:
        raise Exception(f"The group /ENTRY/{group_name} does not exist in the file {nx_file.filename}")

    # We delete the associated process
    process_name = group_name.removeprefix("DATA_")

    if process_name in nx_file["/ENTRY"]:
        del nx_file[f"/ENTRY/{process_name}"]
    else:
        raise Exception(f"The group /ENTRY/{process_name} does not exist in the file {nx_file.filename}")


def detect_variation(
        array: np.ndarray,
        relative_tol: float | int
) -> np.ndarray:
    """
    return the indices where we go from a value under low to a value aboce high

    Parameters
    ----------
    variation_threshold :
        Threshold at which the change is detected

    array :
        The array where the variation have to be detected

    Returns
    -------
    list of indices where the variations are detected
    """

    diff_array = np.diff(array)
    # print("np.diff :\n", diff_array)
    # print("np.where :\n", np.where(diff_array > relative_tol*array[1:]))
    # We ignore the values where the array is equal to zero (relative tol doesn't make sense)
    non_zero_mask = array[1:] != 0
    # We build the condition
    condition = np.abs(diff_array[non_zero_mask]) > np.abs(relative_tol * array[1:][non_zero_mask])
    # We get the indices
    indices = np.where(non_zero_mask)[0][condition] + 1
    return indices


class VerticalScrolledFrame(ttk.Frame):
    """
    A scrollable frame widget using a canvas and a vertical scrollbar.

    This class creates a scrollable frame, allowing content
    larger than the visible area to be scrolled vertically.
    It is based on the implementation from:
    https://coderslegacy.com/python/make-scrollable-frame-in-tkinter/

    Parameters
    ----------
    parent : tk.Widget
        The parent widget in which the scrollable frame will be placed.
    *args : tuple
        Additional positional arguments to pass to the ttk.Frame initializer.
    **kw : dict
        Additional keyword arguments to pass to the ttk.Frame initializer.
    """

    def __init__(self, parent, width=200, height=500, *args, **kw):
        """
        Initialize the VerticalScrolledFrame.

        Parameters
        ----------
        parent :
            The parent widget in which the scrollable frame will be placed.
        *args :
            Additional positional arguments to pass to the ttk.Frame initializer.
        **kw :
            Additional keyword arguments to pass to the ttk.Frame initializer.
        """
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                                width=width, height=height,
                                yscrollcommand=vscrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        vscrollbar.config(command=self.canvas.yview)

        # Reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = ttk.Frame(self.canvas)
        self.interior.columnconfigure(1, weight=1)
        self.interior.bind('<Configure>', self._configure_interior)
        self.canvas.bind('<Configure>', self._configure_canvas)
        self.interior_id = self.canvas.create_window(0, 0, window=self.interior,
                                                     anchor=tk.NW)

    def _configure_interior(self, event):
        """
        Update the scroll region of the canvas to match the size of the inner frame.

        Parameters
        ----------
        event : tk.Event
            The event object containing information about the configuration change.
        """
        size = (self.interior.winfo_reqwidth(), self.interior.winfo_reqheight())
        self.canvas.config(scrollregion=(0, 0, size[0], size[1]))
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the canvas's width to fit the inner frame.
            self.canvas.config(width=self.interior.winfo_reqwidth())

    def _configure_canvas(self, event):
        """
        Update the inner frame's width to match the canvas's width.

        Parameters
        ----------
        event : tk.Event
            The event object containing information about the configuration change.
        """
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the inner frame's width to fill the canvas.
            self.canvas.itemconfigure(self.interior_id,
                                      width=self.canvas.winfo_width())
