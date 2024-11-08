"""
This file allows the user to open and modify an .h5 file
"""
import tkinter as tk
import os
import re
import copy
from tkinter import ttk, filedialog
import numpy as np
import h5py

from .nexus_format import dictParamNXsas, dictUnit
from .nexus_generation import generate_nxsas_file


def quit_program(root: tk.Tk) -> None:
    """
    This function closes the GUI and exits the program
    Parameters
    ----------
    root
        The root window for the GUI
    -------

    """
    root.destroy()


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
    if re.search(r"(^-?\d*[.,]\d*$)|(^-?\d?[.,]\d*e[+-]\d*$)", string):
        value = float(string)
    elif re.search(r"^-?\d+$", string):
        value = int(string)
    elif string.lower().strip() in ["none", ""]:
        value = None
    else:
        value = str(string).lower()

    return value


def remove_widgets(frame: tk.Frame) -> None:
    """
    This function closes all the widgets in a frame
    Parameters
    ----------
    frame
        the frame that needs to be purged
    -------

    """
    for widget in frame.winfo_children():
        widget.destroy()


def _browse_file(widget: tk.Entry, string_var: tk.StringVar) -> None:
    """
    This function fills an Entry widget with the absolute path of a selected file
    Parameters
    ----------
    widget
        The entry widget that is to be filled
    string_var
        The tkinter textvariable of that widget
    -------

    """
    filename = filedialog.askopenfilename(initialdir="./",
                                          title="Select a File",
                                          filetypes=(
                                              ("HDF5 Files", "*.h5"), ("all files", "*.*")))

    string_var.set(filename)
    widget.configure(textvariable=string_var)


class VerticalScrolledFrame(ttk.Frame):
    """
    This class creates a scrollable frame

    This class comes from this webpage :
    https://coderslegacy.com/python/make-scrollable-frame-in-tkinter/
    """

    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                                width=200, height=300,
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
        self.interior_id = self.canvas.create_window(0, 0, window=self.interior, anchor=tk.NW)

    def _configure_interior(self, event):
        # Update the scrollbars to match the size of the inner frame.
        size = (self.interior.winfo_reqwidth(), self.interior.winfo_reqheight())
        self.canvas.config(scrollregion=(0, 0, size[0], size[1]))
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the canvas's width to fit the inner frame.
            self.canvas.config(width=self.interior.winfo_reqwidth())

    def _configure_canvas(self, event):
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the inner frame's width to fill the canvas.
            self.canvas.itemconfigure(self.interior_id, width=self.canvas.winfo_width())


