"""
module to test all the processes in the nexus class
"""
import math
import numpy as np
from ..class_nexus_file import NexusFile
from .generate_dummy import *


def test_nexus_class():
    generate_sample_db()
    generate_sample_data()
    generate_nexus(
        mod_dir_path / "files" / "dummy_test_0_0.edf",
        mod_dir_path / "files",
        mod_dir_path / "files" / "settings_EDF2NX_XEUSS_202503250953.json"
    )
    generate_nexus(
        mod_dir_path / "files" / "dummy_test_0_1.edf",
        mod_dir_path / "files",
        mod_dir_path / "files" / "settings_EDF2NX_XEUSS_202503250953.json"
    )

    file_list = ["./files/dummySample_img0.h5"]
    file_number = len(file_list)
    nx_obj = NexusFile(file_list)
    try:
        # Testing the form of attributes after instantiating the object
        file_obj = nx_obj.get_file()[0]
        assert file_number == len(nx_obj.nx_files)
        assert file_list == nx_obj.file_paths
        assert file_number == len(nx_obj.dicts_parameters)

        # Testing the form of additional attribute after the first basic process
        ###############
        ### Q space ###
        ###############
        nx_obj.process_q_space(save=True)
        assert "ENTRY/DATA_Q_SPACE/" in file_obj
        assert file_number == len(nx_obj.list_smi_data)
        assert file_number == len(nx_obj.intensities_data)
        # For each process we test the following :
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_Q_SPACE")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 3

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 2
            assert math.isclose(np.nansum(value), 432705.7, rel_tol=1e-7)

        ##############
        ### Caking ###
        ##############
        nx_obj.process_caking(save=True)
        assert "ENTRY/DATA_CAKED/" in file_obj
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_CAKED")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 3

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 2
            assert math.isclose(np.nansum(value), 1517694408722698, rel_tol=1e-7)

        ######################
        ### Radial average ###
        ######################
        nx_obj.process_radial_average(save=True)
        assert "ENTRY/DATA_RAD_AVG/" in file_obj
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_RAD_AVG")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 1

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 1
            assert math.isclose(np.nansum(value), 2229871904229.2144, rel_tol=1e-7)

        #########################
        ### Azimuthal average ###
        #########################
        nx_obj.process_azimuthal_average(save=True)
        assert "ENTRY/DATA_AZI_AVG/" in file_obj
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_AZI_AVG")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 1

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 1
            assert math.isclose(np.nansum(value), 759275879901.6732, rel_tol=1e-7)

        ##############################
        ### Horizontal integration ###
        ##############################
        nx_obj.process_horizontal_integration(save=True)
        assert "ENTRY/DATA_HOR_INT/" in file_obj
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_HOR_INT")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 1

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 1
            assert math.isclose(np.nansum(value), 2709.5554514750647, rel_tol=1e-7)

        ############################
        ### Vertical integration ###
        ############################
        nx_obj.process_vertical_integration(save=True)
        assert "ENTRY/DATA_VER_INT/" in file_obj
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_VER_INT")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 1

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 1
            assert math.isclose(np.nansum(value), 2709.5554514750647, rel_tol=1e-7)

        ##########################
        ### Absolute intensity ###
        ##########################
        nx_obj.process_absolute_intensity(
            save=True,
            db_path="./files/dummySample_img1.h5",
            roi_size_x=35,
            roi_size_y=35,
            sample_thickness=0.15e-3
        )
        assert "ENTRY/DATA_ABS/" in file_obj
        # Testing the existence and dimension of data
        param_dict, value_dict = nx_obj.get_raw_data("DATA_ABS")
        for key, value in param_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value)) == 3

        # Testing the numerical value of the data via sum
        for key, value in value_dict.items():
            assert isinstance(value, np.ndarray)
            assert len(np.shape(value_dict[key])) == 2
            assert math.isclose(np.nansum(value), 6.476545e-08, rel_tol=1e-7)

        ###################
        ### Delete Data ###
        ###################
        nx_obj.process_delete_data(group_name="DATA_VER_INT")
        nx_files = nx_obj.get_file()
        for h5_obj in nx_files:
            assert "ENTRY/DATA_VER_INT" not in h5_obj


    except Exception as error:
        raise error
    finally:
        nx_obj.nexus_close()
