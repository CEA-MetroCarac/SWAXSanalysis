"""
Package-wide functions and classes
"""
import re
import tkinter as tk
from tkinter import ttk

import numpy as np
from saxs_nxformat import DICT_UNIT


def string_2_value(string: str, unit_type: str = None) -> str | int | float | None:
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


def replace_h5_dataset(hdf5_file, dataset_h5path, new_dataset, new_dataset_h5path=None):
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

    new_dataset_h5path :
        default is None. Change to change the name of the dataset as ou replace it
    """
    # We get the old dataset and it's attributes and then delete it
    old_dataset = hdf5_file[dataset_h5path]
    attributes = dict(old_dataset.attrs)
    del hdf5_file[dataset_h5path]

    # We create the new dataset with the new data provided
    if new_dataset_h5path:
        new_dataset = hdf5_file.create_dataset(new_dataset_h5path,
                                               data=new_dataset,
                                               compression="gzip",
                                               compression_opts=9)
    else:
        new_dataset = hdf5_file.create_dataset(dataset_h5path,
                                               data=new_dataset,
                                               compression="gzip",
                                               compression_opts=9)

    # We add the attributes to the new dataset so that we do not lose them
    for attr_name, attr_value in attributes.items():
        new_dataset.attrs[attr_name] = attr_value

def detect_variation(array, variation_threshold):
    """
    return the indices where we go from a value under low to a value aboce high

    Parameters
    ----------
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