class Application(tk.Tk):
    """
    This class creates the advanced application.

    Attributes
    ----------
    do_advanced : bool
        Is the app launched in advanced mode ?

    frame1 : tk.Frame
        the frame containing the browsing option and autofill options

    label_data : tk.Label
        the label used to identify the entry box that accepts the data file's path

    entry_datapath : tk.Label
        The entry box that accepts the data file's path

    button_browse_datapath : tk.Button
        The button that allows browsing of the data file

    button_autofill : tk.Button
        The button that autofill frame2

    frame2 : VerticalScrolledFrame
        Scrollable frame containing all the parameters from NeXus with fillable entryboxes and
        combobox for the units

    frame3 : tk.Frame
        the frame containing the quit and export button

    button_quit : tk.Button
        The button used to exit the program

    button_export : tk.Button
        The button used to export the file to NeXus format



    """

    def __init__(self, do_advanced):
        super().__init__()
        self.do_advanced = do_advanced

        self.focus_force()

        # Initialisation of the root window
        self.title(".edf to .h5 converter")
        self.geometry("700x500")

        # Initialisation of the frame that has the browsing and configuration buttons
        self.frame1 = tk.Frame(self)
        self.frame1.pack(padx=8, pady=8, fill="x")
        self.frame1.columnconfigure(1, weight=1)
        self._create_widgets_frame1()

        # Initialisation of the frame that has the parameters
        self.frame2 = VerticalScrolledFrame(self)
        if self.do_advanced:
            self.label_param = tk.Label(self, text="Nexus parameters")
            self.label_param.pack()
            self.frame2.pack(padx=8, pady=8, fill="x")
        self._create_widget_frame2(dictParamNXsas)

        # Initialisation of the frame that has the close and export buttons
        self.frame3 = tk.Frame(self)
        self.stringar_entry_save = tk.StringVar()
        self.frame3.pack(padx=8, pady=8, fill="x")
        self._create_widget_frame3()

    def _create_widgets_frame1(self):
        """
        Creates the widget of frame 1 :

        - A labeled entry bow that can be filles via browsing for both the data and settings file
        - A button that autofill the parameters if a settings file is provided
        - A button that opens a new window to create a settings file
        """

        # The Data row which contains a label, entry and browse button
        self.label_data = tk.Label(self.frame1, text="Absolute path of the file")
        self.label_data.grid(column=0, row=0, sticky="w")

        self.stringvar_datapath = tk.StringVar()
        self.stringvar_datapath.set("")
        self.entry_datapath = ttk.Entry(self.frame1, textvariable=self.stringvar_datapath)
        self.entry_datapath.grid(column=1, row=0, sticky="we")

        self.button_browse_datapath = tk.Button(
            self.frame1,
            text="browse",
            command=lambda: _browse_file(self.entry_datapath,
                                         self.stringvar_datapath)
        )
        self.button_browse_datapath.grid(column=2, row=0, sticky="w")

        self.button_autofill = tk.Button(self.frame1, text="load", command=self._autofill)
        self.button_autofill.grid(row=2, column=1, sticky="w", pady=5)

    def _create_widget_frame2(self, param_dict):
        """
        Creates the widget of frame 2 :

        - A list of labeled entry boxes or combobox for each NXsas parameters
        - A combobox next to the entry box if the parameter is numerical

        """
        self.frame2.interior.columnconfigure(1, weight=1)

        row_nbr = -1
        # For each NeXus parameter present in the paramDict
        for key_param, value_param in param_dict.items():
            row_nbr = row_nbr + 1
            tk.Label(self.frame2.interior, text=key_param).grid(column=0, row=row_nbr, sticky="w",
                                                                pady=2)

            # If there are obligatory values
            if len(value_param[2]) != 0:
                options = value_param[2]
                combobox = ttk.Combobox(self.frame2.interior, values=options, state="readonly",
                                        name=f"valueCombo{row_nbr}")
                combobox.grid(column=1, row=row_nbr, sticky="we", pady=2)
                combobox.set(options[0])

            # Otherwise, we create an entry to input the parameter
            else:
                string_var = tk.StringVar()
                string_var.set(value_param[1])
                entry = tk.Entry(self.frame2.interior, textvariable=string_var,
                                 name=f"valueEntry{row_nbr}")
                entry.grid(column=1, row=row_nbr, sticky="we", pady=2)
                if value_param[3]["EX_required"] == "true":
                    entry.configure(background="lightpink")
                elif value_param[3]["EX_required"] == "false":
                    entry.configure(background="khaki")

            # If the parameter has a unit attribute we add a combobox next to the entry. The
            # options are the unit
            # that correspond to the unit type specified. By default the unit type is unitless
            if "units" in value_param[3].keys():
                unit = value_param[3]["units"]
                unit_type = "NX_UNITLESS"
                for key_unit, value_unit in dictUnit.items():
                    if unit in value_unit:
                        unit_type = key_unit

                options = list(dictUnit[unit_type].keys())
                combobox = ttk.Combobox(self.frame2.interior, values=options, state="readonly",
                                        name=f"comboUnit{row_nbr}")
                combobox.grid(column=2, row=row_nbr, sticky="we", pady=2)
                combobox.set(unit)

    def _create_widget_frame3(self):
        """
        Creates the widgets of frame 3:

        - A button to exit the program
        - A button to export the file to NeXus format

        """
        self.frame3.columnconfigure(1, weight=1)

        # The quit button
        self.button_quit = tk.Button(self.frame3, text="Close program",
                                     command=lambda: quit_program(self))
        self.button_quit.grid(row=1, column=1, padx=8, pady=8, sticky="w")

        # The export button
        self.button_export = tk.Button(self.frame3, text="Save File",
                                       command=self._check_completion)
        self.button_export.grid(row=1, column=1, padx=8, pady=8, sticky="e")

    def _load_h5(self):
        """
        Loads the HDF5 file

        Returns
        -------
        fileHDF5
            The file that's needed to be loaded
        """
        try:
            file_h5 = h5py.File(self.stringvar_datapath.get(), "r")
            return file_h5
        except Exception as error:
            self.destroy()
            tk.messagebox.showerror("Error", f"An error occurred while loading:\n {str(error)}")
            return None

    def _autofill(self):
        """
        Autofill the parameters if a settings file is provided
        """
        nexus_file_dict = {}

        def _load_datasets(group, path=""):
            for key, item in group.items():
                current_path = f"{path}/{key}"
                if isinstance(item, h5py.Dataset):
                    if np.shape(item) != () and current_path:
                        nexus_file_dict[current_path] = item[:]
                    else:
                        nexus_file_dict[current_path] = item[()]
                elif isinstance(item, h5py.Group):
                    _load_datasets(item, current_path)

        with self._load_h5() as file_h5:
            _load_datasets(file_h5)
        key_gui = ""
        for child_widget in self.frame2.interior.children.values():
            if isinstance(child_widget, tk.Label):
                key_gui = child_widget.cget("text")

            elif isinstance(child_widget, tk.Entry) and \
                    re.search("^valueEntry", child_widget.winfo_name()):
                try:
                    child_widget.delete(0, tk.END)
                    child_widget.insert(0, nexus_file_dict[key_gui])

                except KeyError:
                    child_widget.delete(0, tk.END)
                    child_widget.insert(0, "None")

            elif isinstance(child_widget, ttk.Combobox) and \
                    re.search("^comboUnit", child_widget.winfo_name()):
                try:
                    unit = dictParamNXsas[key_gui][3]["units"]
                    child_widget.set(unit)
                except KeyError:
                    child_widget.set("")

    def _check_completion(self):
        """
        Tries to fill a copy of ParamNXsas dictionary, if a required parameter is not filled it
        fails
        """
        key = ""
        # We make a deep copy of the NXsas format dictionary, this copy will be filled
        filled_dict = copy.deepcopy(dictParamNXsas)

        # For each widget in the second frame
        for child_widget in self.frame2.interior.children.values():
            # if the widget is a label we get its text, which is the key to the parameter in the
            # NeXus format
            if isinstance(child_widget, tk.Label):
                key = child_widget.cget("text")

            # Or if the widget is an entry or a combobox with a name that starts with valueEntry
            # or valueCombo
            elif (isinstance(child_widget, (tk.Entry, ttk.Combobox))) \
                    and re.search("(^value)", child_widget.winfo_name()):
                dict_attributes = dictParamNXsas[key][3]
                assertion_a = dict_attributes["EX_required"] == "true" and \
                              child_widget.get().lower() not in ["none", ""]
                assertion_b = dict_attributes["EX_required"] == "false"
                # If the attribute is required and is filled or is not required we convert the
                # string into an adequate
                # type and fill the dictionary
                if assertion_a or assertion_b:
                    value = child_widget.get().lower()
                    value = string_2_value(value)
                    filled_dict[key][1] = value
                # Otherwise we raise an error
                else:
                    filled_dict = dictParamNXsas
                    if self.do_advanced:
                        tk.messagebox.showerror("Error", "A required argument has not been filled")
                    else:
                        tk.messagebox.showerror("Error",
                                                "A required argument has not been filled, "
                                                "please open in "
                                                "advanced mode to manually fill it")
                    return

            # Or if the widget is a combobox with a name that starts with "comboUnit" we fill the
            # unit attribute
            elif (isinstance(child_widget, ttk.Combobox)) and re.search("(^comboUnit)",
                                                                        child_widget.winfo_name()):
                filled_dict[key][3]["units"] = str(child_widget.get().lower())

        # We then load the data and generate the file
        with self._load_h5() as file_h5:
            data_array = file_h5["/entry/instrument/detector/data"][:]

        try:
            os.remove(self.stringvar_datapath.get())
            split_path = os.path.split(self.stringvar_datapath.get())
            generate_nxsas_file(filled_dict, data_array, split_path[0])
            tk.messagebox.showinfo("Success", "File converted successfully !")
        except Exception as error:
            tk.messagebox.showinfo("Error", f"There was a problem converting the file:\n{error}")


if __name__ == "__main__":
    app = Application(True)
    app.mainloop()
