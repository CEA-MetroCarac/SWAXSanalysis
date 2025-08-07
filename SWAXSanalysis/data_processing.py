"""
This module is meant to help the user process their data
"""
import copy
import inspect
import pathlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any
import matplotlib.pyplot as plt

import h5py
import time

import numpy as np

from . import DESKTOP_PATH, ICON_PATH
from . import FONT_TITLE, FONT_BUTTON, FONT_TEXT, FONT_LOG
from .class_nexus_file import NexusFile
from .utils import string_2_value, extract_from_h5, VerticalScrolledFrame


def get_group_names(
        file_list: list[pathlib.Path] | list[str]
) -> list[Any]:
    """
    This function finds the groups that are shared by
    all files in the file_list

    Parameters
    ----------
    file_list :
        List of the files' paths

    Returns :
        All groups shared by all the files
    """
    group_count = {}
    groups = []
    for file_path in file_list:
        with h5py.File(file_path, "r") as file_object:
            parent_group = file_object["/ENTRY"]

            for name in parent_group.keys():
                nx_class = str(extract_from_h5(
                    file_object,
                    f"/ENTRY/{name}",
                    "attribute",
                    "NX_class"
                ))

                if nx_class == "NXdata" and name not in groups:
                    if name in group_count.keys():
                        group_count[name] += 1
                    else:
                        group_count[name] = 1

    for group, count in group_count.items():
        if count == len(file_list):
            groups.append(group)

    return groups


