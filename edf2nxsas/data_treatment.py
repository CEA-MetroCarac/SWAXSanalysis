"""
The main feature of this module is the NexusFile class which is used
to treat raw data contained in a .h5 file formated according
to the NXcanSAS standard
"""
import shutil
import os
import numpy as np
import h5py

import matplotlib.pyplot as plt

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


def replace_h5_dataset(data_file, dataset_path, new_data, new_dataset_path=None):
    """
    Function used to replace a dataset that's already been created
    in a hdf5 file

    Parameters
    ----------
    data_file :
        File containing the dataset

    dataset_path :
        Path of the dataset in the hdf5 file

    new_data :
        new value for the dataset

    new_dataset_path :
        default is None, used if you want to change the name of the data set
        as you replace it
    """
    old_dataset = data_file[dataset_path]
    attributes = dict(old_dataset.attrs)

    del data_file[dataset_path]

    if new_dataset_path:
        new_dataset = data_file.create_dataset(new_dataset_path,
                                               data=new_data,
                                               compression="gzip",
                                               compression_opts=9)
    else:
        new_dataset = data_file.create_dataset(dataset_path,
                                               data=new_data,
                                               compression="gzip",
                                               compression_opts=9)

    for key, value in attributes.items():
        new_dataset.attrs[key] = value


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
        self.file_path = h5_path
        self.file = h5py.File(h5_path, "r+")

        self.dict_parameters = {
            "beam stop": [[0, 0]]
        }

        # We extract the relevant info from the H5 file
        intensity_data = [self.file["ENTRY/DATA/I"][:]]
        position_data = [self.file["ENTRY/DATA/R"][:]]
        self.dict_parameters["I raw data"] = intensity_data
        self.dict_parameters["R raw data"] = position_data

        # Concerning the source
        wavelength = self.extract_from_h5("ENTRY/INSTRUMENT/SOURCE/incident_wavelength")
        self.dict_parameters["wavelength"] = wavelength * 1e-9

        # Concerning the sample
        incident_angle = self.extract_from_h5("ENTRY/SAMPLE/yaw")
        self.dict_parameters["incident angle"] = incident_angle

        # Concerning the detector
        detector_name = str(self.extract_from_h5("/ENTRY/INSTRUMENT/DETECTOR/name"))
        if "dectris eiger2 si 1m, s/n e-02-0299" in detector_name.lower():
            self.dict_parameters["detector name"] = "Eiger1M_xeuss"
        elif "dectris eiger2 r 500k, s/n e-01-0326" in detector_name.lower():
            self.dict_parameters["detector name"] = "Eiger500k_xeuss"

        beam_center_x = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/beam_center_x")
        beam_center_y = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/beam_center_y")
        self.dict_parameters["beam center"] = [beam_center_x, beam_center_y]

        rotation_1 = -self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/yaw")
        rotation_2 = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/pitch")
        rotation_3 = -self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/roll")
        self.dict_parameters["detector rotation"] = [[rotation_1, rotation_2, rotation_3]]

        sample_detector_distance = self.extract_from_h5("ENTRY/INSTRUMENT/DETECTOR/SDD")
        self.dict_parameters["distance"] = sample_detector_distance

        # We input the info in the SMI package
        self.smi_data = SMI_beamline.SMI_geometry(
            geometry="Transmission",
            sdd=self.dict_parameters["distance"] * 1e3,
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
        return self.file

    def extract_from_h5(self, path, data_type="dataset", attribute_name=None):
        """
        Method used to extract a dataset or attribute from the .h5 file

        Parameters
        ----------
        path :
            path of the dataset

        data_type :
            type of the value extracted (attribute or dataset)

        attribute_name :
            if it's an attribute, give its name

        Returns
        -------
        Either the attribute or dataset selected

        """
        dataset = self.file[path]
        attributes = dataset.attrs
        if data_type == "dataset" and np.shape(dataset) == ():
            return dataset[()]
        elif data_type == "dataset" and np.shape(dataset) != ():
            return dataset[:]
        elif data_type == "attribute" and attribute_name in attributes.keys():
            return attributes[attribute_name]
        else:
            print(f"error while extracting from {path}")
            return None

    def q_space(self, display=False, save=False, group_name="DATA_Q_SPACE"):
        """
        Method used to put the data in Q space (Fourier space)

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

        if save:
            dim = np.shape(self.dict_parameters["R raw data"][0])
            qx_list = np.linspace(self.smi_data.qp[0], self.smi_data.qp[-1], dim[1])
            qy_list = np.linspace(self.smi_data.qz[-1], self.smi_data.qz[0], dim[0])
            qx_grid, qy_grid = np.meshgrid(qx_list, qy_list)
            mesh_q = np.stack((qx_grid, qy_grid), axis=-1)

            self.save_data("Q", mesh_q, group_name, self.smi_data.img_st)

    def caking(self, display=False, save=False, group_name="DATA_CAKED"):
        """
        Method used to cake the data

        Parameters
        ----------
        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        self.smi_data.caking(azimuth_range=[-180, 180],
                             radial_range=[min(self.smi_data.qz), max(self.smi_data.qz)],
                             npt_azim=1000,
                             npt_rad=1000)

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

    def radial_average(self, r_range=None, angle_range=None, display=False, save=False, group_name="DATA_RAD_AVG"):
        """
        Method used to do the radial average of the data in fourier space

        Parameters
        ----------
        r_range :
            Radial range of the radial averaging

        angle_range :
            Angle range of the radial averaging

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        if r_range is None:
            qp_max = max(self.smi_data.qp)
            qz_max = max(self.smi_data.qz)

            qr_max = np.sqrt(qp_max ** 2 + qz_max ** 2)

            r_range = [0, qr_max]

        if angle_range is None:
            angle_range = [-180, 180]

        self.smi_data.radial_averaging(azimuth_range=angle_range,
                                       npt=2000,
                                       radial_range=r_range)

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

    def horizontal_integration(self, qx_range=None, qy_range=None, display=False, save=False, group_name="DATA_HOR_INT"):
        """
        Method used to do the horizontal integration of the data in fourier space

        Parameters
        ----------
        qx_range:
            horizontal range of the horizontal averaging

        qy_range :
            vertical range of the horizontal averaging

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        if qx_range is None:
            qx_range = [self.smi_data.qp[0], self.smi_data.qp[-1]]
        if qy_range is None:
            qy_range = [self.smi_data.qz[0], self.smi_data.qz[-1]]

        self.smi_data.horizontal_integration(q_per_range=qy_range, q_par_range=qx_range)

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

    def vertical_integration(self, qx_range=None, qy_range=None, display=False, save=False, group_name="DATA_VER_INT"):
        """
        Method used to do the vertical integration of the data in fourier space.

        Parameters
        ----------
        qx_range:
            horizontal range of the horizontal averaging

        qy_range :
            vertical range of the horizontal averaging

        display :
            Choose if you want the result displayed or not

        save :
            Choose if you want the result saved in the .h5 or not

        group_name:
            Name of the group that will contain the data
        """
        self.smi_data.masks = np.logical_not(np.ones(np.shape(self.smi_data.imgs)))
        self.smi_data.calculate_integrator_trans(self.dict_parameters["detector rotation"])

        if qx_range is None:
            qx_range = [self.smi_data.qp[0], self.smi_data.qp[-1]]
        if qy_range is None:
            qy_range = [self.smi_data.qz[0], self.smi_data.qz[-1]]

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

    def save_data(self, parameter_symbol, parameter, dataset_name, dataset):
        """
        Method used to save data in the h5 file

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
        dataset_name = dataset_name.upper()
        dataset_path = f"/ENTRY/{dataset_name}"
        if dataset_path in self.file:
            del self.file[dataset_path]
        self.file.copy("ENTRY/DATA", self.file["/ENTRY"], dataset_name)

        replace_h5_dataset(self.file, f"{dataset_path}/R",
                           parameter, f"{dataset_path}/{parameter_symbol}")
        replace_h5_dataset(self.file, f"{dataset_path}/I", dataset)

    def delete_data(self, group_name):
        """
        Method used to properly delete data from the h.5 file

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
        Method used to close the loaded file correctly
        """
        self.file.close()
        repack_hdf5(self.file_path, self.file_path + ".tmp")
        os.remove(self.file_path)
        shutil.move(self.file_path + ".tmp", self.file_path)


if __name__ == "__main__":
    FILE_NAME = "C:\\Users\\AT280565\\PycharmProjects\\EdfToHdf5\\edf2NxSAS\\" \
                "treated data\\instrument - Xeuss\\" \
                "config - 2024-12-19T15-00\\sample - SafeLiMove\\" \
                "experiment - SAXS\\format - NXsas\\defaultSampleName_SAXS_2025-01-07T10-49-59.h5"

    nx_file = NexusFile(FILE_NAME)
    nx_file.q_space(display=True, save=True)
    nx_file.close()
