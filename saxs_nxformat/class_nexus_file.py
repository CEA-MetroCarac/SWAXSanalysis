"""
The main feature of this module is the NexusFile class which is used
to treat raw data contained in a .h5 file formated according
to the NXcanSAS standard
TODO : Add smoothing method?
"""
import copy
import inspect
import os
import shutil
import time
from pathlib import Path

import matplotlib.pyplot as plt
from smi_analysis import SMI_beamline

from . import PLT_CMAP, PLT_CMAP_OBJ
from .utils import *


def repack_hdf5(
        input_file: str | Path,
        output_file: str | Path
) -> None:
    """
    Repack an HDF5 file to reduce its size by copying its content to a new file.

    Parameters
    ----------
    input_file :
        Path to the input HDF5 file.

    output_file :
        Path to the output (repacked) HDF5 file.
    """
    with h5py.File(input_file, 'r') as src, h5py.File(output_file, 'w') as dest:
        src.copy("/ENTRY", dest)
    os.remove(input_file)
    shutil.move(output_file, input_file)


def create_process(
        hdf5_file: h5py.File,
        group_h5path: str,
        process_name: str,
        process_desc: str
) -> None:
    """
    Function used to create a new group in the hdf5 file that will contain pertinent information
    concerning the process that was applied.

    Parameters
    ----------
    hdf5_file :
        File where the process is to be saved

    group_h5path :
        Path of the process group, this will define the group's name.
        For clarity this should be PROCESS_... the ellipsis corresponding
        to the name of the associated DATA_... group

    process_name :
        Name of the process

    process_desc :
        Description of the process
    """
    # We first delete the old process if it exists
    if hdf5_file.get(group_h5path):
        del hdf5_file[group_h5path]

    # We then create the group and set its attributes and datasets
    group = hdf5_file.create_group(group_h5path)
    group.attrs["canSAS_class"] = "SASprocess"

    group.create_dataset("name", data=process_name)
    group.create_dataset("description", data=process_desc)


def extract_smi_param(
        h5obj: h5py.File,
        input_data_group: str
) -> dict:
    """
    Extract the parameters used by SMI from an hdf5 object.
    the h5 file must follow the NXcanSAS standard
    Parameters
    ----------
    h5obj :
        opened h5 file that contains the parameters

    input_data_group :
        Data group used to extract parameters

    Returns :
        parameters used by SMI
    -------
    """
    dict_parameters = {
        "beam stop": [[0, 0]]
    }

    # We extract the relevant info from the H5 file
    if f"ENTRY/{input_data_group}" not in h5obj:
        raise KeyError(
            f"the group ENTRY/{input_data_group} "
            f"is not a node of the current file"
        )

    intensity_data = [h5obj[f"ENTRY/{input_data_group}/I"][:]]

    if len(np.shape(intensity_data[0])) != 2:
        raise TypeError(
            f"The shape of the data in ENTRY/{input_data_group} "
            f"is not 2 dimensional"
        )

    position_data = [h5obj[f"ENTRY/{input_data_group}/Q"][:]]
    dict_parameters["I raw data"] = intensity_data
    dict_parameters["R raw data"] = position_data

    # Concerning the source
    wavelength = extract_from_h5(h5obj, "ENTRY/INSTRUMENT/SOURCE/incident_wavelength")
    dict_parameters["wavelength"] = wavelength * 1e-9

    # Concerning the sample
    incident_angle = extract_from_h5(h5obj, "ENTRY/SAMPLE/yaw")
    dict_parameters["incident angle"] = 0

    # Concerning the detector
    # We use a regex that detects the keyword required in the detector's name
    detector_name = extract_from_h5(h5obj, "/ENTRY/INSTRUMENT/DETECTOR/name").decode("utf-8")
    if re.search(
            "(?i)(?=.*dectris)" +
            "(?i)(?=.*eiger2)" +
            "(?i)(?=.*1m)",
            detector_name.lower()
    ):
        dict_parameters["detector name"] = "Eiger1M_xeuss"
        dict_parameters["detector rotation"] = [[0, 0, 0]]

    if re.search(
            "(?i)(?=.*" + "dectris" + ")" +
            "(?i)(?=.*" + "eiger2" + ")" +
            "(?i)(?=.*" + "500k" + ")",
            detector_name.lower()
    ):
        dict_parameters["detector name"] = "Eiger500k_xeuss"
        rotation_1 = - extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/yaw")
        rotation_2 = extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/pitch")
        rotation_3 = - extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/roll")
        dict_parameters["detector rotation"] = [[rotation_1, rotation_2, rotation_3]]

    # Concerning the beamcenter
    beam_center_x = extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/beam_center_x")
    beam_center_y = extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/beam_center_y")
    dict_parameters["beam center"] = [beam_center_x, beam_center_y]

    # Concerning the sample-detector distance
    sample_detector_distance = extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/SDD")
    dict_parameters["distance"] = sample_detector_distance * 1e3

    return dict_parameters


