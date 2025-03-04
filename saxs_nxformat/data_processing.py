"""
This module is meant to help the user process their data
"""
import inspect
import re
import h5py
import tkinter as tk
from tkinter import ttk, filedialog

from saxs_nxformat import TREATED_PATH, ICON_PATH
from saxs_nxformat.class_nexus_file import NexusFile
from saxs_nxformat.utils import string_2_value


def get_group_names(file_list):
    groups = []
    for file_path in file_list:
        with h5py.File(file_path, "r") as file_object:
            parent_group = file_object["/ENTRY"]

            for name in parent_group.keys():
                if isinstance(parent_group[name], h5py.Group) and "DATA" in name and name not in groups:
                    groups.append(name)

    return groups


class GUI_process(tk.Tk):
    """
    A gui allowing the user to process his data automatically

    Attributes
    ----------
    selected_files :
        Files selected by the user via file explorer

    process :
        key : process name
        value : method object

    frame_inputs :
        frame containing the selected files

    process_frame :
        frame containing all the available processes in NexusFile

    param_frame :
        frame containing all the parameters associated to the selected process

    progress_label :
        Label displaying the status of the application

    to_process:
        files that are to be processed
    """

    def __init__(self):
        self.selected_files = None
        self.process = {}
        for name, method in inspect.getmembers(NexusFile, predicate=inspect.isfunction):
            if name.startswith("process_"):
                self.process[name.removeprefix("process_")] = method

        super().__init__()
        self.iconbitmap(ICON_PATH)
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
        """
        Builds the input frame
        """
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

        self.do_batch = ttk.Checkbutton(self.frame_inputs, text="Join files and graphs")
        self.do_batch.grid(column=0, row=3, sticky="news")

    def _process_building(self):
        """
        Builds the frame containing all available processes
        """
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
        """
        Builds the param frame according to the selected process

        Parameters
        ----------
        process_name :
            Name of the process that will have his parameters
            displayed in the frame
        """
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
                param_name, param_value = param_str.split("=")
                label_param = tk.Label(self.param_frame,
                                       text=param_name,
                                       font=("Arial", 12))
                label_param.grid(column=0, row=current_row, pady=5, padx=5, sticky="w")

                if param_name == "group_name":
                    entry_param = ttk.Combobox(self.param_frame,
                                               font=("Arial", 12))
                    entry_param["values"] = get_group_names(self.selected_files)
                else:
                    entry_param = tk.Entry(self.param_frame,
                                           font=("Arial", 12))
                entry_param.insert(0, str(param_value.strip("'")))
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
            initialdir=TREATED_PATH,
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
        """
        Starting the selected process with the parameters filled out

        Parameters
        ----------
        process :
            name of the selected process
        """
        self.progress_label.configure(text="Processing in progress, please wait...",
                                      fg="#C16200")
        self.progress_label.update_idletasks()

        # We get the selected file
        self.to_process = []
        selected_index = self.file_list.curselection()

        for index in selected_index:
            self.to_process += [self.selected_files[index]]

        # We get the parameters and convert them
        param_dict = {}
        for widget in self.param_frame.winfo_children():
            if hasattr(widget, 'tag'):
                tag = widget.tag
                entry_value = str(widget.get())
                value = string_2_value(entry_value)
                param_dict[tag] = value

        # We fill out the parameters for every file

        nxfiles = NexusFile(self.to_process, self.do_batch.state())
        try:
            process(nxfiles, **param_dict)
        except Exception as exception:
            print(exception)
        nxfiles.nexus_close()
        self.progress_label.configure(text="No processing in progress",
                                      fg="#6DB06E")


if __name__ == "__main__":
    app = GUI_process()
    app.mainloop()