class GUI_process(tk.Frame):
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

    frame_params :
        frame containing all the parameters associated to the selected process

    progress_label :
        Label displaying the status of the application

    to_process:
        files that are to be processed
    """

    def __init__(self, parent) -> None:
        self.selected_files = None
        self.process = {}
        self.to_process = []
        for name, method in inspect.getmembers(NexusFile, predicate=inspect.isfunction):
            if name.startswith("process_"):
                self.process[name.removeprefix("process_")] = method

        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.frame_inputs = VerticalScrolledFrame(self, width=100, height=300)
        self.frame_inputs.configure(border=5, relief="ridge")
        self.frame_inputs.grid(row=0, rowspan=3, column=0, sticky="nsew", pady=5, padx=5)
        self._inputs_building()

        self.frame_params = VerticalScrolledFrame(self, width=100, height=300)
        self.frame_params.configure(border=5, relief="ridge")
        self.frame_params.grid(row=0, rowspan=2, column=1, sticky="nsew", pady=5, padx=5)

        self.frame_log = tk.Frame(self, border=5, relief="ridge")
        self.frame_log.grid(row=0, rowspan=3, column=2, sticky="nsew", pady=5, padx=5)
        self._build_log()

        self.progress_label = tk.Label(
            self,
            text="No processing in progress",
            font=FONT_TITLE,
            fg="#6DB06E"
        )
        self.progress_label.grid(column=1, row=2, sticky="e", padx=5, pady=5)

    def _inputs_building(self) -> None:
        """
        Builds the input frame
        """
        self.frame_inputs.interior.columnconfigure(0, weight=1)
        self.frame_inputs.interior.columnconfigure(1, weight=1)
        frame_title = tk.Label(
            self.frame_inputs.interior,
            text="Inputs",
            font=FONT_TITLE,
            padx=10, pady=10)
        frame_title.grid(column=0, row=0, sticky="w", pady=(15, 20), padx=5, columnspan=2)

        browse_button = tk.Button(
            self.frame_inputs.interior,
            text="Upload files",
            font=FONT_BUTTON,
            command=self.browse_files,
            padx=20,
            pady=5)
        browse_button.grid(column=0, row=1, columnspan=2)

        self.file_list = tk.Listbox(self.frame_inputs.interior, selectmode=tk.MULTIPLE)
        self.file_list.grid(column=0, row=2, sticky="news", columnspan=2)
        self.file_list.configure(exportselection=False)

        select_all_button = tk.Button(
            self.frame_inputs.interior,
            text="Select all",
            font=FONT_BUTTON,
            command=lambda: self.file_list.selection_set(0, "end"),
            padx=20,
            pady=5)
        select_all_button.grid(column=0, row=3)

        unselect_all_button = tk.Button(
            self.frame_inputs.interior,
            text="Unselect all",
            font=FONT_BUTTON,
            command=lambda: self.file_list.selection_clear(0, "end"),
            padx=20,
            pady=5)
        unselect_all_button.grid(column=1, row=3)

        self.do_batch_var = tk.IntVar()
        self.do_batch = tk.Checkbutton(
            self.frame_inputs.interior,
            text="Join files and graphs",
            font=FONT_TEXT,
            variable=self.do_batch_var
        )
        self.do_batch.grid(column=0, row=4, sticky="we", columnspan=2)

        frame_title = tk.Label(
            self.frame_inputs.interior,
            text="Process options",
            font=FONT_TITLE
        )
        frame_title.grid(column=0, row=5, sticky="w", pady=(5, 20), padx=5)

        current_row = 6
        current_column = 0

        for process_name in self.process.keys():
            button_process = tk.Button(
                self.frame_inputs.interior,
                text=process_name.replace("_", " "),
                font=FONT_BUTTON,
                command=lambda name=process_name: self._create_params(name),
                width=20
            )
            button_process.grid(
                column=current_column,
                columnspan=2,
                row=current_row,
                padx=5,
                pady=5,
                sticky="news"
            )

            self.frame_inputs.interior.rowconfigure(current_row, weight=1)
            current_row += 1

    def _create_params(
            self,
            process_name: str
    ) -> None:
        """
        Builds the parameter frame according to the selected process

        Parameters
        ----------
        process_name :
            Name of the process that will have its parameters
            displayed in the frame
        """
        self.to_process = []
        selected_index = self.file_list.curselection()

        for index in selected_index:
            self.to_process += [self.selected_files[index]]

        if self.selected_files is None:
            self.print_log(
                "You didn't specify any file to process.\nCouldn't build parameters properly."
            )
            return
        if len(self.to_process) == 0:
            self.print_log(
                "You didn't select any file to process.\nCouldn't build parameters properly."
            )
            return

        self.frame_params.interior.columnconfigure(0, weight=0)
        self.frame_params.interior.columnconfigure(1, weight=1)

        for widget in self.frame_params.interior.winfo_children():
            widget.destroy()

        frame_title = tk.Label(
            self.frame_params.interior,
            text="Process parameters",
            font=FONT_TITLE,
        )
        frame_title.grid(column=0, columnspan=2, row=0, sticky="we", pady=(5, 20), padx=5)

        label_process = tk.Label(
            self.frame_params.interior,
            text=f"Process : {process_name}",
            font=FONT_TEXT
        )
        label_process.grid(column=0, columnspan=2, row=1, sticky="w", pady=(5, 20), padx=5)

        label_input_data = tk.Label(
            self.frame_params.interior,
            font=FONT_TEXT,
            text="input data group"
        )
        label_input_data.grid(column=0, row=2, pady=5, padx=5, sticky="w")

        self.input_data = ttk.Combobox(
            self.frame_params.interior,
            font=FONT_TEXT
        )
        self.input_data["values"] = get_group_names(self.to_process)
        self.input_data.current(0)
        self.input_data.grid(column=1, row=2, pady=5, padx=5, sticky="we")

        # We get the method and inspect it to get its parameters and default values
        method = self.process[process_name]
        signature = inspect.signature(method)
        param_list = list(signature.parameters.items())

        current_row = 3
        for param in param_list:
            self.frame_params.interior.rowconfigure(current_row, weight=1)
            if param[0] not in ["self"]:
                param_str = str(param[1])
                param_name_type, param_value = param_str.split("=")
                param_name, _ = param_name_type.split(":")
                label_param = tk.Label(
                    self.frame_params.interior,
                    text=param_name.replace("_", " "),
                    font=FONT_TEXT
                )
                label_param.grid(column=0, row=current_row, pady=5, padx=5, sticky="w")

                if param_name == "group_name":
                    entry_param = ttk.Combobox(
                        self.frame_params.interior,
                        font=FONT_TEXT
                    )
                    entry_param["values"] = get_group_names(self.to_process)
                elif param_name == "group_names":
                    entry_param = tk.Listbox(
                        self.frame_params.interior,
                        font=FONT_TEXT,
                        selectmode=tk.MULTIPLE,
                        exportselection=False
                    )
                    for group in get_group_names(self.to_process):
                        entry_param.insert(tk.END, group)
                elif param_name == "other_variable":
                    dict_var = {}
                    nx_file = NexusFile(self.to_process)
                    try:
                        dict_var = nx_file._detect_variables()
                    except Exception as error:
                        self.print_log(
                            f"{error}"
                        )
                    finally:
                        nx_file.nexus_close()

                    entry_param = ttk.Combobox(
                        self.frame_params.interior,
                        font=FONT_TEXT
                    )
                    entry_param["values"] = list(dict_var.keys()) + ["Index"]

                else:
                    entry_param = tk.Entry(self.frame_params.interior,
                                           font=FONT_TEXT)
                entry_param.insert(0, str(param_value.strip(" ").strip("'")))
                entry_param.grid(column=1, row=current_row, pady=5, padx=5, sticky="we")
                entry_param.tag = f"{param[0]}"
                current_row += 1

        confirm_button = tk.Button(
            self.frame_params.interior,
            text="Confirm",
            font=FONT_BUTTON,
            command=lambda process=method: self.after(0, self._start_processing(process))
        )
        confirm_button.grid(column=0, columnspan=2, row=current_row,
                            pady=15, padx=15)

    def _build_log(self) -> None:
        self.frame_log.columnconfigure(0, weight=1)
        self.frame_log.rowconfigure(1, weight=1)
        # Label
        title = tk.Label(
            self.frame_log,
            text="Log",
            font=FONT_TITLE
        )
        title.grid(pady=10, padx=10, row=0, column=0, sticky="news")

        # Log output area
        self.log_text = tk.Text(
            self.frame_log,
            font=FONT_LOG,
            width=20
        )
        self.log_text.grid(pady=10, padx=10, row=1, column=0, sticky="news")
        self.log_text.config(state=tk.NORMAL)

    def browse_files(self) -> None:
        """
        Method used to browse and select files
        """
        filenames = filedialog.askopenfilenames(
            initialdir=DESKTOP_PATH,
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

    def print_log(
            self,
            message: str
    ) -> None:
        """Function to print logs in the Tkinter Text widget."""

        def print_message():
            self.log_text.insert(tk.END, message + "\n\n")
            self.log_text.see(tk.END)

        self.after(
            0,
            print_message()
        )

        self.log_text.update_idletasks()

    def _start_processing(
            self,
            process
    ) -> None:
        """
        Starting the selected process with the parameters filled out

        Parameters
        ----------
        process :
            Callable method that needs to be applied
        """
        self.progress_label.configure(
            text="Processing in progress, please wait...",
            fg="#C16200"
        )
        self.print_log(
            "You're free to tab out of the window, but clicking on it might stop the log updates"
        )
        self.update()

        # We get the selected file
        self.to_process = []
        selected_index = self.file_list.curselection()

        for index in selected_index:
            self.to_process += [self.selected_files[index]]

        # We get the parameters and convert them
        param_dict = {}
        for widget in self.frame_params.interior.winfo_children():
            if hasattr(widget, 'tag'):
                tag = widget.tag
                if isinstance(widget, tk.Listbox):
                    entry_value = [string_2_value(widget.get(idx)) for idx in widget.curselection()]
                    value = entry_value
                else:
                    entry_value = str(widget.get())
                    value = string_2_value(entry_value)

                param_dict[tag] = value

        # We fill out the parameters for every file
        do_batch_state = bool(self.do_batch_var.get())
        # #############################
        # profiler = cProfile.Profile()
        # profiler.enable()
        # #############################

        self.print_log(
            f"Starting {process.__name__.removeprefix('process_').replace('_', ' ')}..."
        )

        if len(self.to_process) > 2:
            single_time = self._estimate_time(process, param_dict)

            self.print_log(
                f"Estimated process time :\n"
                f"{single_time * len(self.to_process)} seconds"
            )

        nxfiles = None
        try:
            nxfiles = NexusFile(self.to_process, do_batch_state, input_data_group=self.input_data.get())
            do_process, reason = self._pre_process_tests(
                param_dict=param_dict,
                process=process,
                do_batch_state=do_batch_state
            )

            if do_process:
                process(nxfiles, **param_dict)

                self.print_log(
                    f"{process.__name__.removeprefix('process_').replace('_', ' ')} "
                    f"done"
                )
            else:
                self.print_log(
                    f"{process.__name__.removeprefix('process_').replace('_', ' ')} "
                    f"has been canceled. Reason :\n{reason}"
                )

        except Exception as exception:
            self.print_log(
                str(exception)
            )
            raise exception
        finally:
            if nxfiles is not None:
                nxfiles.nexus_close()
            self.after(
                0,
                self.progress_label.configure(
                    text="No processing in progress",
                    fg="#6DB06E"
                )
            )
        # ####################################################
        # profiler.disable()
        # stats = pstats.Stats(profiler).sort_stats('tottime')
        # stats.print_stats()
        # ####################################################

    def _pre_process_tests(
            self,
            param_dict: dict,
            process,
            do_batch_state: bool

    ):
        do_process = True
        reason = ""

        display = param_dict.get("display", False)
        save = param_dict.get("save", False)
        if process.__name__.removeprefix('process_').replace('_', ' ') in ["display", "delete data"]:
            display = True
        if display or save:
            if display and not do_batch_state and len(self.to_process) > 16:
                yesno_answer = messagebox.askyesno(
                    "Confirm",
                    f"You're about to display {len(self.to_process)} graphs individually.\n"
                    f"Are you sure you do not want to use the 'Join files and graph' option ?"
                )

                do_process = do_process and yesno_answer

                if not yesno_answer:
                    reason += "Join files and graph wasn't checked"
        else:
            reason += "Display and Save are set to false.\n"
            do_process = do_process and False

        return do_process, reason

    def _estimate_time(
            self,
            process,
            param_dict: dict,
    ) -> float:
        """
        Function to estimate process time of one file
        Parameters
        ----------
        process :
            The process to estimate

        test_file :
            The file to test the execution time

        Returns :
            execution time of one file
        -------

        """
        param_dict_single = copy.deepcopy(param_dict)
        if "display" in param_dict_single.keys():
            param_dict_single["display"] = False
        if "save" in param_dict_single.keys():
            param_dict_single["save"] = False

        start_time = time.time()

        nx_test_file = None
        try:
            nx_test_file = NexusFile([self.to_process[0]], False, input_data_group=self.input_data.get())
            process(nx_test_file, **param_dict_single)
            if process.__name__.removeprefix('process_').replace('_', ' ') == "display":
                plt.close("all")
        except Exception as error:
            self.print_log(
                f"Error while estimating time :\n{error}"
            )
        finally:
            if nx_test_file is not None:
                nx_test_file.nexus_close()
            time_estimate = time.time() - start_time

        del param_dict_single

        time_estimate = np.round(time_estimate, 0)
        return time_estimate


if __name__ == "__main__":
    app = GUI_process()
    app.mainloop()