class NexusFile:
    """
    A class that can load and treat data formated in the NXcanSAS standard

    Attributes
    ----------
    file_paths :
        list of path of the treated file

    nx_files :
        List of loaded file

    dicts_parameters :
        list of dictionary of all releavant parameters associated to each files

    list_smi_data :
        list of Stitched data using the SMI package
    """

    def __init__(
            self,
            h5_paths: list[str] | list[Path],
            do_batch: bool = False,
            input_data_group: str = "DATA"
    ) -> None:
        """
        The init of this class consists of extracting every releavant parameters
        from the h5 file.

        Parameters
        ----------
        h5_paths
            The path of the h5 files we want to open passed as a list of strings

        do_batch :
            Determines wether the data is assembled in a new file or not and whether it is
            displayed a single figure or not
        """
        if isinstance(h5_paths, list):
            for path in h5_paths:
                if not isinstance(path, str) and not isinstance(path, Path):
                    raise TypeError(
                        f"Your list of path contains something other than a string or Path :"
                        f"{path} is not a string or a Path object"
                    )
            self.file_paths = h5_paths
        else:
            raise TypeError(
                "You tried to pass the path of the file(s) you want to open "
                "as something other than a list."
            )

        self.init_plot = True
        self.fig = None
        self.ax = None
        self.do_batch = do_batch
        self.input_data_group = input_data_group

        self.dicts_parameters = []
        self.list_smi_data = []

        self.nx_files = []

        for file_path in self.file_paths:
            nx_file = h5py.File(file_path, "r+")
            self.nx_files.append(nx_file)

            dict_parameters = extract_smi_param(nx_file, self.input_data_group)
            self.dicts_parameters.append(dict_parameters)

    def _stitching(self):
        self.list_smi_data = []
        for dict_param in self.dicts_parameters:
            dict_parameters = dict_param

            # We input the info in the SMI package
            smi_data = SMI_beamline.SMI_geometry(
                geometry="Transmission",
                sdd=dict_parameters["distance"],
                wav=dict_parameters["wavelength"],
                alphai=dict_parameters["incident angle"],
                center=dict_parameters["beam center"],
                bs_pos=dict_parameters["beam stop"],
                detector=dict_parameters["detector name"],
                det_angles=dict_parameters["detector rotation"]
            )
            smi_data.open_data_db(dict_parameters["I raw data"])
            smi_data.stitching_data()

            self.list_smi_data.append(smi_data)

    def show_method(
            self,
            method_name: str | None = None
    ) -> str:
        """
        Method allowing to display the docstring
        of any methods from this class

        Parameters
        ----------
        method_name:
            Name of the method to display. If is None, will display
            all available method to display

        Return:
            the Doc string of the selected method
        -------
        """
        return_string = ""
        for name, method in inspect.getmembers(NexusFile, predicate=inspect.isfunction):
            if method_name is None or method_name == name:
                return_string += f"\n{name}"
            if method_name == name:
                return_string += f"\nDocstring : {method.__doc__}"
                signature = inspect.signature(method)
                param_list = list(signature.parameters.items())
                for param in param_list:
                    if param[0] != "self":
                        param_str = str(param[1])
                        return_string += f"\n    {param_str}"
        if method_name is None:
            return_string += \
                "\nPlease rerun this function and pass the name of one method as a parameter\n" \
                "to get more information concerning this particular method"
        return return_string

    def get_file(self) -> list[h5py.File]:
        """
        Getter of the actual h5 files
        """
        return self.nx_files

    def add_file(
            self,
            new_h5_paths: list[str] | list[Path]
    ) -> None:
        """
        Allows for the addition of more file to
        an already opened object from this class

        Parameters
        ----------
        new_h5_paths:
            Path list of all the files that need to be added
        """

        if isinstance(new_h5_paths, list):
            for path in new_h5_paths:
                if not isinstance(path, str) and not isinstance(path, Path):
                    raise TypeError(
                        "Your list of path contains something other than a string or Path :"
                        f"{path} is not a string or a Path object"
                    )
            self.file_paths = self.file_paths + new_h5_paths
        else:
            raise TypeError(
                "You tried to pass the path of the file(s) you want to open "
                "as something other than a list."
            )

        for file_path in new_h5_paths:
            nx_file = h5py.File(file_path, "r+")
            self.nx_files.append(nx_file)

            dict_parameters = extract_smi_param(nx_file, self.input_data_group)
            self.dicts_parameters.append(dict_parameters)

    def get_raw_data(
            self,
            group_name: str = "DATA_Q_SPACE"
    ) -> tuple[dict[str, np.ndarray | None], dict[str, np.ndarray]]:
        """
        Get raw data of the group name. The parameter and intensity are returned as python dict :
            - key : file name
            - value : param | intensity

        Parameters
        ----------
        group_name :
            name of the group that contains the data to extract

        Returns
        -------
        2 dict :
            - The first one contains the parameter
            - The second one contains the intensity

        """
        extracted_value_data = {}
        extracted_param_data = {}
        for index, nxfile in enumerate(self.nx_files):
            file_path = Path(self.file_paths[index])
            file_name = file_path.name
            if f"ENTRY/{group_name}" in nxfile:
                extracted_value_data[file_name] = \
                    np.array(extract_from_h5(nxfile, f"ENTRY/{group_name}/I"))

            if f"ENTRY/{group_name}/R" in nxfile:
                extracted_param_data[file_name] = \
                    np.array(extract_from_h5(nxfile, f"ENTRY/{group_name}/R"))
            elif f"ENTRY/{group_name}/Q" in nxfile:
                extracted_param_data[file_name] = \
                    np.array(extract_from_h5(nxfile, f"ENTRY/{group_name}/Q"))
            elif f"ENTRY/{group_name}/Chi" in nxfile:
                extracted_param_data[file_name] = \
                    np.array(extract_from_h5(nxfile, f"ENTRY/{group_name}/Chi"))
            else:
                extracted_param_data[file_name] = None

        return extracted_param_data, extracted_value_data

    def get_parameters(self):
        """
        Getter of the dict containing parameters used for SMI analysis

        Returns:
            dict of parameters
        -------

        """
        param_dict = {}
        for index, file_path in enumerate(self.file_paths):
            file_path = Path(file_path)
            file_name = file_path.name

            param_dict[file_name] = self.dicts_parameters[index]
        return param_dict

    def get_process_desc(
            self,
            group_name: str = "PROCESS_Q_SPACE"
    ) -> dict[str, Any]:
        """
        Getter of a process' description

        Parameters
        ----------
        group_name :
            Name of the group from which the description is extracted

        Returns
        -------
        Description of the process as a string
        """
        extracted_description = {}
        for index, nxfile in enumerate(self.nx_files):
            file_path = Path(self.file_paths[index])
            file_name = file_path.name
            if f"ENTRY/{group_name}" in nxfile:
                string = extract_from_h5(
                    nxfile,
                    f"ENTRY/{group_name}/description"
                ).decode("utf-8")
                extracted_description[file_name] = string

        return extracted_description

    def process_q_space(
            self,
            display: bool = False,
            save: bool = False,
            group_name: str = "DATA_Q_SPACE",
            percentile: float | int = 99
    ) -> None:
        """
        Method used to put the data in Q space (Fourier space).
        This will save an array containing the intensity values
        and another array containing the vector Q associated
        to each intensities

        Parameters
        ----------
        percentile :
            Controls the intensity range. It will go from 0 to percentile / 100 * (max intensity)

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        self.init_plot = True

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = extract_from_h5(
                self.nx_files[index],
                f"/ENTRY/{self.input_data_group}/mask"
            )
            smi_data.calculate_integrator_trans(
                self.dicts_parameters[index]["detector rotation"]
            )

            dim = np.shape(self.dicts_parameters[index]["R raw data"][0])
            qx_list = np.linspace(smi_data.qp[0], smi_data.qp[-1], dim[2])
            qy_list = np.linspace(smi_data.qz[-1], smi_data.qz[0], dim[1])
            qx_grid, qy_grid = np.meshgrid(qx_list, qy_list)

            mesh_q = np.stack((qx_grid, qy_grid), axis=-1)

            mesh_q = np.moveaxis(mesh_q, (0, 1, 2), (1, 2, 0))

            if display:
                self._display_data(
                    index, self.nx_files[index],
                    extracted_param_data=mesh_q,
                    extracted_value_data=smi_data.img_st,
                    label_x="$q_{hor} (A^{-1})$",
                    label_y="$q_{ver} (A^{-1})$",
                    title="2D Data in q-space",
                    percentile=percentile
                )

            # Saving the data and the process it just went trough
            if save:
                mask = smi_data.masks

                save_data(self.nx_files[index], group_name, "Q", mesh_q, smi_data.img_st, mask)

                create_process(
                    self.nx_files[index],
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Conversion to q-space",
                    "This process converts the 2D array Q containing the position in A into a 2D "
                    "array containing the positions in q-space, A^-1.\n"
                    "Each element of the array Q is a vector containing qx and qy"
                )

    def process_caking(
            self,
            display: bool = False,
            save: bool = False,
            group_name: str = "DATA_CAKED",
            azi_min: None | float | int = None,
            azi_max: None | float | int = None,
            pts_azi: None | int = None,
            radial_min: None | float | int = None,
            radial_max: None | float | int = None,
            pts_rad: None | int = None,
            percentile: float | int = 99
    ) -> None:
        """
        Method used to cake the data.
        This will display the data in the (q_r, chi) coordinate system.

        Parameters
        ----------
        percentile :
            Controls the intensity range.
            It will go from 0 to percentile / 100 * (max intensity)

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data

        pts_rad:
            Number of point in the radial range

        radial_max:
            Maximum of the radial range

        radial_min:
            Minimum of the radial range

        pts_azi:
            Number of point in the azimuthal range

        azi_max:
            Maximum of the azimuthal angle range

        azi_min:
            Minimum of the azimuthal angle range
        """
        self.init_plot = True

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        initial_none_flags = {
            "azi_min": azi_min is None,
            "azi_max": azi_max is None,
            "radial_min": radial_min is None,
            "radial_max": radial_max is None,
            "pts_azi": pts_azi is None,
            "pts_rad": pts_rad is None,
        }

        for index, smi_data in enumerate(self.list_smi_data):
            defaults = {
                "azi_min": -180,
                "azi_max": 180,
                "radial_min": min(smi_data.qz),
                "radial_max": max(smi_data.qz),
                "pts_azi": 1000,
                "pts_rad": 1000,
            }

            # Set default values if parameters are None
            if initial_none_flags["azi_min"]:
                azi_min = defaults["azi_min"]
            if initial_none_flags["azi_max"]:
                azi_max = defaults["azi_max"]
            if initial_none_flags["radial_min"]:
                radial_min = defaults["radial_min"]
            if initial_none_flags["radial_max"]:
                radial_max = defaults["radial_max"]
            if initial_none_flags["pts_azi"]:
                pts_azi = defaults["pts_azi"]
            if initial_none_flags["pts_rad"]:
                pts_rad = defaults["pts_rad"]

            smi_data.caking(
                azimuth_range=[azi_min, azi_max],
                radial_range=[radial_min, radial_max],
                npt_azim=pts_azi,
                npt_rad=pts_rad
            )

            q_list = smi_data.q_cake
            chi_list = smi_data.chi_cake
            q_grid, chi_grid = np.meshgrid(q_list, chi_list)

            mesh_cake = np.stack((q_grid, chi_grid), axis=-1)

            mesh_cake = np.moveaxis(mesh_cake, (0, 1, 2), (1, 2, 0))

            if display:
                self._display_data(
                    index, self.nx_files[index],
                    extracted_param_data=mesh_cake,
                    extracted_value_data=smi_data.cake,
                    scale_x="log", scale_y="log",
                    label_x="$q_r (A^{-1})$",
                    label_y="$\\chi$",
                    title="Caked q-space data",
                    percentile=percentile
                )

            if save:
                mask = smi_data.masks

                save_data(self.nx_files[index], group_name, "Q", mesh_cake, smi_data.cake, mask)

                create_process(
                    self.nx_files[index],
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Data caking",
                    "This process plots the intensity with respect to "
                    "the azimuthal angle and the distance "
                    "from the center of the q-space.\n"
                    "Parameters used :\n"
                    f"   - Azimuthal range : [{azi_min:.4f}, {azi_max:.4f}] with {pts_azi} points\n"
                    f"   - Radial Q range : [{radial_min:.4f}, {radial_max:.4f}] with {pts_rad} points\n"
                )

    def process_radial_average(
            self,
            display: bool = False,
            save: bool = False,
            group_name: str = "DATA_RAD_AVG",
            r_min: None | float | int = None,
            r_max: None | float | int = None,
            angle_min: None | float | int = None,
            angle_max: None | float | int = None,
            pts: None | int = None
    ) -> None:
        """
        Method used to perform radial averaging of data in Fourier space.
        This will reduce the signal to one dimension :
        intensity versus distance from the center

        Parameters
        ----------
        display : bool, optional
            Choose if you want the result displayed or not.

        save : bool, optional
            Choose if you want the result saved in the .h5 or not.

        group_name : str, optional
            Name of the group that will contain the data.

        r_min : float, optional
            Minimum radial value for averaging.

        r_max : float, optional
            Maximum radial value for averaging.

        angle_min : float, optional
            Minimum angle for averaging.

        angle_max : float, optional
            Maximum angle for averaging.

        pts : int, optional
            Number of points for the averaging process.
        """
        self.init_plot = True

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        initial_none_flags = {
            "r_min": r_min is None,
            "r_max": r_max is None,
            "angle_min": angle_min is None,
            "angle_max": angle_max is None,
            "pts": pts is None,
        }

        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = extract_from_h5(
                self.nx_files[index],
                f"/ENTRY/{self.input_data_group}/mask"
            )

            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            if np.sum(np.sign(smi_data.qp) + np.sign(smi_data.qz)) == 0:
                default_r_min = 0
            elif np.sign(smi_data.qp[-1]) == np.sign(smi_data.qp[0]):
                default_r_min = np.sqrt(min(np.abs(smi_data.qz)) ** 2)
            elif np.sign(smi_data.qz[-1]) == np.sign(smi_data.qz[0]):
                default_r_min = np.sqrt(min(np.abs(smi_data.qp)) ** 2)
            else:
                default_r_min = np.sqrt(
                    min(np.abs(smi_data.qp)) ** 2 + min(np.abs(smi_data.qz)) ** 2
                )

            defaults = {
                "r_max": np.sqrt(
                    max(np.abs(smi_data.qp)) ** 2 + max(np.abs(smi_data.qz)) ** 2
                ),
                "r_min": default_r_min,
                "angle_min": -180,
                "angle_max": 180,
                "pts": 2000
            }

            if initial_none_flags["r_min"]:
                r_min = defaults["r_min"]
            if initial_none_flags["r_max"]:
                r_max = defaults["r_max"]
            if initial_none_flags["angle_min"]:
                angle_min = defaults["angle_min"]
            if initial_none_flags["angle_max"]:
                angle_max = defaults["angle_max"]
            if initial_none_flags["pts"]:
                pts = defaults["pts"]

            smi_data.radial_averaging(
                azimuth_range=[angle_min, angle_max],
                npt=pts,
                radial_range=[r_min, r_max]
            )

            if display:
                self._display_data(
                    index, self.nx_files[index],
                    extracted_param_data=smi_data.q_rad, extracted_value_data=smi_data.I_rad,
                    scale_x="log", scale_y="log",
                    label_x="$q_r (A^{-1})$",
                    label_y="Intensity (a.u.)",
                    title=f"Radial integration over the regions \n "
                          f"[{angle_min:.4f}, {angle_max:.4f}] and [{r_min:.4f}, {r_max:.4f}]"
                )

            if save:
                q_list = smi_data.q_rad
                i_list = smi_data.I_rad
                mask = smi_data.masks
                save_data(self.nx_files[index], group_name, "Q", q_list, i_list, mask)

                create_process(
                    self.nx_files[index],
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Radial averaging",
                    "This process integrates the intensity signal over a specified radial angle range"
                    "and radial q range.\n"
                    "Parameters used :\n"
                    f"   - Azimuthal range : [{angle_min:.4f}, {angle_max:.4f}]\n"
                    f"   - Radial Q range : [{r_min:.4f}, {r_max:.4f}] with {pts} points\n"
                )

    def process_azimuthal_average(
            self,
            display: bool = False,
            save: bool = False,
            group_name: str = "DATA_AZI_AVG",
            r_min: None | float | int = None,
            r_max: None | float | int = None,
            npt_rad: None | int = None,
            angle_min: None | float | int = None,
            angle_max: None | float | int = None,
            npt_azi: None | int = None
    ) -> None:
        """
        Method used to do the radial average of the data in fourier space

        Parameters
        ----------
        npt_azi :
            Number of points in the azimuthal range

        npt_rad :
            Number of points in the radial range

        angle_max :
            Maximum azimuthal angle

        angle_min :
            Minimum azimuthal angle

        r_max :
            Maximum distance from the center

        r_min :
            Minimum distance from the center

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """

        self.init_plot = True

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        initial_none_flags = {
            "r_min": r_min is None,
            "r_max": r_max is None,
            "npt_rad": npt_rad is None,
            "angle_min": angle_min is None,
            "angle_max": angle_max is None,
            "npt_azi": npt_azi is None
        }

        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = extract_from_h5(
                self.nx_files[index],
                f"/ENTRY/{self.input_data_group}/mask"
            )
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            if np.sum(np.sign(smi_data.qp) + np.sign(smi_data.qz)) == 0:
                r_min = 0
            elif np.sign(smi_data.qp[-1]) == np.sign(smi_data.qp[0]):
                r_min = np.sqrt(min(np.abs(smi_data.qz)) ** 2)
            elif np.sign(smi_data.qz[-1]) == np.sign(smi_data.qz[0]):
                r_min = np.sqrt(min(np.abs(smi_data.qp)) ** 2)
            else:
                r_min = np.sqrt(min(np.abs(smi_data.qp)) ** 2 + min(np.abs(smi_data.qz)) ** 2)

            defaults = {
                "r_max": np.sqrt(max(np.abs(smi_data.qp)) ** 2 + max(np.abs(smi_data.qz)) ** 2),
                "r_min": r_min,
                "npt_rad": 500,
                "angle_min": -180,
                "angle_max": 180,
                "npt_azi": 500
            }

            if initial_none_flags["r_min"]:
                r_min = defaults["r_min"]
            if initial_none_flags["r_max"]:
                r_max = defaults["r_max"]
            if initial_none_flags["npt_rad"]:
                npt_rad = defaults["npt_rad"]
            if initial_none_flags["angle_min"]:
                angle_min = defaults["angle_min"]
            if initial_none_flags["angle_max"]:
                angle_max = defaults["angle_max"]
            if initial_none_flags["npt_azi"]:
                npt_azi = defaults["npt_azi"]

            smi_data.azimuthal_averaging(
                azimuth_range=[angle_min, angle_max],
                npt_azim=npt_azi,
                radial_range=[r_min, r_max],
                npt_rad=npt_rad
            )

            if display:
                self._display_data(
                    index, self.nx_files[index],
                    extracted_param_data=np.deg2rad(smi_data.chi_azi),
                    extracted_value_data=smi_data.I_azi,
                    scale_x="linear", scale_y="log",
                    label_x="$\\chi (rad)$",
                    label_y="Intensity (a.u.)",
                    title=f"Azimuthal integration over the regions \n "
                          f"[{angle_min:.4f}, {angle_max:.4f}] and [{r_min:.4f}, {r_max:.4f}]"
                )

            if save:
                chi_list = np.deg2rad(smi_data.chi_azi)
                i_list = smi_data.I_azi
                mask = smi_data.masks
                save_data(self.nx_files[index], group_name, "Chi", chi_list, i_list, mask)
                create_process(
                    self.nx_files[index],
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Azimuthal averaging",
                    "This process integrates the intensity signal over a specified azimuthal angle range"
                    " and radial q range.\n"
                    "Parameters used :\n"
                    f"   - Azimuthal range : [{angle_min:.4f}, {angle_max:.4f}] with {npt_azi} points\n"
                    f"   - Radial Q range : [{r_min:.4f}, {r_max:.4f}] with {npt_rad} points\n"
                )

    def process_horizontal_integration(
            self,
            display: bool = False,
            save: bool = False,
            group_name: str = "DATA_HOR_INT",
            qx_min: None | float | int = None,
            qx_max: None | float | int = None,
            qy_min: None | float | int = None,
            qy_max: None | float | int = None
    ) -> None:
        """
        Method used to perform horizontal integration of the data in Fourier space.

        Parameters
        ----------
        qy_max :
            Maximum of the q_y range

        qy_min :
            Minimum onf the q_y range

        qx_max :
            Maximum of the q_x range

        qx_min :
            Minimum of the q_x range

        display : bool, optional
            Choose if you want the result displayed or not.

        save : bool, optional
            Choose if you want the result saved in the .h5 or not.

        group_name : str, optional
            Name of the group that will contain the data.

        """
        self.init_plot = True

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        initial_none_flags = {
            "qx_min": qx_min is None,
            "qx_max": qx_max is None,
            "qy_min": qy_min is None,
            "qy_max": qy_max is None,
        }

        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = extract_from_h5(
                self.nx_files[index],
                f"/ENTRY/{self.input_data_group}/mask"
            )
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            defaults = {
                "qx_min": smi_data.qp[0],
                "qx_max": smi_data.qp[-1],
                "qy_min": smi_data.qz[0],
                "qy_max": smi_data.qz[-1]
            }

            if initial_none_flags["qx_min"]:
                qx_min = defaults["qx_min"]
            if initial_none_flags["qx_max"]:
                qx_max = defaults["qx_max"]
            if initial_none_flags["qy_min"]:
                qy_min = defaults["qy_min"]
            if initial_none_flags["qy_max"]:
                qy_max = defaults["qy_max"]

            smi_data.horizontal_integration(
                q_per_range=[qy_min, qy_max],
                q_par_range=[qx_min, qx_max]
            )

            if display:
                self._display_data(
                    index, self.nx_files[index],
                    extracted_param_data=smi_data.q_hor, extracted_value_data=smi_data.I_hor,
                    scale_x="log", scale_y="log",
                    label_x="$q_{ver} (A^{-1})$",
                    label_y="Intensity (a.u.)",
                    title=f"Vertical integration in the region \n "
                          f"[{qy_min:.4f}, {qy_max:.4f}] and [{qx_min:.4f}, {qx_max:.4f}]"
                )

            if save:
                q_list = smi_data.q_hor
                i_list = smi_data.I_hor
                mask = smi_data.masks
                save_data(self.nx_files[index], group_name, "Q", q_list, i_list, mask)

                create_process(
                    self.nx_files[index],
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Horizontal integration",
                    "This process integrates the intensity signal "
                    "over a specified horizontal strip in "
                    "q-space.\n"
                    "Parameters used :\n"
                    f"   - Horizontal Q range : [{qx_min:.4f}, {qx_max:.4f}]\n"
                    f"   - Vertical Q range : [{qx_min:.4f}, {qx_max:.4f}]\n"
                )

    def process_vertical_integration(
            self,
            display: bool = False,
            save: bool = False,
            group_name: str = "DATA_VER_INT",
            qx_min: None | float | int = None,
            qx_max: None | float | int = None,
            qy_min: None | float | int = None,
            qy_max: None | float | int = None
    ) -> None:
        """
        Method used to do the vertical integration of the data in fourier space.

        Parameters
        ----------
        qy_max :
            Maximum of the q_y range

        qy_min :
            Minimum onf the q_y range

        qx_max :
            Maximum of the q_x range

        qx_min :
            Minimum of the q_x range

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        self.init_plot = True

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        initial_none_flags = {
            "qx_min": qx_min is None,
            "qx_max": qx_max is None,
            "qy_min": qy_min is None,
            "qy_max": qy_max is None,
        }

        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = extract_from_h5(
                self.nx_files[index],
                f"/ENTRY/{self.input_data_group}/mask"
            )
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            defaults = {
                "qx_min": smi_data.qp[0],
                "qx_max": smi_data.qp[-1],
                "qy_min": smi_data.qz[0],
                "qy_max": smi_data.qz[-1]
            }

            if initial_none_flags["qx_min"]:
                qx_min = defaults["qx_min"]
            if initial_none_flags["qx_max"]:
                qx_max = defaults["qx_max"]
            if initial_none_flags["qy_min"]:
                qy_min = defaults["qy_min"]
            if initial_none_flags["qy_max"]:
                qy_max = defaults["qy_max"]

            smi_data.vertical_integration(
                q_per_range=[qy_min, qy_max],
                q_par_range=[qx_min, qx_max]
            )

            if display:
                self._display_data(
                    index, self.nx_files[index],
                    group_name=group_name,
                    extracted_param_data=smi_data.q_ver, extracted_value_data=smi_data.I_ver,
                    scale_x="log", scale_y="log",
                    label_x="$q_{hor} (A^{-1})$",
                    label_y="Intensity (a.u.)",
                    title=f"Vertical integration in the region \n "
                          f"[{qy_min:.4f}, {qy_max:.4f}] and [{qx_min:.4f}, {qx_max:.4f}]"
                )

            if save:
                q_list = smi_data.q_ver
                i_list = smi_data.I_ver
                mask = smi_data.masks
                save_data(self.nx_files[index], group_name, "Q", q_list, i_list, mask)

                create_process(
                    self.nx_files[index],
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Vertical integration",
                    "This process integrates the intensity signal over a specified vertical strip in "
                    "q-space\n"
                    "Parameters used :\n"
                    f"   - Horizontal Q range : [{qx_min:.4f}, {qx_max:.4f}]\n"
                    f"   - Vertical Q range : [{qx_min:.4f}, {qx_max:.4f}]\n"
                )

    def process_absolute_intensity(
            self,
            db_path: Path | str = "",
            group_name: str = "DATA_ABS",
            display: bool = False,
            save: bool = False,
            roi_size_x: int = 30,
            roi_size_y: int = 30,
            sample_thickness: float = 1,
    ):
        """
        This process convert the intensities in your file into absolute intensities.

        Parameters
        ----------
        group_name :
            name fo the group where the data is going to be saved

        save :
            Choose whether you want to save tha data or not

        display :
            Choose whether you want to display tha data or not

        sample_thickness :
            The thickness of the sample

        db_path :
            path of the direct beam data

        roi_size_x :
            Horizontal size of the region of interest. By default gets the beam size of the HDF5

        roi_size_y :
            Vertical size of the region of interest. By default gets the beam size of the HDF5
        """
        if db_path is None:
            raise TypeError("No direct beam data path provided")

        if len(self.file_paths) != len(self.list_smi_data):
            self._stitching()

        initial_none_flags = {
            "roi_size_x": roi_size_x is None,
            "roi_size_y": roi_size_y is None,
            "sample_thickness": sample_thickness is None,
        }

        self.init_plot = True
        for index, nx_file in enumerate(self.nx_files):

            defaults = {
                "roi_size_x": extract_from_h5(nx_file, "ENTRY/INSTRUMENT/SOURCE/beam_size_x"),
                "roi_size_y": extract_from_h5(nx_file, "ENTRY/INSTRUMENT/SOURCE/beam_size_y"),
                "sample_thickness": extract_from_h5(nx_file, "ENTRY/SAMPLE/thickness"),
            }

            if initial_none_flags["roi_size_x"]:
                roi_size_x = defaults["roi_size_x"]
            if initial_none_flags["roi_size_y"]:
                roi_size_y = defaults["roi_size_y"]
            if initial_none_flags["sample_thickness"]:
                sample_thickness = defaults["sample_thickness"]

            positions = self.dicts_parameters[index]["R raw data"][0]

            raw_data = self.dicts_parameters[index]["I raw data"][0]
            beam_center_x = int(self.dicts_parameters[index]["beam center"][0])
            beam_center_y = int(self.dicts_parameters[index]["beam center"][1])
            expo_time = extract_from_h5(nx_file, "ENTRY/COLLECTION/exposition_time")

            i_roi_data = np.sum(
                raw_data[
                beam_center_y - roi_size_y:beam_center_y + roi_size_y,
                beam_center_x - roi_size_x:beam_center_x + roi_size_x
                ]
            )
            i_roi_data = i_roi_data / expo_time

            with h5py.File(db_path) as h5obj:
                raw_db = extract_from_h5(h5obj, "ENTRY/DATA/I")
                beam_center_x_db = \
                    int(extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/beam_center_x"))
                beam_center_y_db = \
                    int(extract_from_h5(h5obj, "ENTRY/INSTRUMENT/DETECTOR/beam_center_y"))
                time_db = extract_from_h5(h5obj, "ENTRY/COLLECTION/exposition_time")

            i_roi_db = np.sum(
                raw_db[
                beam_center_y_db - roi_size_y:beam_center_y_db + roi_size_y,
                beam_center_x_db - roi_size_x:beam_center_x_db + roi_size_x
                ]
            )
            i_roi_db = i_roi_db / time_db

            transmission = i_roi_data / i_roi_db
            scaling_factor = 1 / (transmission * sample_thickness * i_roi_db * expo_time)

            # print(
            #     f"Absolute intensity parameters :\n"
            #     f"  - db path : {db_path}\n"
            #     f"  - I_ROI_DATA : {i_roi_data}\n"
            #     f"  - I_ROI_DB : {i_roi_db}\n"
            #     f"  - time : {expo_time}\n"
            #     f"  - time_db : {time_db}\n"
            #     f"  - transmission : {transmission}\n"
            #     f"  - SF : {scaling_factor}\n"
            # )

            abs_data = raw_data * scaling_factor

            if display:
                self._display_data(
                    index, nx_file,
                    group_name=group_name,
                    extracted_param_data=positions, extracted_value_data=abs_data,
                    scale_x="log", scale_y="log",
                    label_x="$q_{hor} (A^{-1})$",
                    label_y="$Intensity (m^{-1})$",
                    title="Absolute intensity of the data"
                )

            if save:
                q_list = positions
                i_list = abs_data
                mask = self.list_smi_data[index].masks
                save_data(nx_file, group_name, "Q", q_list, i_list, mask)

                create_process(
                    nx_file,
                    f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                    "Absolute Intensity",
                    "This process computes the absolute intensity of the data based on "
                    "direct beam data file\n"
                    "Parameters used :\n"
                    f"   - Path of the file : {db_path}"
                    f"   - Sample thickness : {sample_thickness:.4f}"
                    f"   - Region of interest size : ({roi_size_x:.2f}, {roi_size_y:.2f})"
                )

    def process_display(
            self,
            group_name: str = "DATA_Q_SPACE",
            scale_x: str = "log",
            scale_y: str = "log",
            label_x: str = "",
            label_y: str = "",
            title: str = "",
            xmin: None | float | int = None,
            xmax: None | float | int = None,
            ymin: None | float | int = None,
            ymax: None | float | int = None,
            optimize_range: bool = False,
            legend: bool = True,
            percentile: int | float = 99
    ) -> None:
        """
        Public method used to display data
       Parameters
        ----------
        legend :
            Choose whether you want to display the legend

        ymax :
            upper y range

        ymin :
            lower y range

        xmax :
            upper x range

        xmin :
            lower x range

        optimize_range :
            Bool to know if the range should be optimized for display

        percentile :
            Controls the intensity range. It will go from 0 to percentile / 100 * (max intensity)
            This parameter is only usefull for 2D plotting

        title :
            Title of the plot

        label_y :
            Title of the y axis

        label_x :
            Title of the x axis

        scale_y :
            Scale of the y axis "linear" or "log"

        scale_x :
            Scale of the x axis "linear" or "log"

        group_name:
            Name of the data group to be displayed
        """
        self.init_plot = True
        for index, nxfile in enumerate(self.nx_files):
            self._display_data(
                index=index, nxfile=nxfile,
                group_name=group_name,
                scale_x=scale_x, scale_y=scale_y,
                label_x=label_x, label_y=label_y,
                xmin=xmin, xmax=xmax,
                ymin=ymin, ymax=ymax,
                title=title, percentile=percentile,
                legend=legend, optimize_range=optimize_range
            )

    """
    Deprecated but could still be usefull
    
    def process_concatenate(
            self,
            group_names: None | list[str] = None
    ) -> None:
        for index, nxfile in enumerate(self.nx_files):
            q_list = []
            i_list = []
            for group in group_names:
                if f"ENTRY/{group}/I" not in nxfile:
                    raise Exception(f"There is no I data in {group} of file {self.file_paths[index]}")

                extracted_value_data = extract_from_h5(nxfile, f"ENTRY/{group}/I")

                if len(np.shape(extracted_value_data)) != 1:
                    raise Exception(f"I data in {group} of file {self.file_paths[index]} is not 1D")

                i_list = i_list + list(extracted_value_data)

                # We extract the parameter
                if f"ENTRY/{group}/Q" not in nxfile:
                    raise Exception(f"There is no Q data in {group} of file {self.file_paths[index]}")

                extracted_param_data = extract_from_h5(nxfile, f"ENTRY/{group}/Q")

                if len(np.shape(extracted_param_data)) != 1:
                    raise Exception(f"Q data in {group} of file {self.file_paths[index]} is not 1D")

                q_list = q_list + list(extracted_param_data)

            q_list = np.array(q_list)
            i_list = np.array(i_list)
            print(q_list)
            print(i_list)

            mask = self.list_smi_data[index].masks
            save_data(nxfile, "Q", q_list, "DATA_CONCAT", i_list, mask)

            create_process(self.nx_files[index],
                           f"/ENTRY/PROCESS_CONCAT",
                           "Data concatenation",
                           "Concatenates all the intensity and scattering vector selected"
                           )
    """

    def process_2_param_intensity(
            self,
            save: bool = False,
            display: bool = False,
            group_name: str = "DATA_RAD_AVG",
            other_variable: str = None,
            percentile: float | int = 95
    ):
        """
        TODO : complete docstring / allow plotting according to index as second parameter
        Parameters
        ----------
        percentile
        save
        display
        group_name
        other_variable

        Returns
        -------

        """
        # We extract the intensity and first parameter
        dict_param, dict_value = self.get_raw_data(group_name=group_name)
        for key, value in dict_value.items():
            if len(np.shape(value)) != 1:
                raise TypeError(f"Data in {group_name}, in file "
                                f"{key}, is not one dimensional")

        # We extract the second parameter
        dict_other_param = {}
        if other_variable == "Index":
            for index_file, h5obj in enumerate(self.nx_files):
                dict_other_param[Path(self.file_paths[index_file]).name] = \
                    index_file
        else:
            for index_file, h5obj in enumerate(self.nx_files):
                dict_other_param[Path(self.file_paths[index_file]).name] = \
                    extract_from_h5(h5obj, other_variable)

        # We check to see if the param have the same lengths
        common_len = 0
        for index, (key, value) in enumerate(dict_param.items()):
            if index == 0:
                common_len = len(value)
                continue
            if common_len != len(value):
                raise ValueError(f"the file {key} does not have the same amount of point in "
                                 f"it's intensity array as the other files ({common_len} points)")

        # We create the parameter meshes and the intensity array
        param_array = np.zeros((2, len(self.nx_files), common_len))
        value_array = np.zeros((len(self.nx_files), common_len))
        for index, (key, value) in enumerate(dict_other_param.items()):
            param_array[0, index, :] = dict_param[key]
            param_array[1, index, :] = value
            value_array[index, :] = dict_value[key]

        if display:
            self._display_data(
                extracted_param_data=param_array,
                extracted_value_data=value_array,
                percentile=percentile
            )

    def process_delete_data(
            self,
            group_name: str = "DATA_Q_SPACE"
    ) -> None:
        """
        Method used to delete a data group from all files

        Parameters
        ----------
        group_name:
            Data_group to delete
        """
        for nxfile in self.nx_files:
            delete_data(nxfile, group_name)

    def _detect_variables(self):
        """
        Process detecting all common variable between the
        opened files and returning only the ones that
        change in between those files.

        Returns
        -------
        Dictionary :
            - key : path of the variable in the HDF5 file
            - value : list of unique values (no duplicate)
        """
        dict_var = {}
        # We get all parameters' paths
        for nx_file in self.nx_files:
            base_path = "ENTRY/INSTRUMENT"
            paths = explore_file(
                nx_file[base_path],
                explore_group=True,
                explore_dataset=False,
                base_path=base_path
            )
            dict_var[nx_file] = paths

        for nx_file in self.nx_files:
            base_path = "ENTRY/COLLECTION"
            paths = explore_file(
                nx_file[base_path],
                explore_group=True,
                explore_dataset=False,
                base_path=base_path
            )
            dict_var[nx_file] = paths

        # We count the number of times each paths appear in all the list
        dict_count = {}
        for value in dict_var.values():
            for h5path in value:
                if h5path in dict_count.keys():
                    dict_count[h5path] += 1
                else:
                    dict_count[h5path] = 1

        # If the number of time the parameter appear is different
        # from the number of file we delete this parameter
        dict_valid_path = copy.deepcopy(dict_count)
        for path, count in dict_count.items():
            if count != len(self.nx_files) or isinstance(self.nx_files[0][path], h5py.Group):
                del dict_valid_path[path]

        # We get the parameter for each file
        dict_param_value = {}
        for path in dict_valid_path.keys():
            param_dict = {}
            for h5file in dict_var.keys():
                value = extract_from_h5(h5file, path)
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                filename = Path(h5file.filename).name
                param_dict[filename] = value
            if len(set(param_dict.values())) != 1:
                dict_param_value[path] = param_dict
        return dict_param_value

    def _display_data(
            self,
            index: None | int = None,
            nxfile: None | h5py.File = None,
            group_name: None | str = None,
            extracted_param_data: None | np.ndarray = None,
            extracted_value_data: None | np.ndarray = None,
            scale_x: str = "log",
            scale_y: str = "log",
            label_x: str = "",
            label_y: str = "",
            title: str = "",
            legend: bool = False,
            xmin: None | float | int = None,
            xmax: None | float | int = None,
            ymin: None | float | int = None,
            ymax: None | float | int = None,
            percentile: int | float = 99,
            optimize_range: bool = False
    ):
        """
        Displays the data contained in the DATA_... group

        Parameters
        ----------
        nxfile :
            File object

        index :
            Index of the file

        optimize_range :
            Bool to know if the range should be optimized for display

        extracted_param_data :
            Data on which extracted_value_data depends

        extracted_value_data :
            The value we want to display (Intensity mostly)

        percentile :
            Controls the intensity range. It will go from 0 to percentile / 100 * (max intensity)
            This parameter is only usefull for 2D plotting

        title :
            Title of the plot

        label_y :
            Title of the y axis

        label_x :
            Title of the x axis

        scale_y :
            Scale of the y axis "linear" or "log"

        scale_x :
            Scale of the x axis "linear" or "log"

        group_name:
            Name of the data group to be displayed
        """
        # We extract the intensity
        param_not_inserted = extracted_param_data is None
        value_not_inserted = extracted_param_data is None

        group_name_inserted = group_name is not None

        # We extract the data
        if value_not_inserted and group_name_inserted:
            extracted_value_data = extract_from_h5(nxfile, f"ENTRY/{group_name}/I")

        # We extract the parameter
        if param_not_inserted and group_name_inserted:
            if f"ENTRY/{group_name}/R" in nxfile:
                extracted_param_data = extract_from_h5(nxfile, f"ENTRY/{group_name}/R")
            elif f"ENTRY/{group_name}/Q" in nxfile:
                extracted_param_data = extract_from_h5(nxfile, f"ENTRY/{group_name}/Q")
            elif f"ENTRY/{group_name}/Chi" in nxfile:
                extracted_param_data = extract_from_h5(nxfile, f"ENTRY/{group_name}/Chi")
            else:
                extracted_param_data = None

        # If the intensity value is a scalar we print it
        if np.isscalar(extracted_value_data):
            print(extracted_value_data)

        # If the intensity value is a 1D array we plot it
        elif len(np.shape(extracted_value_data)) == 1:
            # Separation required because in the batch case we need to have the graphs
            # in the same figure
            if self.do_batch:
                if self.init_plot:
                    self.fig, self.ax = plt.subplots(figsize=(10, 6))
                    self.init_plot = False
            else:
                self.fig, self.ax = plt.subplots(figsize=(10, 6))
            self.ax.set_xscale(scale_x)
            self.ax.set_yscale(scale_y)

            self.ax.set_xlabel(label_x)
            self.ax.set_ylabel(label_y)
            self.ax.set_title(title)

            if xmin is not None and xmax is not None:
                self.ax.set_xlim(xmin, xmax)

            if ymin is not None and ymax is not None:
                self.ax.set_ylim(ymin, ymax)

            plot_color = PLT_CMAP_OBJ(index / len(self.nx_files))

            file_path = Path(self.file_paths[index])
            split_file_name = file_path.name.split("_")
            label = file_path.name.removesuffix(split_file_name[-1] + "_")

            first_index, last_index = 0, -1
            if optimize_range:
                indices_high_var = detect_variation(extracted_value_data, 0.8)
                print(indices_high_var)
                if len(indices_high_var) > 2:
                    first_index, last_index = indices_high_var[0], indices_high_var[-2]
                elif len(indices_high_var) == 2:
                    first_index, last_index = indices_high_var[0], indices_high_var[-1]
            self.ax.plot(
                extracted_param_data[first_index:last_index],
                extracted_value_data[first_index:last_index],
                label=f"{label}",
                color=plot_color
            )

            if self.do_batch:
                if index == len(self.nx_files) - 1:
                    if legend:
                        self.ax.legend()
                    plt.show(block=False)
            else:
                if legend:
                    self.ax.legend()
                plt.show(block=False)
                time.sleep(0.5)

        # If the intensity value is a 2D array we imshow it
        elif len(np.shape(extracted_value_data)) == 2:
            if self.do_batch:
                file_number = len(self.nx_files)
                dims = int(np.ceil(np.sqrt(file_number)))
                if self.init_plot:
                    self.fig, self.ax = plt.subplots(dims, dims, layout="constrained")
                    self.init_plot = False

                if dims != 1 and index is not None:
                    current_ax = self.ax[int(index // dims), int(index % dims)]
                else:
                    current_ax = self.ax
            else:
                _, ax = plt.subplots(layout="constrained")
                current_ax = ax

            print(label_x)
            current_ax.set_xlabel(label_x)
            current_ax.set_ylabel(label_y)
            current_ax.set_title(title)

            cplot = current_ax.pcolormesh(
                extracted_param_data[0, ...],
                extracted_param_data[1, ...],
                extracted_value_data,
                vmin=0,
                vmax=np.percentile(
                    extracted_value_data[~np.isnan(extracted_value_data)],
                    percentile),
                cmap=PLT_CMAP
            )
            cbar = plt.colorbar(cplot, ax=current_ax)
            cbar.set_label("Intensity")

            if self.do_batch:
                if index == len(self.nx_files) - 1:
                    plt.show(block=False)
            else:
                plt.show(block=False)
                time.sleep(0.1)

    def nexus_close(self):
        """
        Method used to close the loaded file correctly by repacking it and then closing it
        """
        for index, file_obj in enumerate(self.nx_files):
            file_obj.close()
            repack_hdf5(self.file_paths[index], str(self.file_paths[index]) + ".tmp")


if __name__ == "__main__":
    # profiler = cProfile.Profile()
    # profiler.enable()

    data_path = r"C:\Users\AT280565\Desktop\Data Treatment Center\Treated Data\instrument - " \
                r"XEUSS\250429_Al_test\250429_Al_run02\format - " \
                r"NX\Eprouvette_AluMg_run02_img00001-00002_20250512125323.h5"

    with h5py.File(data_path) as file:
        data1 = file["ENTRY/DATA/I"][:]

    plt.figure()
    plt.imshow(
        data1,
        vmin=0,
        vmax=np.percentile(
            data1[~np.isnan(data1)],
            99),
        cmap=PLT_CMAP
    )
    cbar = plt.colorbar()
    cbar.set_label("Intensity")
    plt.xlabel("$p_x$ (pixel)")
    plt.ylabel("$p_y$ (pixel)")
    plt.title("Raw Data")
    plt.show()

    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('tottime')
    # stats.print_stats()
