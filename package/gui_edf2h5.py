"""
This python file generates a GUI that allows the user to export an EDF file
to an HDF5 file with the NXsas standard.
To do so the user needs to follow these steps :
    - Launch the program and chose the advanced or simple mode of the program
    - In simple mode :
        - The user needs to provide an edf file that needs to be exported
        - The user then needs to provide a settings file that is tailored to
        the machine that produced the EDF file
        - The user can then click the export button, the file will be
        generated in the directory that contains
        this program
    - In advanced mode :
        - The user needs to provide an edf file that needs to be exported
        - the user can either autofill the required field or manually do so :
            - To autofill, The user then needs to provide a settings file
            that is tailored to the
            machine that produced the EDF file
        - The user can create said settings file by clicking the
        corresponding button :
            - First, the user needs to check the relevant metadata that is
            present in the header of the EDF file
            - Then, the user can match the relevant metadata to the
            corresponding NXsas parameters. The NXsas parameters
            are described on the following webpage :
            https://manual.nexusformat.org/classes/applications/NXsas.html
            - Finally the user needs to specify the unit of the metadata if
            it is relevant. After that they can click the
            save settings button which will generate a settings file. DO NOT
            CHANGE THE FIRST TWO WORDS, only the last one.
        - After filling the required fields, the user can click the export
        button which will generate the file,
        the file will be generated in the directory that contains this program
"""
import os
import tkinter as tk
import ast
import re
import copy
from tkinter import ttk, filedialog
from datetime import datetime
import fabio

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
    if re.search("(^-?\\d*[.,]\\d*$)|(^-?\\d?[.,]\\d*e[+-]\\d*$)", string):
        value = float(string)
    elif re.search("^-?\\d+$", string):
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
    This function fills an Entry widget with the absolute path of a selected
    file
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
                                              ("TxT Files", "*.txt"),
                                              ("EDF Files", "*.edf*"),
                                              ("all files", "*.*")))

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
        self.interior_id = self.canvas.create_window(0, 0, window=self.interior,
                                                     anchor=tk.NW)

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
            self.canvas.itemconfigure(self.interior_id,
                                      width=self.canvas.winfo_width())


