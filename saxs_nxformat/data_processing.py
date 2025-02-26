"""
This module is meant to help the user process their data
"""
import inspect
import re
import tkinter as tk
from tkinter import ttk, filedialog

from saxs_nxformat.class_nexus_file import NexusFile


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
                                width=200, height=200,
                                yscrollcommand=vscrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        vscrollbar.config(command=self.canvas.yview)

        # Reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = ttk.Frame(self.canvas)
        self.interior.columnconfigure(0, weight=1)
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
    if re.search("(^none$)|(^defaul?t$)|(^$)", string.lower()):
        return None
    if re.search("(^-?\\d*[.,]\\d*$)|(^-?\\d?[.,]?\\d*e[+-]\\d*$)", string.lower()):
        value = float(string)
    elif re.search("^-?\\d+$", string):
        value = int(string)
    elif re.search("^true$", string.lower()):
        value = True
    elif re.search("^false$", string.lower()):
        value = False
    elif re.search("^[a-z]+(_[a-z]+)*$", string.lower()):
        value = string.upper()
    else:
        print(f"{string} couldn't be converted, set to None")
        return None

    return value


class GUI_process(tk.Tk):
    """
    A GUI to manually process SAXS or WAXS data in the form of a
    .h5 file following the NXcanSAS standard

    Attributes
    ----------
    selected_files :
        Tuple or List of all the selected files

    selected_folder :
        Path of the selected folder

    stringvar_file_name :
        Holds the name of the settings file to be saved.

    frame1 :
        Frame containing all the buttons and texts

    label_selection :
        Label to inform the user on what they selected

    Label_status :
        Label to inform the user of the conversion status
    """

    def __init__(self):
        self.selected_files = None
        self.process = {}
        for name, method in inspect.getmembers(NexusFile, predicate=inspect.isfunction):
            if name.startswith("process_"):
                self.process[name.removeprefix("process_")] = method

        super().__init__()
        self.focus_force()
        self.geometry("1200x900")
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=2)
        self.title("Data processing")

        self.frame_inputs = tk.Frame(self, border=5, relief="ridge")
        self.frame_inputs.grid(row=0, column=0, sticky="nsew", pady=5, padx=5)
        self.frame_inputs.columnconfigure(0, weight=1)
        self._inputs_building()

        self.param_frame = tk.Frame(self, border=5, relief="ridge")
        self.param_frame.grid(row=1, rowspan=3, column=0, sticky="news", pady=5, padx=5)
        self.param_frame.columnconfigure(1, weight=1)

        self.frame_processes = tk.Frame(self, border=5, relief="ridge")
        self.frame_processes.grid(row=0, rowspan=2, column=1, columnspan=2, sticky="nsew", pady=5, padx=5)
        self._process_building()

        close_button = tk.Button(self,
                                 text="Close",
                                 font=("Arial", 12),
                                 command=lambda: self.destroy())
        close_button.grid(column=1, row=3, sticky="w", padx=5, pady=5)

        self.progress_label = tk.Label(self,
                                       text="No processing in progress",
                                       font=("Arial", 14, "bold"),
                                       fg="#6DB06E")
        self.progress_label.grid(column=2, row=3, sticky="w", padx=5, pady=5)

    def _inputs_building(self):
        frame_title = tk.Label(self.frame_inputs,
                               text="Inputs",
                               font=("Arial", 14, "bold"),
                               padx=10, pady=10)
        frame_title.grid(column=0, row=0, sticky="w", pady=(15, 20), padx=5)

        browse_button = tk.Button(self.frame_inputs,
                                  text="Select files",
                                  font=("Arial", 12),
                                  command=self.browse_files,
                                  padx=20,
                                  pady=5)
        browse_button.grid(column=0, row=1)

        self.file_list = tk.Listbox(self.frame_inputs, selectmode=tk.MULTIPLE)
        self.file_list.grid(column=0, row=2, sticky="news")

    def _process_building(self):
        self.frame_processes.columnconfigure(0, weight=1)
        self.frame_processes.columnconfigure(1, weight=1)
        self.frame_processes.columnconfigure(2, weight=1)
        self.frame_processes.columnconfigure(3, weight=1)

        self.frame_processes.rowconfigure(1, weight=1)
        self.frame_processes.rowconfigure(2, weight=1)
        self.frame_processes.rowconfigure(3, weight=1)
        self.frame_processes.rowconfigure(4, weight=1)
        frame_title = tk.Label(self.frame_processes,
                               text="Process options",
                               font=("Arial", 14, "bold"))
        frame_title.grid(column=0, row=0, sticky="w", pady=(5, 20), padx=5)

        current_row = 1
        current_column = 0

        for process_name in self.process.keys():
            button_process = tk.Button(self.frame_processes,
                                       text=process_name,
                                       command=lambda name=process_name: self._create_params(name),
                                       width=20)
            button_process.grid(column=current_column, row=current_row,
                                padx=15, pady=15, sticky="news")

            if current_column >= 3:
                current_column = 0
                current_row += 1
            else:
                current_column += 1

    def _create_params(self, process_name):
        print(process_name)
        for widget in self.param_frame.winfo_children():
            widget.destroy()

        frame_title = tk.Label(self.param_frame,
                               text="Process parameters",
                               font=("Arial", 14, "bold"),
                               )
        frame_title.grid(column=0, row=0, sticky="we", pady=(5, 20), padx=5)

        label_process = tk.Label(self.param_frame,
                                 text=f"Process : {process_name}",
                                 font=("Arial", 12))
        label_process.grid(column=0, row=1, sticky="w", pady=(5, 20), padx=5)

        # We get the method and inspect it to get its parameters and default values
        method = self.process[process_name]
        signature = inspect.signature(method)
        param_list = list(signature.parameters.items())

        current_row = 2
        for param in param_list:
            if param[0] != "self":
                param_str = str(param[1])
                name, value = param_str.split("=")
                label_param = tk.Label(self.param_frame,
                                       text=name,
                                       font=("Arial", 12))
                label_param.grid(column=0, row=current_row, pady=5, padx=5, sticky="w")

                entry_param = tk.Entry(self.param_frame,
                                       font=("Arial", 12))
                entry_param.insert(0, str(value.strip("'")))
                entry_param.grid(column=1, row=current_row, pady=5, padx=5, sticky="we")
                entry_param.tag = f"{param[0]}"
                current_row += 1

        confirm_button = tk.Button(self.param_frame,
                                   text="Confirm",
                                   font=("Arial", 12),
                                   command=lambda process=method: self._start_processing(process))
        confirm_button.grid(column=0, columnspan=2, row=current_row,
                            pady=15, padx=15)

    def browse_files(self):
        """
        Method used to browse and select files
        """
        filenames = filedialog.askopenfilenames(
            initialdir="./",
            title="Select Files",
            filetypes=(
                ("HDF5 Files", "*.h5*"),
                ("All Files", "*.*")
            )
        )
        self.selected_files = filenames

        self.file_list.delete(0, tk.END)

        for file in self.selected_files:
            name = file.split("/")[-1]
            self.file_list.insert(tk.END, name)

    def _start_processing(self, process):
        self.progress_label.configure(text="Processing in progress, please wait...",
                                      fg="#C16200")
        self.progress_label.update_idletasks()

        # We get the selected file
        self.to_process = []
        selected_index = self.file_list.curselection()
        print(selected_index)

        for index in selected_index:
            self.to_process += [self.selected_files[index]]

        print(self.to_process)

        # We get the parameters and convert them
        param_dict = {}
        for widget in self.param_frame.winfo_children():
            if hasattr(widget, 'tag'):
                tag = widget.tag
                entry_value = str(widget.get())
                value = string_2_value(entry_value)
                param_dict[tag] = value
        print(param_dict)

        # We fill out the parameters for every file
        print(process)
        for file_path in self.to_process:
            file = NexusFile(file_path)
            process(file, **param_dict)
            file.close()
        self.progress_label.configure(text="No processing in progress",
                                      fg="#6DB06E")


if __name__ == "__main__":
    app = GUI_process()
    app.mainloop()
