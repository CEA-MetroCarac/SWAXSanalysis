"""
This module is to be executed by the user. It will create a GUI to convert
a .h5 file following the homebrewed NXsas format to an NXcanSAS
"""
import os
import tkinter as tk
from tkinter import filedialog

from saxs_nxformat.class_nexus_file import NexusFile


def find_hdf5_files(directory):
    """
    Recursively finds hdf5 files in the selected directory

    Parameters
    ----------
    directory :
        The directory that's going to be explored recursively

    Returns
    -------
     hdf5_files :
        A list of all the hdf5 files found in the folder and sub folders

    """
    hdf5_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".h5"):
                hdf5_files.append(os.path.join(root, file))
    return hdf5_files


class GUI(tk.Tk):
    """
    A GUI to manualy treat SAXS or WAXS data in the form of a
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
        super().__init__()
        self.focus_force()

        self.frame1 = tk.Frame(self)
        self.frame1.pack()
        self.title("NXsas2NXcanSAS")
        self.selected_files = None
        self.selected_folder = None

        # Label title
        label_title = tk.Label(self.frame1,
                               text="NXsas to NXcanSAS convertor",
                               font=("Arial", 16, "bold"))
        label_title.grid(column=0, row=0,
                         columnspan=2,
                         padx=10, pady=10)

        # Button to browse files
        button_files = tk.Button(self.frame1,
                                 text="Select Files",
                                 command=self.browse_files,
                                 fg="#7B8CDE",
                                 font=("Arial", 12, "bold"),
                                 padx=5)
        button_files.grid(column=0, row=1,
                          padx=5, pady=5)

        # Button to browse folder
        button_folder = tk.Button(self.frame1,
                                  text="Select Folder",
                                  command=self.browse_folder,
                                  fg="#7B8CDE",
                                  font=("Arial", 12, "bold"),
                                  padx=5)
        button_folder.grid(column=1, row=1,
                           padx=5, pady=5)

        # Label selection
        self.label_selection = tk.Label(self.frame1,
                                        text="No files selected",
                                        font=("Arial", 14, "bold"),
                                        fg="#BF3836")
        self.label_selection.grid(column=0, row=2,
                                  columnspan=2,
                                  padx=10, pady=10)

        # Label conversion
        self.label_status = tk.Label(self.frame1,
                                     text="Status : Waiting to start conversion",
                                     font=("Arial", 14, "bold"),
                                     fg="#BF3836")
        self.label_status.grid(column=0, row=3,
                               columnspan=2,
                               padx=10, pady=10)

        # Button to close
        button_convert = tk.Button(self.frame1,
                                   text="Close",
                                   command=lambda: self.destroy(),
                                   font=("Arial", 14, "bold"))
        button_convert.grid(column=0, row=4,
                            padx=10, pady=10)

        # Button to convert
        button_convert = tk.Button(self.frame1,
                                   text="Convert",
                                   command=self.engage_convert,
                                   font=("Arial", 14, "bold"))
        button_convert.grid(column=1, row=4,
                            padx=10, pady=10)

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
        self.selected_folder = None
        self.label_selection.configure(text=f"{len(filenames)} files selected !",
                                       fg="#6DB06E")

    def browse_folder(self):
        """
        Method used to select a folder
        """
        foldername = filedialog.askdirectory(
            initialdir="./",
            title="Select Folder"
        )
        self.selected_folder = foldername
        self.selected_files = None
        self.label_selection.configure(text="Folder selected !",
                                       fg="#6DB06E")

    def engage_convert(self):
        """
        Method to start the conversion process
        """
        self.label_status.configure(text="Status : conversion in progress, please wait...",
                                    fg="#C16200")
        self.after(100, self.start_convert)

    def start_convert(self):
        """
        Actual conversion process
        """
        if self.selected_folder:
            self.selected_files = find_hdf5_files(self.selected_folder)
        elif self.selected_folder is None and self.selected_files is None:
            tk.messagebox.showerror("error", "No file or folder selected")
            return

        for path in self.selected_files:
            print(path)
            file = NexusFile(path)
            file.process_q_space(display=False, save=True)
            file.process_radial_average(display=False, save=True)
            file.close()
        self.label_status.configure(text="Status : conversion successfull",
                                    fg="#6DB06E")


if __name__ == "__main__":
    app = GUI()
    app.mainloop()
