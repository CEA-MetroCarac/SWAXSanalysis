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
from saxs_nxformat import DICT_UNIT


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

    elif re.search("(^-?\\d*[.,]\\d*$)|(^-?\\d?[.,]?\\d*e[+-]\\d*$)", string.lower()):
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
    if unit_start == "arbitrary" or unit_end == "arbitrary" or number is None:
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

        number = number * (starting_unit / ending_unit)

    # print(number_start, unitStart, number, unitEnd)
    return number


def replace_h5_dataset(
        hdf5_file: h5py.File,
        dataset_h5path: str | pathlib.Path,
        new_dataset: int | float | np.ndarray,
        new_dataset_type,
        new_dataset_h5path: None | str | pathlib.Path = None,
) -> None:
    """
    Function used to replace a dataset that's already been created
    in a hdf5 file

    Parameters
    ----------
    hdf5_file :
        File containing the dataset

    dataset_h5path :
        Path of the dataset in the hdf5 file

    new_dataset :
        new value for the dataset

    new_dataset_type :
        type of the new dataset

    new_dataset_h5path :
        default is None. Change to change the name of the dataset as you replace it
    """
    # We get the old dataset and it's attributes and then delete it
    if dataset_h5path in hdf5_file:
        old_dataset = hdf5_file[dataset_h5path]
        attributes = dict(old_dataset.attrs)
        del hdf5_file[dataset_h5path]
    else:
        attributes = {"units": "1/nm"}

    # We create the new dataset with the new data provided
    if new_dataset_h5path:
        new_dataset = hdf5_file.create_dataset(
            new_dataset_h5path,
            data=new_dataset,
            dtype=new_dataset_type,
            compression="gzip",
            compression_opts=9
        )
    else:
        new_dataset = hdf5_file.create_dataset(
            dataset_h5path,
            data=new_dataset,
            dtype=new_dataset_type,
            compression="gzip",
            compression_opts=9
        )

    # We add the attributes to the new dataset so that we do not lose them
    for attr_name, attr_value in attributes.items():
        new_dataset.attrs[attr_name] = attr_value


def save_data(
        nx_file: h5py.File,
        parameter_symbol: str,
        parameter_data: np.ndarray,
        group_name: str,
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

    group_name :
        Name of the group containing all the data

    value_data :
        Contains the data
    """
    # We create the dataset h5path and if it exists we delete what was previously there
    group_name = group_name.upper()
    dataset_path = f"/ENTRY/{group_name}"
    if dataset_path in nx_file and group_name != "DATA":
        del nx_file[dataset_path]

    # we copy the raw data and set the copied data to the name selected
    # That way we also copy the attributes
    if group_name != "DATA":
        nx_file.copy("ENTRY/DATA", nx_file["/ENTRY"], group_name)

    # we replace the raw data with the new data
    # TODO : propagate uncertainties
    # Concerning Q
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/Q",
        parameter_data,
        parameter_data.dtype,
        f"{dataset_path}/{parameter_symbol}"
    )
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/Qdev",
        np.zeros(np.shape(parameter_data)),
        np.zeros(np.shape(parameter_data)).dtype
    )
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/dQl",
        np.zeros(np.shape(parameter_data)),
        np.zeros(np.shape(parameter_data)).dtype
    )
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/dQw",
        np.zeros(np.shape(parameter_data)),
        np.zeros(np.shape(parameter_data)).dtype
    )
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/Qmean",
        np.array([0]),
        np.array([0]).dtype
    )
    # Concerning I
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/I",
        value_data,
        value_data.dtype
    )
    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/Idev",
        np.zeros(np.shape(value_data)),
        np.zeros(np.shape(value_data)).dtype
    )

    replace_h5_dataset(
        nx_file,
        f"{dataset_path}/mask",
        mask,
        mask.dtype
    )

    dim = len(np.shape(nx_file[f"{dataset_path}/I"]))
    if dim == 1:
        del nx_file[f"{dataset_path}/mask"]

        del nx_file[f"{dataset_path}"].attrs["I_axes"]
        nx_file[f"{dataset_path}"].attrs["I_axes"] = "Q"

        del nx_file[f"{dataset_path}"].attrs["Q_indices"]
        nx_file[f"{dataset_path}"].attrs["Q_indices"] = [0]

        del nx_file[f"{dataset_path}"].attrs["mask_indices"]
        nx_file[f"{dataset_path}"].attrs["mask_indices"] = [0]
    elif dim == 2:
        del nx_file[f"{dataset_path}/Qdev"]
        del nx_file[f"{dataset_path}/dQl"]
        del nx_file[f"{dataset_path}/dQw"]


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
    group_name = group_name.upper()
    if group_name in nx_file["/ENTRY"]:
        del nx_file[f"/ENTRY/{group_name}"]
    else:
        print("This group does not exists")


def detect_variation(
        array: np.ndarray,
        variation_threshold: float | int
) -> None:
    """
    return the indices where we go from a value under low to a value aboce high

    Parameters
    ----------
    variation_threshold :
        Threshold at whoch the change is detected

    array :
        The array where the variation have to be detected

    low :
        low threshold

    high :
        high threshold

    Returns
    -------
    list of indices where the variations are detected
    """
    diff_array = np.diff(array)
    return np.where(diff_array > variation_threshold)[0] + 1


def mobile_mean(
        data: np.ndarray,
        nbr_neighbour: int = 5
) -> np.ndarray:
    if nbr_neighbour % 2 == 0:
        raise ValueError("nbr_neighbour doit être impair pour un lissage symétrique.")

    kernel = np.ones(nbr_neighbour) / nbr_neighbour
    smoothed_data = np.convolve(data, kernel, mode='valid')
    return smoothed_data


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

    def __init__(self, parent, *args, **kw):
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
                                width=200, height=500,
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
