"""
module description
"""

import json
import os
import re
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog

import fabio
from saxs_nxformat import CONF_PATH


#############################
### Some utility function ###
#############################


def string_2_value(string: str) -> str | int | float | None:
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

    if re.search("(^-?\\d*[.,]\\d*$)|(^-?\\d?[.,]\\d*e[+-]\\d*$)", string):
        value = float(string)
    elif re.search("^-?\\d+$", string):
        value = int(string)
    elif string.lower().strip() in ["none", ""]:
        value = None
    else:
        value = str(string).lower()

    return value


##############################
### Scrollable frame class ###
##############################


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


######################
### App definition ###
######################


class Setting(tk.Tk):
    """
    A GUI application for creating the configuration files.

    This class provides a graphical interface for users to create and save configuration files
    for converting EDF files into a NeXus format.

    Attributes
    ----------
    dict_config : dict
        A dictionary containing the NeXus structure loaded from a JSON file.

    stringvar_datapath : tk.StringVar
        Holds the path to the reference file.

    stringvar_file_name : tk.StringVar
        Holds the name of the settings file to be saved.

    frame1 : tk.Frame
        The frame containing the data input widgets.

    frame2 : VerticalScrolledFrame
        A scrollable frame displaying the parameters and configurations.

    frame3 : tk.Frame
        The frame containing action buttons for navigation and saving.
    """

    def __init__(self):
        super().__init__()
        self.focus_force()

        # We get the path of this script to load the necessary dict
        BASE_DIR = Path(__file__).parent
        json_path = BASE_DIR / "nexus_standards" / "structure_NXcanSAS.json"
        with open(json_path, "r", encoding="utf-8") as file:
            self.dict_config = json.load(file)

        self.title("Config creator")
        self.geometry("700x700")

        label_title = tk.Label(self, text="Config builder",
                               fg="black", font=("Arial", 16, "bold"), justify="left")
        label_title.pack()

        self.frame1 = tk.Frame(self)
        self.stringvar_datapath = tk.StringVar()
        self.frame1.pack(padx=8, pady=8, fill="x")
        self.frame1.columnconfigure(1, weight=1)

        self.frame2 = VerticalScrolledFrame(self)
        self.frame2.pack(padx=8, pady=8, fill="x")

        self.frame3 = tk.Frame(self)
        self.stringvar_file_name = tk.StringVar()
        self.frame3.pack(padx=8, pady=8, fill="x")
        self._create_widget_frame3_1()

        self._create_widgets_frame1()

    def _create_widgets_frame1(self):
        """
        This method adds a label, an entry field, and a browse button to the first frame.
        The entry field displays the absolute path of the reference file selected 
        using the browse button.
        """
        # The Data row which contains a label, entry and browse button
        label_data = tk.Label(self.frame1,
                              text="Absolute path of the reference file")
        label_data.grid(column=0, row=0, sticky="w")

        stringvar_datapath = tk.StringVar()
        stringvar_datapath.set("")
        entry_datapath = ttk.Entry(self.frame1, textvariable=stringvar_datapath)
        entry_datapath.grid(column=1, row=0, sticky="we")

        button_browse_data = tk.Button(self.frame1, text="browse",
                                       command=lambda: self._create_widget_frame2_1(
                                           entry_datapath,
                                           stringvar_datapath))
        button_browse_data.grid(column=2, row=0, sticky="w")

    def _create_widget_frame2_1(self, widget, string_var):
        """
        This method creates a scrollable frame containing all the key, value pairs
        present in the .edf file header. It also creates a checkbox to indicate if
        the user wants to use this key to autofill the hdf5 file
        """
        self.frame2.destroy()
        self.frame2 = VerticalScrolledFrame(self)
        self.frame2.pack(padx=8, pady=8, fill="x")

        file_edf = self._browse_load_edf(widget, string_var)

        if file_edf is not None:
            edf_header = file_edf.header
            edf_header = dict(edf_header)
        else:
            return

        label_param = tk.Label(self.frame2.interior,
                               text="Chose which parameters are "
                                    "relevant.")
        label_param.grid(column=0, columnspan=3)

        row_nbr = 0
        for key, value in edf_header.items():
            row_nbr = row_nbr + 1
            tk.Label(self.frame2.interior, text=key).grid(column=0, row=row_nbr,
                                                          sticky="w", pady=4)

            string_var = tk.StringVar()
            string_var.set(value)
            entry = tk.Entry(self.frame2.interior, textvariable=string_var,
                             state=tk.DISABLED)
            entry.grid(column=1, row=row_nbr, sticky="we", pady=4)

            check_button = ttk.Checkbutton(self.frame2.interior)
            check_button.grid(column=2, row=row_nbr, sticky="w", pady=4)
            check_button.state(['!alternate'])

        self._create_widget_frame3_1()

    def _create_widget_frame2_2(self, checked_label):
        """
        This method updates the scrollable frame to display all the
        NeXus parameters that are used for the format. Each NeXus
        parameter is associated to a combo box that contains all the
        keys kept in the previous frame. Alternatively, the combobox
        can be filled out by the user, wgich will set this value as
        a default value. If left empty a default value will be set.

        Parameters
        ----------
        checked_label : list
            The list of keys from the .edf file that are used as
            options in the comboboxes.
        """
        self.frame2.destroy()
        self.frame2 = VerticalScrolledFrame(self)
        self.frame2.pack(padx=8, pady=8, fill="x")

        def create_fillables(element, line=None, level=0):
            if line is None:
                line = [1]

            indent = 6 * level

            for key, value in element.items():
                element_type = value.get("element type")
                docstring = value.get("docstring")
                content = value.get("content")
                possible_value = value.get("possible value", [0])

                # If the element is a group we only display a label
                if element_type.lower() == "group":
                    label_text = f"Group : {key}"
                    label_group = tk.Label(
                        self.frame2.interior,
                        text=label_text,
                        fg="#BF4E30",
                        font=("Arial", 10, "bold"),
                        justify="left"
                    )
                    label_group.grid(padx=2,
                                     pady=(indent, 4),
                                     column=0,
                                     columnspan=3,
                                     row=line[0],
                                     sticky="w")

                # If the element is a dataset we display a label in the first column
                else:
                    if len(possible_value) == 1 and content is None:
                        level = level + 1
                        continue

                    label_text = f"{element_type} : {key}"
                    if element_type.lower() == "dataset":
                        label_dataset = tk.Label(
                            self.frame2.interior,
                            text=label_text,
                            fg="#008F85",
                            font=("Arial", 10, "bold"),
                            justify="left"
                        )
                    else:
                        label_dataset = tk.Label(
                            self.frame2.interior,
                            text=label_text,
                            fg="#147B4E",
                            font=("Arial", 10, "bold"),
                            justify="left"
                        )

                    label_dataset.grid(padx=(indent, 4), pady=8, column=0, row=line[0], sticky="w")

                    if key.lower() == "@units":
                        combobox = ttk.Combobox(self.frame2.interior,
                                                values=possible_value[0],
                                                state="readonly")
                        combobox.set(possible_value[0][0])
                    elif len(possible_value) > 1:
                        combobox = ttk.Combobox(self.frame2.interior, values=possible_value)
                        combobox.set(possible_value[0])
                    elif len(possible_value) == 1:
                        combobox = ttk.Combobox(self.frame2.interior,
                                                values=possible_value,
                                                state="disabled")
                        combobox.set(possible_value[0])
                    else:
                        combobox = ttk.Combobox(self.frame2.interior, values=checked_label)

                    combobox.grid(padx=2, pady=2, column=1, row=line[0], sticky="we")

                    # for the time being, we stock the reference to the widget
                    value["associated_widget"] = combobox

                if docstring:
                    label_docstring = tk.Label(self.frame2.interior,
                                               text=f"{docstring}",
                                               fg="gray",
                                               font=("Arial", 8, "italic"),
                                               justify="left")
                    label_docstring.grid(padx=(indent, 4),
                                         column=0,
                                         columnspan=3,
                                         row=line[0] + 1,
                                         sticky="w")
                    line[0] += 1

                line[0] += 1

                # If the dataset has content, we call the recursive function
                if content:
                    create_fillables(content, line, level + 1)

        create_fillables(self.dict_config)

        self.create_widget_frame3_2()

    def _create_widget_frame3_1(self):
        """
        This method creates the next step and close button
        for the frame 2-1.
        """
        self.frame3.destroy()
        self.frame3 = tk.Frame(self)
        self.frame3.pack(padx=8, pady=8, fill="x")

        button_continue = tk.Button(self.frame3, text="Next step",
                                    command=self._save_labels)
        button_continue.pack(padx=8, pady=8, side="right")

        button_close = tk.Button(self.frame3, text="Close",
                                 command=lambda: self.destroy())
        button_close.pack(padx=8, pady=8, side="left")

    def create_widget_frame3_2(self):
        """
        This method creates the save and close button as well as
        the entry to enter a name for the settings file for the frame 2-2
        """
        self.frame3.destroy()
        self.frame3 = tk.Frame(self)
        self.frame3.pack(padx=8, pady=8, fill="x")

        self.stringvar_file_name = tk.StringVar()
        self.stringvar_file_name.set("instrumentName")
        entry_file_name = tk.Entry(self.frame3,
                                   textvariable=self.stringvar_file_name,
                                   width=50, justify="center")
        entry_file_name.pack()

        button_save = tk.Button(self.frame3, text="Save settings",
                                command=self._save_settings)
        button_save.pack(padx=8, pady=8, side="right")

        button_close = tk.Button(self.frame3, text="Close",
                                 command=lambda: self.destroy())
        button_close.pack(padx=8, pady=8, side="left")

    def _browse_load_edf(self, widget, string_var):
        """
        This method is used to search and load an edf file into
        the application

        Parameters
        ----------
        widget :
            Widget that will contain the absolute path of the searched file
        string_var :
            Holds the absolute path of the file

        Returns
        -------
        file_edf :
            The loaded edf file, None if there is an error
        """
        filename = filedialog.askopenfilename(initialdir="./",
                                              title="Select a File",
                                              filetypes=(
                                                  ("EDF Files", "*.edf*"),
                                                  ("all files", "*.*")))

        string_var.set(filename)
        widget.configure(textvariable=string_var)
        try:
            file_edf = fabio.open(filename)
            return file_edf
        except Exception as error:
            self.destroy()
            tk.messagebox.showerror("Error",
                                    f"An error occurred while loading the "
                                    f"file:\n {str(error)}")
            return None

    def _save_labels(self):
        """
        Method that saves the checked .edf keys from frame 2-1 and asks
        the user for confirmation.
        """
        header_label = ""
        string = ""
        checked_labels = []

        for child_widget in self.frame2.interior.children.values():
            if isinstance(child_widget, tk.Label):
                header_label = child_widget.cget("text")
            if isinstance(child_widget, ttk.Checkbutton):
                if "selected" in child_widget.state():
                    checked_labels.append(header_label)
                    string = string + f"{header_label}, "

        confirm = tk.messagebox.askokcancel(
            "Warning",
            "Do you confirm you want to keep the following parameters :\n" +
            string[0:-2:1])
        if confirm:
            self._create_widget_frame2_2(checked_labels)
            self.create_widget_frame3_2()

    def _save_settings(self):
        """
        Method that saves the settings in a json file that has the same structure
        as the input json file.
        """

        def fill_config(element):
            for key, value in element.items():
                element_type = value.get("element type")
                content = value.get("content")
                possible_value = value.get("possible value", [0])

                # If the element is a dataset we display a label in the first column
                if element_type.lower() in ["dataset", "attribute"]:
                    if len(possible_value) == 1:
                        value["value"] = possible_value[0]
                        if value.get("associated_widget"):
                            del value["associated_widget"]

                    else:
                        if key == "@units":
                            value["value"] = [value["associated_widget"].get(),
                                              value["possible value"][1]]
                        else:
                            value["value"] = value["associated_widget"].get()
                        del value["associated_widget"]

                # If the dataset has content, we call the recursive function
                if content:
                    fill_config(content)

        fill_config(self.dict_config)

        try:
            current_time = datetime.now()
            time_stamp = str(current_time.strftime("%Y-%m-%dT%H-%M"))
            if "_" in self.stringvar_file_name.get():
                tk.messagebox.showerror("Error",
                                        "Do not use underscores (_) in your "
                                        "instrument name")
                return

            name = f"settings_EDF2NX_{self.stringvar_file_name.get()}_{time_stamp}.json"
            file_path = CONF_PATH / name

            with open(file_path, "w", encoding="utf-8") as fichier:
                json.dump(self.dict_config, fichier, indent=4)

            self.destroy()
            tk.messagebox.showinfo("Sucess", "Settings successfully saved !")
            self.dict_config = {}
        except Exception as error:
            self.dict_config = {}
            tk.messagebox.showerror("Error",
                                    f"An error occurred while saving:\n "
                                    f"{str(error)}")


if __name__ == "__main__":
    app = Setting()
    app.mainloop()
