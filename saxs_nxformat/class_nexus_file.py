"""
The main feature of this module is the NexusFile class which is used
to treat raw data contained in a .h5 file formated according
to the NXcanSAS standard
"""
import os
import shutil
import re

import h5py
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from saxs_nxformat import PLT_CMAP
from smi_analysis import SMI_beamline


def repack_hdf5(input_file, output_file):
    """
    Repack an HDF5 file to reduce its size by copying its content to a new file.

    Parameters
    ----------
    input_file : str
        Path to the input HDF5 file.
    output_file : str
        Path to the output (repacked) HDF5 file.
    """
    with h5py.File(input_file, 'r') as src, h5py.File(output_file, 'w') as dest:
        src.copy("/ENTRY", dest)


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


def create_process(hdf5_file, group_h5path, process_name, process_desc):
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


def extract_from_h5(nx_file, h5path, data_type="dataset", attribute_name=None):
    """
    Method used to extract a dataset or attribute from the .h5 file

    Parameters
    ----------
    nx_file :
        file object

    h5path :
        h5 path of the dataset

    data_type :
        type of the value extracted (attribute or dataset)

    attribute_name :
        if it's an attribute, give its name

    Returns
    -------
    Either the attribute or dataset selected

    """
    # We get the dataset and its attributes
    dataset = nx_file[h5path]
    attributes = dataset.attrs

    # We detect if the dataset is a scalar, an array or an attribute
    if data_type == "dataset" and np.shape(dataset) == ():
        return dataset[()]
    elif data_type == "dataset" and np.shape(dataset) != ():
        return dataset[:]
    elif data_type == "attribute" and attribute_name in attributes.keys():
        return attributes[attribute_name]
    else:
        print(f"error while extracting from {h5path}")
        return None


def save_data(nx_file, parameter_symbol, parameter, dataset_name, dataset):
    """
    Method used to save a dataset in the h5 file

    Parameters
    ----------
    parameter_symbol :
        Symbol of the parameter. will be the name of its dataset

    parameter :
        Contains the parameter data

    dataset_name :
        Name of the group containing all the data

    dataset :
        Contains the data
    """
    # We create the dataset h5path and if it exists we delete what was previously there
    dataset_name = dataset_name.upper()
    dataset_path = f"/ENTRY/{dataset_name}"
    if dataset_path in nx_file:
        del nx_file[dataset_path]

    # we copy the raw data and set the copied data to the name selected
    # That way we also copy the attributes
    nx_file.copy("ENTRY/DATA", nx_file["/ENTRY"], dataset_name)

    # we replace the raw data with the new data
    replace_h5_dataset(nx_file, f"{dataset_path}/R",
                       parameter, f"{dataset_path}/{parameter_symbol}")
    replace_h5_dataset(nx_file, f"{dataset_path}/I",
                       dataset)


def delete_data(nx_file, group_name):
    """
    Method used to properly delete data from the h5 file

    Parameters
    ----------
    group_name :
        Name of the data group to delete
    """
    group_name = group_name.upper()
    if group_name in nx_file:
        del file[f"/ENTRY/{group_name}"]
    else:
        print("This group does not exists")


