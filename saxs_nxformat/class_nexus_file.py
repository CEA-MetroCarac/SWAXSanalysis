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


class NexusFile:
    """
    A class that can load and treat data formated in the NXcanSAS standard

    Attributes
    ----------
    file_path :
        path of the treated file

    file :
        loaded file

    dict_parameters :
        dictionary of all releavant parameters

    smi_data :
        Stitched data using the SMI package
    """

    def __init__(self, h5_path):
        """
        The init of this class consists of extracting every releavant parameters
        from the h5 file and using it to open the data and stitch it using the SMI_package

        Parameters
        ----------
        h5_path
            The path of the h5 file we want to open
        """
        self.file_path = h5_path
        self.file = h5py.File(h5_path, "r+")

        self.dict_parameters = {
            "beam stop": [[0, 0]]
        }

        # We extract the relevant info from the H5 file
        self.intensity_data = [self.file["ENTRY/DATA/I"][:]]
        self.position_data = [self.file["ENTRY/DATA/R"][:]]
        self.dict_parameters["I raw data"] = self.intensity_data
        self.dict_parameters["R raw data"] = self.position_data

        # Concerning the source
        wavelength = self.extract_from_h5("ENTRY/INSTRUMENT/SOURCE/incident_wavelength")
        self.dict_parameters["wavelength"] = wavelength * 1e-9

        # Concerning the sample
        incident_angle = self.extract_from_h5("ENTRY/SAMPLE/yaw")
        self.dict_parameters["incident angle"] = incident_angle

        # Concerning the detector
        # We use a regex that detects the keyword required in the detector's name
        detector_name = self.extract_from_h5("/ENTRY/INSTRUMENT/DETECTOR/name").decode("utf-8")
        if re.search(
                "(?i)(?=.*dectris)" +
                "(?i)(?=.*eiger2)" +
                "(?i)(?=.*1m)",
                detector_name.lower()
        ):
            self.dict_parameters["detector name"] = "Eiger1M_xeuss"
        if re.search(
                "(?i)(?=.*" + "dectris" + ")" +
                "(?i)(?=.*" + "eiger2" + ")" +
                "(?i)(?=.*" + "500k" + ")",
                detector_name.lower()
        ):
            self.dict_parameters["detector name"] = "Eiger500k_xeuss"

        # Concerning the beamcenter
        beam_center_x = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/beam_center_x")
        beam_center_y = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/beam_center_y")
        self.dict_parameters["beam center"] = [beam_center_x, beam_center_y]

        # Concerning the rotations of the detector
        rotation_1 = -self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/yaw")
        rotation_2 = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/pitch")
        rotation_3 = -self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/roll")
        self.dict_parameters["detector rotation"] = [[rotation_1, rotation_2, rotation_3]]

        # Concerning the sample-detector distance
        sample_detector_distance = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/SDD")
        self.dict_parameters["distance"] = sample_detector_distance * 1e3

        # We input the info in the SMI package
        # TODO : change the dict keys to the param names and uses dict** to pass the parameters
        # TODO : See example in data_processing func _start_processing()
        self.smi_data = SMI_beamline.SMI_geometry(
            geometry="Transmission",
            sdd=self.dict_parameters["distance"],
            wav=self.dict_parameters["wavelength"],
            alphai=self.dict_parameters["incident angle"],
            center=self.dict_parameters["beam center"],
            bs_pos=self.dict_parameters["beam stop"],
            detector=self.dict_parameters["detector name"],
            det_angles=self.dict_parameters["detector rotation"]
        )
        self.smi_data.open_data_db(self.dict_parameters["I raw data"])
        self.smi_data.stitching_data()

    def get_file(self):
        """
        Getter of the actual h5 file
        """
        return self.file

    def extract_from_h5(self, h5path, data_type="dataset", attribute_name=None):
        """
        Method used to extract a dataset or attribute from the .h5 file

        Parameters
        ----------
        h5path :
            path of the dataset

        data_type :
            type of the value extracted (attribute or dataset)

        attribute_name :
            if it's an attribute, give its name

        Returns
        -------
        Either the attribute or dataset selected

        """
        # We get the dataset and its attributes
        dataset = self.file[h5path]
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
        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        if display:
            # Displaying the data after it's been processed
            _, ax = plt.subplots(layout="constrained")
            ax.set_title('2D Data in q-space')
            cplot = ax.imshow(self.smi_data.img_st,
                              extent=[self.smi_data.qp[0], self.smi_data.qp[-1],
                                      self.smi_data.qz[0], self.smi_data.qz[-1]],
                              vmin=0,
                              vmax=np.percentile(
                                  self.smi_data.img_st[~np.isnan(self.smi_data.img_st)],
                                  99),
                              cmap="magma")
            ax.set_xlabel('$q_{x} (A^{-1}$)')
            ax.set_ylabel('$q_{y} (A^{-1}$)')
            cbar = plt.colorbar(cplot, ax=ax)
            cbar.set_label("Intensity")
            plt.show()

        # Saving the data and the process it just went trough
        if save:
            dim = np.shape(self.dict_parameters["R raw data"][0])
            qx_list = np.linspace(self.smi_data.qp[0], self.smi_data.qp[-1], dim[1])
            qy_list = np.linspace(self.smi_data.qz[-1], self.smi_data.qz[0], dim[0])
            qx_grid, qy_grid = np.meshgrid(qx_list, qy_list)
            mesh_q = np.stack((qx_grid, qy_grid), axis=-1)

            self.save_data("Q", mesh_q, group_name, self.smi_data.img_st)

            create_process(self.file,
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
        defaults = {
            "azi_min": -180,
            "azi_max": 180,
            "radial_min": min(self.smi_data.qz),
            "radial_max": max(self.smi_data.qz),
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

        self.smi_data.caking(
            azimuth_range=[azi_min, azi_max],
            radial_range=[radial_min, radial_max],
            npt_azim=pts_azi,
            npt_rad=pts_rad
        )

        if display:
            _, ax = plt.subplots(figsize=(10, 6))
            ax.set_title('Caked q-space data')
            cplot = ax.pcolormesh(self.smi_data.q_cake,
                                  self.smi_data.chi_cake,
                                  self.smi_data.cake,
                                  cmap="magma", shading='auto',
                                  vmin=0,
                                  vmax=np.percentile(
                                      self.smi_data.cake[~np.isnan(self.smi_data.cake)],
                                      99.8), )
            ax.set_xlabel('$q (A^{-1}$)')
            ax.set_ylabel('$\\chi (A^{-1}$)')
            cbar = plt.colorbar(cplot, ax=ax)
            cbar.set_label("Intensity")
            plt.show()

        if save:
            q_list = self.smi_data.q_cake
            chi_list = self.smi_data.chi_cake
            q_grid, chi_grid = np.meshgrid(q_list, chi_list)
            mesh_cake = np.stack((q_grid, chi_grid), axis=-1)

            self.save_data("Q", mesh_cake, group_name, self.smi_data.cake)

            create_process(self.file,
                           f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                           "Data caking",
                           "This process plots the intensity with respect to the azimuthal angle and the distance from"
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

        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        defaults = {
            "r_max": np.sqrt(max(self.smi_data.qp) ** 2 + max(self.smi_data.qz) ** 2),
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

        self.smi_data.radial_averaging(
            azimuth_range=[angle_min, angle_max],
            npt=pts,
            radial_range=[r_min, r_max]
        )

        if display:
            _, ax = plt.subplots(figsize=(10, 6))
            ax.set_title('Radial average of data in q-space')
            ax.plot(self.smi_data.q_rad, self.smi_data.I_rad)
            ax.set_xlabel('$q_r (A^{-1}$)')
            ax.set_ylabel('I (A.u.)')
            plt.show()

        if save:
            q_list = self.smi_data.q_rad
            i_list = self.smi_data.I_rad
            self.save_data("Q", q_list, group_name, i_list)

            create_process(self.file,
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
        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        defaults = {
            "r_max": np.sqrt(max(self.smi_data.qp) ** 2 + max(self.smi_data.qz) ** 2),
            "r_min": 0,
            "angle_min": -180,
            "angle_max": 180,
        }

        r_min = r_min if r_min is not None else defaults["r_min"]
        r_max = r_max if r_max is not None else defaults["r_max"]
        angle_min = angle_min if angle_min is not None else defaults["angle_min"]
        angle_max = angle_max if angle_max is not None else defaults["angle_max"]

        self.smi_data.azimuthal_averaging(
            azimuth_range=[angle_min, angle_max],
            radial_range=[r_min, r_max]
        )

        if display:
            _, ax = plt.subplots(figsize=(10, 6))
            ax.set_title('Azimuthal average of data in q-space')
            ax.plot(self.smi_data.chi_azi, self.smi_data.I_azi)
            ax.set_xlabel('$\\chi$')
            ax.set_ylabel('I (A.u.)')
            plt.show()

        if save:
            chi_list = self.smi_data.chi_azi
            i_list = self.smi_data.I_azi
            self.save_data("Chi", chi_list, group_name, i_list)
            create_process(self.file,
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

        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        defaults = {
            "qx_min": self.smi_data.qp[0],
            "qx_max": self.smi_data.qp[-1],
            "qy_min": self.smi_data.qz[0],
            "qy_max": self.smi_data.qz[-1]
        }

        qx_min = qx_min if qx_min is not None else defaults["qx_min"]
        qx_max = qx_max if qx_max is not None else defaults["qx_max"]
        qy_min = qy_min if qy_min is not None else defaults["qy_min"]
        qy_max = qy_max if qy_max is not None else defaults["qy_max"]

        self.smi_data.horizontal_integration(
            q_per_range=[qy_min, qy_max],
            q_par_range=[qx_min, qx_max]
        )

        if display:
            _, ax = plt.subplots(figsize=(10, 6))
            ax.set_title('Horizontal integration of data in q-space')
            ax.plot(self.smi_data.q_hor, self.smi_data.I_hor)
            ax.set_xlabel('$q_{x} (A^{-1}$)')
            ax.set_ylabel('I (A.u.)')
            plt.show()

        if save:
            q_list = self.smi_data.q_hor
            i_list = self.smi_data.I_hor
            self.save_data("Q", q_list, group_name, i_list)

            create_process(self.file,
                           f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                           "Horizontal integration",
                           "This process integrates the intensity signal over a specified horizontal strip in q-space"
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
        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        defaults = {
            "qx_min": self.smi_data.qp[0],
            "qx_max": self.smi_data.qp[-1],
            "qy_min": self.smi_data.qz[0],
            "qy_max": self.smi_data.qz[-1]
        }

        qx_min = qx_min if qx_min is not None else defaults["qx_min"]
        qx_max = qx_max if qx_max is not None else defaults["qx_max"]
        qy_min = qy_min if qy_min is not None else defaults["qy_min"]
        qy_max = qy_max if qy_max is not None else defaults["qy_max"]

        self.smi_data.horizontal_integration(
            q_per_range=[qy_min, qy_max],
            q_par_range=[qx_min, qx_max]
        )

        self.smi_data.vertical_integration(q_per_range=qy_range, q_par_range=qx_range)

        if display:
            _, ax = plt.subplots(figsize=(10, 6))
            ax.set_title('Horizontal integration of data in q-space')
            ax.plot(self.smi_data.q_ver, self.smi_data.I_ver)
            ax.set_xlabel('$q_{y} (A^{-1}$)')
            ax.set_ylabel('I (A.u.)')
            plt.show()

        if save:
            q_list = self.smi_data.q_ver
            i_list = self.smi_data.I_ver
            self.save_data("Q", q_list, group_name, i_list)

            create_process(self.file,
                           f"/ENTRY/PROCESS_{group_name.removeprefix('DATA_')}",
                           "Vertical integration",
                           "This process integrates the intensity signal over a specified vertical strip in q-space"
                           "effectively rendering the signal 1D instead of 2D"
                           )

    def process_display(self, group_name="DATA_Q_SPACE"):
        """
        TODO : Will display the selected data_group
        """

    def save_data(self, parameter_symbol, parameter, dataset_name, dataset):
        """
        TODO : replace the fact we do both positions and intensity at the same time
        TODo : instead do one at a time this will allow uncertainties and such
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
        if dataset_path in self.file:
            del self.file[dataset_path]

        # we copy the raw data and set the copied data to the name selected
        # That way we also copy the attributes
        self.file.copy("ENTRY/DATA", self.file["/ENTRY"], dataset_name)

        # we replace the raw data with the new data
        replace_h5_dataset(self.file, f"{dataset_path}/R",
                           parameter, f"{dataset_path}/{parameter_symbol}")
        replace_h5_dataset(self.file, f"{dataset_path}/I",
                           dataset)

    def delete_data(self, group_name):
        """
        Method used to properly delete data from the h5 file

        Parameters
        ----------
        group_name :
            Name of the data group to delete
        """
        group_name = group_name.upper()
        if group_name in self.file:
            del self.file[f"/ENTRY/{group_name}"]
        else:
            print("This group does not exists")

    def close(self):
        """
        Method used to close the loaded file correctly by repacking it and then closing it
        """
        self.file.close()
        repack_hdf5(self.file_path, self.file_path + ".tmp")
        os.remove(self.file_path)
        shutil.move(self.file_path + ".tmp", self.file_path)


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