class Application(tk.Tk):
    """
    This class creates the advanced application.

    Attributes
    ----------
    do_advanced : bool
        Is the app launched in advanced mode ?

    autofill_settings : dict
        Dictionary used to store autofill settings

    frame1 : tk.Frame
        the frame containing the browsing option and autofill options

    label_data : tk.Label
        the label used to identify the entry box that accepts the data file's
        path

    entry_datapath : tk.Label
        The entry box that accepts the data file's path

    button_browse_data : tk.Button
        The button that allows browsing of the data file

    label_settingspath : tk.Label
        The label used to identify the entry box that accepts the settings
        file's path

    entry_settingspath : tk.Label
        The entry box that accepts the settings file's path

    button_browse_settings : tk.Button
        The button that allows browsing of the settings file

    button_autofill : tk.Button
        The button that autofill frame2

    button_create_autofill : tk.Button
        The button that opens the configure settings window

    frame2 : VerticalScrolledFrame
        Scrollable frame containing all the parameters from NeXus with
        fillable entryboxes and combobox for the units

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

        self.autofill_settings = {}

        # Initialisation of the root window
        self.title(".edf to .h5 converter")
        self.geometry("700x500")

        # Initialisation of the frame that has the browsing and configuration
        # buttons
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
        self.stringvar_entry_save = tk.StringVar()
        self.frame3.pack(padx=8, pady=8, fill="x")
        self._create_widget_frame3()

    def _create_widgets_frame1(self):
        """
        Creates the widget of frame 1 :

        - A labeled entry bow that can be filles via browsing for both the
        data and settings file
        - A button that autofill the parameters if a settings file is provided
        - A button that opens a new window to create a settings file
        """

        # The Data row which contains a label, entry and browse button
        self.label_data = tk.Label(self.frame1,
                                   text="Absolute path of the file")
        self.label_data.grid(column=0, row=0, sticky="w")

        self.stringvar_datapath = tk.StringVar()
        self.stringvar_datapath.set("")
        self.entry_datapath = ttk.Entry(self.frame1,
                                        textvariable=self.stringvar_datapath)
        self.entry_datapath.grid(column=1, row=0, sticky="we")

        self.button_browse_data = tk.Button(self.frame1, text="browse",
                                            command=lambda: _browse_file(
                                                self.entry_datapath,
                                                self.stringvar_datapath))
        self.button_browse_data.grid(column=2, row=0, sticky="w")

        # The Settings row which contains a label, entry and browse button
        self.label_settingspath = tk.Label(self.frame1,
                                           text="Absolute path of the settings "
                                                "file")
        self.label_settingspath.grid(column=0, row=1, sticky="w")

        self.stringvar_settings_path = tk.StringVar()
        self.stringvar_settings_path.set("")
        self.entry_settingspath = ttk.Entry(self.frame1,
                                            textvariable=self.stringvar_settings_path)
        self.entry_settingspath.grid(column=1, row=1, sticky="we")

        self.button_browse_settings = tk.Button(self.frame1, text="browse",
                                                command=lambda: _browse_file(
                                                    self.entry_settingspath,
                                                    self.stringvar_settings_path))
        self.button_browse_settings.grid(column=2, row=1, sticky="w")

        # The config row which contains the autofill button and the create
        # settings button
        if self.do_advanced:
            self.button_autofill = tk.Button(self.frame1, text="Autofill",
                                             command=self._autofill)
            self.button_autofill.grid(row=2, column=1, sticky="w", pady=5)

            self.button_create_autofill = tk.Button(self.frame1,
                                                    text="Create autofill "
                                                         "settings",
                                                    command=lambda: Setting(
                                                        self,
                                                        self.stringvar_datapath.get()))
            self.button_create_autofill.grid(row=2, column=1, sticky="e",
                                             pady=5)

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
            tk.Label(self.frame2.interior, text=key_param).grid(column=0,
                                                                row=row_nbr,
                                                                sticky="w",
                                                                pady=2)

            # If there are obligatory values
            if len(value_param[2]) != 0:
                options = value_param[2]
                combobox = ttk.Combobox(self.frame2.interior, values=options,
                                        state="readonly",
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

            # If the parameter has a unit attribute we add a combobox next to
            # the entry. The options are the unit
            # that correspond to the unit type specified. By default the unit
            # type is unitless
            if "units" in value_param[3].keys():
                unit = value_param[3]["units"]
                unit_type = "NX_UNITLESS"
                for key_unit, value_unit in dictUnit.items():
                    if unit in value_unit:
                        unit_type = key_unit

                options = list(dictUnit[unit_type].keys())
                combobox = ttk.Combobox(self.frame2.interior, values=options,
                                        state="readonly",
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
        self.button_export = tk.Button(self.frame3,
                                       text="Export file to NeXus format",
                                       command=self._check_completion)
        self.button_export.grid(row=1, column=1, padx=8, pady=8, sticky="e")

    def _load_edf(self):
        """
        Loads the EDF file

        Returns
        -------
        file_edf
            The file that needed to be loaded
        """
        try:
            file_edf = fabio.open(self.stringvar_datapath.get())
            return file_edf
        except Exception as error:
            self.destroy()
            tk.messagebox.showerror("Error",
                                    f"An error occurred while loading the "
                                    f"file:\n {str(error)}")
            return None

    def _load_autofill(self):
        """
        Loads the settings file and store the settings in a variable
        """
        try:
            with open(self.stringvar_settings_path.get(), "r", encoding="utf-8") as settings_file:
                self.autofill_settings = ast.literal_eval(
                    f"{settings_file.readline()}")
        except Exception as error:
            self.autofill_settings = {}
            tk.messagebox.showerror("Error",
                                    f"An error occurred while loading the "
                                    f"settings file:\n {str(error)}")

    def _autofill(self):
        """
        Autofill the parameters if a settings file is provided
        """
        # We load the settings file for the autofill
        self._load_autofill()

        file_edf = self._load_edf()

        if file_edf is not None:
            edf_header = file_edf.header
            edf_header = dict(edf_header)
        else:
            return None

        string = ""
        key_nexus = ""
        # For each widget in the second freame
        for child_widget in self.frame2.interior.children.values():
            # if the widget is a label we get its text, which is the key to
            # the parameter in the NeXus format
            if isinstance(child_widget, tk.Label):
                key_nexus = child_widget.cget("text")

            # Or if the widget is an Entry that has a name that starts with
            # valueEntry, we try to :
            #   - translate the nexusKey into an EDFkey and try to insert the
            #   corresponding value from
            #   the EDF header into the entryWidget.
            #   - If we fail, we instead fill the entry with None
            elif isinstance(child_widget, tk.Entry) and re.search("^valueEntry",
                                                                  child_widget.winfo_name()):
                try:
                    key_edf = self.autofill_settings[key_nexus][0]
                    child_widget.delete(0, tk.END)
                    child_widget.insert(0, edf_header[key_edf])
                except KeyError:
                    text = child_widget.get()
                    if text.lower().strip() == "":
                        child_widget.delete(0, tk.END)
                        child_widget.insert(0, "None")
                    if len(dictParamNXsas[key_nexus][2]) == 0:
                        string = string + f"{key_nexus}\n"

            # Or if the widget is a ComboBox that has a name that starts with
            # comboUnit, we try to :
            #   - translate the nexusKey into a unit and try to insert the
            #   unit into the combobox.
            #   - If we fail, we instead fill the entry with ""
            elif isinstance(child_widget, ttk.Combobox) and re.search(
                    "^comboUnit", child_widget.winfo_name()):
                try:
                    unit = self.autofill_settings[key_nexus][1]
                    child_widget.set(unit)
                except Exception as error:
                    print(f"Autofill error :\n {error}")

        # We inform the user of which value have been autofilled
        if string == "" and self.do_advanced:
            tk.messagebox.showinfo("Success",
                                   "All values have been sucessfully "
                                   "autofilled")
        elif string != "" and self.do_advanced:
            tk.messagebox.showwarning("Warning",
                                      f"The following values have not been "
                                      f"filled :\n{string}")
        return None

    def _check_completion(self):
        """
        Tries to fill a copy of ParamNXsas dictionary, if a required
        parameter is not filled it fails
        """
        if not self.do_advanced:
            self._autofill()

        key = ""
        # We make a deep copy of the NXsas format dictionary, this copy will
        # be filled
        filled_dict = copy.deepcopy(dictParamNXsas)

        # For each widget in the second frame
        for child_widget in self.frame2.interior.children.values():
            # if the widget is a label we get its text, which is the key to
            # the parameter in the NeXus format
            if isinstance(child_widget, tk.Label):
                key = child_widget.cget("text")

            # Or if the widget is an entry or a combobox with a name that
            # starts with valueEntry or valueCombo
            elif isinstance(child_widget, (tk.Entry, ttk.Combobox)) \
                    and re.search("(^value)", child_widget.winfo_name()):
                dict_attributes = dictParamNXsas[key][3]
                assertion_a = dict_attributes["EX_required"] == "true" \
                              and child_widget.get().lower() not in ["none", ""]
                assertion_b = dict_attributes["EX_required"] == "false"
                # If the attribute is required and is filled or is not
                # required we convert the string into an adequate
                # type and fill the dictionary
                if assertion_a or assertion_b:
                    value = child_widget.get().lower()
                    value = string_2_value(value)
                    filled_dict[key][1] = value
                # Otherwise we raise an error
                else:
                    filled_dict = dictParamNXsas
                    if self.do_advanced:
                        tk.messagebox.showerror("Error",
                                                "A required argument has not "
                                                "been filled")
                    else:
                        if not self.do_advanced:
                            self.frame2.pack(padx=8, pady=8, fill="x")
                        tk.messagebox.showerror("Error",
                                                "A required argument has not "
                                                "been filled, "
                                                "please fill it manually")
                    return

            # Or if the widget is a combobox with a name that starts with
            # "comboUnit" we fill the unit attribute
            elif (isinstance(child_widget, ttk.Combobox)) and re.search(
                    "(^comboUnit)", child_widget.winfo_name()):
                filled_dict[key][3]["units"] = str(child_widget.get().lower())

        # We then load the data and generate the file
        file_edf = self._load_edf()

        if file_edf is not None:
            data_array = file_edf.data
        else:
            return

        try:
            split_path = os.path.split(self.stringvar_datapath.get())
            generate_nxsas_file(filled_dict, data_array, split_path[0])
            tk.messagebox.showinfo("Success", "File converted successfully !")
        except Exception as error:
            tk.messagebox.showinfo("Error",
                                   f"There was a problem converting the file:\n{error}")


class Setting(tk.Toplevel):
    """
    Creates the window to create a new settings file

    Attributes
    ----------
    dict_match : dict
        Stores the match between the NXsas parameters key and the edf header key

    checked_labels : list
        Stores the checked labels

    frame1
        the frame containing the path of the edf file that we want to create
        a settings file for

    label_datapath
        the label used to identify the entry box that accepts the data file's
        path

    entry_datapath
        the entry box that accepts the data file's path, it is disabled since
        we get it from the previous window

    frame2
        This frame has 2 states :

        - The frame contains all the header data and has a checkbox next to
        it to identify the one that are relevant
        - The frame contains all the NXsas parameters and a combobox
        containing all the relevant header data

    frame3
        This frame also has 2 states :

        - The frame contains a button that is used to proceed to the next step
        - The frame contains an entry box to name your settings file and a
        button that saves it

    entry_file_name
        the fillable entry that contains the desired name of the settings file

    button_save
        the button that saves the settings file

    """

    def __init__(self, master, path):
        super().__init__(master)

        self.focus_force()

        self.dict_match = {}
        self.checked_labels = []

        self.title("Autofill setting")
        self.geometry("700x500")

        self.frame1 = tk.Frame(self)
        self.stringvar_datapath = tk.StringVar()
        self.stringvar_datapath.set(path)
        self.frame1.pack(padx=8, pady=8, fill="x")
        self.frame1.columnconfigure(1, weight=1)

        self.label_param = tk.Label(self,
                                    text="Chose which parameters are "
                                         "relevant.")
        self.label_param.pack()

        self.frame2 = VerticalScrolledFrame(self)
        self.frame2.pack(padx=8, pady=8, fill="x")

        self.frame3 = tk.Frame(self)
        self.stringvar_file_name = tk.StringVar()
        self.frame3.pack(padx=8, pady=8, fill="x")

        self._create_widgets_frame1()
        self._create_widget_frame2_1()

    def _create_widgets_frame1(self):
        self.label_datapath = tk.Label(self.frame1,
                                       text="Absolute path of the file")
        self.label_datapath.grid(column=0, row=0, sticky="w")

        self.entry_datapath = ttk.Entry(self.frame1,
                                        textvariable=self.stringvar_datapath,
                                        state=tk.DISABLED)
        self.entry_datapath.grid(column=1, row=0, sticky="we")

    def _create_widget_frame2_1(self):
        file_edf = self._load_edf()

        if file_edf is not None:
            edf_header = file_edf.header
            edf_header = dict(edf_header)
        else:
            return

        row_nbr = -1
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

    def _create_widget_frame2_2(self):
        self.focus_force()
        self.frame2.destroy()
        self.frame2 = VerticalScrolledFrame(self)
        self.frame2.pack(padx=8, pady=8, fill="x")
        self.label_param.configure(
            text="Match the header parameter to the corresponding NeXus "
                 "parameter if possible.")

        self.frame2.interior.columnconfigure(1, weight=1)
        row_nbr = -1
        for label in self.checked_labels:
            row_nbr = row_nbr + 1
            tk.Label(self.frame2.interior, text=label).grid(column=0,
                                                            row=row_nbr,
                                                            sticky="w")

            options_param = [""]
            options_unit = []
            for key, value in dictParamNXsas.items():
                for value_unit in dictUnit.values():
                    for unit in list(value_unit.keys()):
                        options_unit = options_unit + [unit]

                if len(value[2]) == 0:
                    options_param.append(key)
            combobox = ttk.Combobox(self.frame2.interior, values=options_param,
                                    state="readonly",
                                    name=f"comboParam{row_nbr}")
            combobox.grid(column=1, row=row_nbr, sticky="we")

            combobox = ttk.Combobox(self.frame2.interior, values=options_unit,
                                    state="readonly",
                                    name=f"comboUnit{row_nbr}")
            combobox.grid(column=2, row=row_nbr, sticky="we", pady=2)
            combobox.set("")

        self._create_widget_frame3_2()

    def _create_widget_frame3_1(self):
        self.button_continue = tk.Button(self.frame3, text="Next step",
                                         command=self._save_labels)
        self.button_continue.pack(padx=8, pady=8)

    def _create_widget_frame3_2(self):
        self.frame3.destroy()
        self.frame3 = tk.Frame(self)
        self.frame3.pack(padx=8, pady=8, fill="x")

        self.stringvar_file_name.set("instrumentName")
        self.entry_file_name = tk.Entry(self.frame3,
                                        textvariable=self.stringvar_file_name,
                                        width=50, justify="center")
        self.entry_file_name.pack()

        self.button_save = tk.Button(self.frame3, text="Save settings",
                                     command=self._save_settings)
        self.button_save.pack(padx=8, pady=8)

    def _load_edf(self):
        """
        Loads the EDF file

        Returns
        -------
        file_edf
            The file that needed to be loaded
        """
        try:
            file_edf = fabio.open(self.stringvar_datapath.get())
            return file_edf
        except Exception as error:
            self.destroy()
            tk.messagebox.showerror("Error",
                                    f"An error occurred while loading the "
                                    f"file:\n {str(error)}")
            return None

    def _save_labels(self):
        header_label = ""
        string = ""
        for child_widget in self.frame2.interior.children.values():
            if isinstance(child_widget, tk.Label):
                header_label = child_widget.cget("text")
            if isinstance(child_widget, ttk.Checkbutton):
                if "selected" in child_widget.state():
                    self.checked_labels.append(header_label)
                    string = string + f"{header_label}, "

        confirm = tk.messagebox.askokcancel(
            "Warning",
            "Do you confirm you want to keep the following parameters :\n" +
            string[
            0:-2:1])
        if confirm:
            self._create_widget_frame2_2()
            self._create_widget_frame3_2()
        else:
            self.checked_labels = []

    def _save_settings(self):
        value = ""
        key = ""
        for child_widget in self.frame2.interior.children.values():
            if isinstance(child_widget, tk.Label):
                value = child_widget.cget("text")

            elif isinstance(child_widget, ttk.Combobox) and re.search(
                    "^comboParam", child_widget.winfo_name()):
                key = child_widget.get()
                if key.lower().strip() != "" and key.lower().strip() in self.dict_match:
                    self.dict_match = {}
                    tk.messagebox.showerror("Error",
                                            f"An error occurred while "
                                            f"saving:\n {key} is used two "
                                            f"times")
                    return
                elif key.lower().strip() == "":
                    continue
                else:
                    self.dict_match[key] = [value]

            elif isinstance(child_widget, ttk.Combobox) and re.search(
                    "^comboUnit", child_widget.winfo_name()):
                unit = child_widget.get()
                self.dict_match[key].append(unit)

        try:
            current_time = datetime.now()
            time_stamp = str(current_time.strftime("%Y-%m-%dT%H-%M"))
            if "_" in self.stringvar_file_name.get():
                tk.messagebox.showerror("Error",
                                        "Do not use underscores '_' in your "
                                        "instrument name")
                return
            name = "settings_EDF2NXsas_" + self.stringvar_file_name.get() + \
                   "_" + time_stamp + ".txt"
            with open(name, "w", encoding="utf-8") as file:
                file.write(str(self.dict_match))
            self.destroy()
            tk.messagebox.showinfo("Sucess", "Settings successfully saved !")
            self.dict_match = {}
        except Exception as error:
            self.dict_match = {}
            tk.messagebox.showerror("Error",
                                    f"An error occurred while saving:\n "
                                    f"{str(error)}")


if __name__ == "__main__":
    answer = tk.messagebox.askyesnocancel("Booting method",
                                          "Would you like to open in advanced "
                                          "mode ?")
    if answer is not None:
        app = Application(answer)
        app.mainloop()