class NexusFile:
    """
    A class that can load and treat data formated in the NXcanSAS standard
    TODO : manage data stitching, ask for example files

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

    intensities_data :
        list of array of intensities
    """

    def __init__(self, h5_paths, do_batch):
        """
        The init of this class consists of extracting every releavant parameters
        from the h5 file and using it to open the data and stitch it using the SMI_package

        Parameters
        ----------
        h5_paths
            The path of the h5 files we want to open passed as a list of strings

        do_batch :
            Determines wether the data is assembled in a new file or not and whether it is
            displayed a single figure or not
        """
        self.file_paths = h5_paths
        if "selected" in do_batch:
            self.do_batch = True
        else:
            self.do_batch = False

        self.nx_files = []
        self.dicts_parameters = []
        self.list_smi_data = []
        self.intensities_data = []

        for index, file_path in enumerate(self.file_paths):
            nx_file = h5py.File(file_path, "r+")

            dict_parameters = {
                "beam stop": [[0, 0]]
            }

            # We extract the relevant info from the H5 file
            intensity_data = [nx_file["ENTRY/DATA/I"][:]]
            position_data = [nx_file["ENTRY/DATA/R"][:]]
            dict_parameters["I raw data"] = intensity_data
            dict_parameters["R raw data"] = position_data

            # Concerning the source
            wavelength = extract_from_h5(nx_file, "ENTRY/INSTRUMENT/SOURCE/incident_wavelength")
            dict_parameters["wavelength"] = wavelength * 1e-9

            # Concerning the sample
            incident_angle = extract_from_h5(nx_file, "ENTRY/SAMPLE/yaw")
            dict_parameters["incident angle"] = incident_angle

            # Concerning the detector
            # We use a regex that detects the keyword required in the detector's name
            detector_name = extract_from_h5(nx_file, "/ENTRY/INSTRUMENT/DETECTOR/name").decode("utf-8")
            if re.search(
                    "(?i)(?=.*dectris)" +
                    "(?i)(?=.*eiger2)" +
                    "(?i)(?=.*1m)",
                    detector_name.lower()
            ):
                dict_parameters["detector name"] = "Eiger1M_xeuss"
            if re.search(
                    "(?i)(?=.*" + "dectris" + ")" +
                    "(?i)(?=.*" + "eiger2" + ")" +
                    "(?i)(?=.*" + "500k" + ")",
                    detector_name.lower()
            ):
                dict_parameters["detector name"] = "Eiger500k_xeuss"

            # Concerning the beamcenter
            beam_center_x = extract_from_h5(nx_file, "ENTRY/INSTRUMENT/DETECTOR/beam_center_x")
            beam_center_y = extract_from_h5(nx_file, "ENTRY/INSTRUMENT/DETECTOR/beam_center_y")
            dict_parameters["beam center"] = [beam_center_x, beam_center_y]

            # Concerning the rotations of the detector
            rotation_1 = - extract_from_h5(nx_file, "ENTRY/INSTRUMENT/DETECTOR/yaw")
            rotation_2 = extract_from_h5(nx_file, "ENTRY/INSTRUMENT/DETECTOR/pitch")
            rotation_3 = - extract_from_h5(nx_file, "ENTRY/INSTRUMENT/DETECTOR/roll")
            dict_parameters["detector rotation"] = [[rotation_1, rotation_2, rotation_3]]

            # Concerning the sample-detector distance
            sample_detector_distance = extract_from_h5(nx_file, "ENTRY/INSTRUMENT/DETECTOR/SDD")
            dict_parameters["distance"] = sample_detector_distance * 1e3

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

            self.nx_files.append(nx_file)
            self.dicts_parameters.append(dict_parameters)
            self.intensities_data.append(intensity_data)
            self.list_smi_data.append(smi_data)

    def get_file(self):
        """
        Getter of the actual h5 files
        """
        return self.nx_files

    def process_q_space(
            self, display=False, save=False, group_name="DATA_Q_SPACE"
    ):
        """
        Method used to put the data in Q space (Fourier space). This will save an array
        containing the intensity values and another array containing the vector Q associated
        to each intensities

        Parameters
        ----------
        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        plot_count = 0
        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = np.logical_not(np.ones(np.shape(smi_data.imgs)))
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            if display:
                if self.do_batch:
                    if plot_count == 0:
                        file_number = len(self.nx_files)
                        dims = int(np.ceil(np.sqrt(file_number)))
                        fig, ax = plt.subplots(dims, dims, layout="constrained")
                    current_ax = ax[int(plot_count // dims), int(plot_count % dims)]
                else:
                    fig, ax = plt.subplots(layout="constrained")
                    current_ax = ax
                current_ax.set_title('2D Data in q-space')
                current_ax.set_xlabel('$q_{x} (A^{-1}$)')
                current_ax.set_ylabel('$q_{y} (A^{-1}$)')
                cplot = current_ax.imshow(
                    smi_data.img_st,
                    extent=[smi_data.qp[0], smi_data.qp[-1],
                            smi_data.qz[0], smi_data.qz[-1]],
                    vmin=0,
                    vmax=np.percentile(
                        smi_data.img_st[~np.isnan(smi_data.img_st)],
                        99),
                    cmap=PLT_CMAP
                )
                cbar = plt.colorbar(cplot, ax=current_ax)
                cbar.set_label("Intensity")
                plot_count += 1

                if self.do_batch:
                    if plot_count == len(self.nx_files):
                        plt.show()
                else:
                    plt.show()

            # Saving the data and the process it just went trough
            if save:
                dim = np.shape(self.dicts_parameters[index]["R raw data"][0])
                qx_list = np.linspace(smi_data.qp[0], smi_data.qp[-1], dim[1])
                qy_list = np.linspace(smi_data.qz[-1], smi_data.qz[0], dim[0])
                qx_grid, qy_grid = np.meshgrid(qx_list, qy_list)
                mesh_q = np.stack((qx_grid, qy_grid), axis=-1)

                save_data(self.nx_files[index], "Q", mesh_q, group_name, smi_data.img_st)

                create_process(self.nx_files[index],
                               f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                               "Conversion to q-space",
                               "This process converts the 2D array Q containing the position in A into a 2D "
                               "array containing the positions in q-space, A^-1. "
                               "Each element of the array Q is a vector containing qx and qy"
                               )

    def process_caking(
            self, display=False, save=False, group_name="DATA_CAKED",
            azi_min=None, azi_max=None, pts_azi=None,
            radial_min=None, radial_max=None, pts_rad=None
    ):
        """
        Method used to cake the data. This will display the data in the (q_r, chi) coordinate system.

        Parameters
        ----------
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
        plot_count = 0
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
            azi_min = azi_min if azi_min is not None else defaults["azi_min"]
            azi_max = azi_max if azi_max is not None else defaults["azi_max"]
            radial_min = radial_min if radial_min is not None else defaults["radial_min"]
            radial_max = radial_max if radial_max is not None else defaults["radial_max"]
            pts_azi = pts_azi if pts_azi is not None else defaults["pts_azi"]
            pts_rad = pts_rad if pts_rad is not None else defaults["pts_rad"]

            smi_data.caking(
                azimuth_range=[azi_min, azi_max],
                radial_range=[radial_min, radial_max],
                npt_azim=pts_azi,
                npt_rad=pts_rad
            )

            if display:
                if self.do_batch:
                    if plot_count == 0:
                        file_number = len(self.nx_files)
                        dims = int(np.ceil(np.sqrt(file_number)))
                        fig, ax = plt.subplots(dims, dims, layout="constrained")
                    current_ax = ax[int(plot_count // dims), int(plot_count % dims)]
                else:
                    fig, ax = plt.subplots(layout="constrained")
                    current_ax = ax
                current_ax.set_title('Caked q-space data')
                current_ax.set_xlabel('$q (A^{-1}$)')
                current_ax.set_ylabel('$\\chi$')
                cplot = current_ax.pcolormesh(
                    smi_data.q_cake,
                    smi_data.chi_cake,
                    smi_data.cake,
                    cmap=PLT_CMAP, shading='auto',
                    vmin=0,
                    vmax=np.percentile(
                        smi_data.cake[~np.isnan(smi_data.cake)],
                        99.8),
                )
                cbar = plt.colorbar(cplot, ax=current_ax)
                cbar.set_label("Intensity")
                plot_count += 1
                if self.do_batch:
                    if plot_count == len(self.nx_files):
                        plt.show()
                else:
                    plt.show()

            if save:
                q_list = smi_data.q_cake
                chi_list = smi_data.chi_cake
                q_grid, chi_grid = np.meshgrid(q_list, chi_list)
                mesh_cake = np.stack((q_grid, chi_grid), axis=-1)

                save_data(self.nx_files[index], "Q", mesh_cake, group_name, smi_data.cake)

                create_process(self.nx_files[index],
                               f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                               "Data caking",
                               "This process plots the intensity with respect to the azimuthal angle and the distance "
                               "from"
                               "the center of the q-space. That way the rings are flattened."
                               )

    def process_radial_average(
            self, display=False, save=False, group_name="DATA_RAD_AVG",
            r_min=None, r_max=None,
            angle_min=None, angle_max=None,
            pts=None
    ):
        """
        Method used to perform radial averaging of data in Fourier space. This will reduce the signal to
        one dimension : intensity versus distance from the center

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
        plot_count = 0
        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = np.logical_not(np.ones(np.shape(smi_data.imgs)))
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            defaults = {
                "r_max": np.sqrt(max(smi_data.qp) ** 2 + max(smi_data.qz) ** 2),
                "r_min": 0,
                "angle_min": -180,
                "angle_max": 180,
                "pts": 2000
            }

            r_min = r_min if r_min is not None else defaults["r_min"]
            r_max = r_max if r_max is not None else defaults["r_max"]
            angle_min = angle_min if angle_min is not None else defaults["angle_min"]
            angle_max = angle_max if angle_max is not None else defaults["angle_max"]
            pts = pts if pts is not None else defaults["pts"]

            smi_data.radial_averaging(
                azimuth_range=[angle_min, angle_max],
                npt=pts,
                radial_range=[r_min, r_max]
            )

            if display:
                if self.do_batch:
                    if plot_count == 0:
                        _, ax = plt.subplots(figsize=(10, 6))
                else:
                    _, ax = plt.subplots(figsize=(10, 6))
                ax.set_title('Radial average of data in q-space')
                ax.set_xlabel('$q_r (A^{-1}$)')
                ax.set_ylabel('I (A.u.)')
                file_path = Path(self.file_paths[index])
                file_name = file_path.name
                ax.loglog(smi_data.q_rad, smi_data.I_rad, label=f"{file_name}")
                plot_count += 1

                if self.do_batch:
                    if plot_count == len(self.nx_files):
                        ax.legend()
                        plt.show()
                else:
                    ax.legend()
                    plt.show()

            if save:
                q_list = smi_data.q_rad
                i_list = smi_data.I_rad
                save_data(self.nx_files[index], "Q", q_list, group_name, i_list)

                create_process(self.nx_files[index],
                               f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                               "Radial averaging",
                               "This process integrates the intensity signal over a specified radial angle range"
                               " and q range, effectively rendering the signal 1D instead of 2D"
                               )

    def process_azimuthal_average(
            self, display=False, save=False, group_name="DATA_AZI_AVG",
            r_min=None, r_max=None,
            angle_min=None, angle_max=None,
    ):
        """
        Method used to do the radial average of the data in fourier space

        Parameters
        ----------
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
        plot_count = 0
        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = np.logical_not(np.ones(np.shape(smi_data.imgs)))
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            defaults = {
                "r_max": np.sqrt(max(smi_data.qp) ** 2 + max(smi_data.qz) ** 2),
                "r_min": 0,
                "angle_min": -180,
                "angle_max": 180,
            }

            r_min = r_min if r_min is not None else defaults["r_min"]
            r_max = r_max if r_max is not None else defaults["r_max"]
            angle_min = angle_min if angle_min is not None else defaults["angle_min"]
            angle_max = angle_max if angle_max is not None else defaults["angle_max"]

            smi_data.azimuthal_averaging(
                azimuth_range=[angle_min, angle_max],
                radial_range=[r_min, r_max]
            )

            if display:
                if self.do_batch:
                    if plot_count == 0:
                        _, ax = plt.subplots(figsize=(10, 6))
                else:
                    _, ax = plt.subplots(figsize=(10, 6))
                ax.set_title('Azimuthal average of data in q-space')
                ax.set_xlabel('$\\chi$')
                ax.set_ylabel('I (A.u.)')
                file_path = Path(self.file_paths[index])
                file_name = file_path.name
                ax.loglog(smi_data.chi_azi, smi_data.I_azi, label=f"{file_name}")
                plot_count += 1

                if self.do_batch:
                    if plot_count == len(self.nx_files):
                        ax.legend()
                        plt.show()
                else:
                    ax.legend()
                    plt.show()

            if save:
                chi_list = smi_data.chi_azi
                i_list = smi_data.I_azi
                save_data(self.nx_files[index], "Chi", chi_list, group_name, i_list)
                create_process(self.nx_files[index],
                               f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                               "Azimuthal averaging",
                               "This process integrates the intensity signal over a specified azimuthal angle range"
                               " and q range, effectively rendering the signal 1D instead of 2D"
                               )

    def process_horizontal_integration(
            self, display=False, save=False, group_name="DATA_HOR_INT",
            qx_min=None, qx_max=None,
            qy_min=None, qy_max=None
    ):
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
        plot_count = 0

        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = np.logical_not(np.ones(np.shape(smi_data.imgs)))
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            defaults = {
                "qx_min": smi_data.qp[0],
                "qx_max": smi_data.qp[-1],
                "qy_min": smi_data.qz[0],
                "qy_max": smi_data.qz[-1]
            }

            qx_min = qx_min if qx_min is not None else defaults["qx_min"]
            qx_max = qx_max if qx_max is not None else defaults["qx_max"]
            qy_min = qy_min if qy_min is not None else defaults["qy_min"]
            qy_max = qy_max if qy_max is not None else defaults["qy_max"]

            smi_data.horizontal_integration(
                q_per_range=[qy_min, qy_max],
                q_par_range=[qx_min, qx_max]
            )

            if display:
                if self.do_batch:
                    if plot_count == 0:
                        _, ax = plt.subplots(figsize=(10, 6))
                else:
                    _, ax = plt.subplots(figsize=(10, 6))
                ax.set_title('Horizontal integration of data in q-space')
                ax.set_xlabel('$q_{x} (A^{-1}$)')
                ax.set_ylabel('I (A.u.)')
                file_path = Path(self.file_paths[index])
                file_name = file_path.name
                ax.plot(smi_data.q_hor, smi_data.I_hor, label=f"{file_name}")
                plot_count += 1

                if self.do_batch:
                    if plot_count == len(self.nx_files):
                        ax.legend()
                        plt.show()
                else:
                    ax.legend()
                    plt.show()

            if save:
                q_list = smi_data.q_hor
                i_list = smi_data.I_hor
                save_data(self.nx_files[index], "Q", q_list, group_name, i_list)

                create_process(self.nx_files[index],
                               f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                               "Horizontal integration",
                               "This process integrates the intensity signal over a specified horizontal strip in "
                               "q-space"
                               "effectively rendering the signal 1D instead of 2D"
                               )

    def process_vertical_integration(
            self, display=False, save=False, group_name="DATA_HOR_INT",
            qx_min=None, qx_max=None,
            qy_min=None, qy_max=None
    ):
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
        plot_count = 0
        for index, smi_data in enumerate(self.list_smi_data):
            smi_data.masks = np.logical_not(np.ones(np.shape(smi_data.imgs)))
            smi_data.calculate_integrator_trans(self.dicts_parameters[index]["detector rotation"])

            defaults = {
                "qx_min": smi_data.qp[0],
                "qx_max": smi_data.qp[-1],
                "qy_min": smi_data.qz[0],
                "qy_max": smi_data.qz[-1]
            }

            qx_min = qx_min if qx_min is not None else defaults["qx_min"]
            qx_max = qx_max if qx_max is not None else defaults["qx_max"]
            qy_min = qy_min if qy_min is not None else defaults["qy_min"]
            qy_max = qy_max if qy_max is not None else defaults["qy_max"]

            smi_data.vertical_integration(
                q_per_range=[qy_min, qy_max],
                q_par_range=[qx_min, qx_max]
            )

            if display:
                if self.do_batch:
                    if plot_count == 0:
                        _, ax = plt.subplots(figsize=(10, 6))
                else:
                    _, ax = plt.subplots(figsize=(10, 6))
                    ax.set_title('Horizontal integration of data in q-space')
                    ax.set_xlabel('$q_{y} (A^{-1}$)')
                    ax.set_ylabel('I (A.u.)')
                file_path = Path(self.file_paths[index])
                file_name = file_path.name
                ax.plot(smi_data.q_ver, smi_data.I_ver, label=f"{file_name}")
                plot_count += 1

                if self.do_batch:
                    if plot_count == len(self.nx_files):
                        ax.legend()
                        plt.show()
                else:
                    ax.legend()
                    plt.show()

            if save:
                q_list = smi_data.q_ver
                i_list = smi_data.I_ver
                save_data(self.nx_files[index], "Q", q_list, group_name, i_list)

                create_process(self.nx_files[index],
                               f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                               "Vertical integration",
                               "This process integrates the intensity signal over a specified vertical strip in q-space"
                               "effectively rendering the signal 1D instead of 2D"
                               )

    def process_display(self, group_name="DATA_Q_SPACE"):
        """
        TODO : Will display the selected data_group
        """

    def close(self):
        """
        Method used to close the loaded file correctly by repacking it and then closing it
        """
        for index, file in enumerate(self.nx_files):
            file.close()
            repack_hdf5(self.file_paths[index], self.file_paths[index] + ".tmp")
            os.remove(self.file_paths[index])
            shutil.move(self.file_paths[index] + ".tmp", self.file_paths[index])


if __name__ == "__main__":
    FILE_NAME = "/edf2NxSAS/treated data/instrument - Xeuss/config - 2024-12-19T15-00/sample - SafeLiMove/experiment " \
                "- WAXS1/format - NXsas/defaultSampleName_SAXS_2025-02-19T10-36-52.h5"

    nx_file = NexusFile(FILE_NAME)
    nx_file.process_q_space(display=True, save=True)
    nx_file.process_caking(display=True, save=True)
    nx_file.process_radial_average(display=True, save=True)
    nx_file.process_azimuthal_average(display=True, save=True)
    nx_file.process_vertical_integration(display=True, save=True)

    nx_file.close()
