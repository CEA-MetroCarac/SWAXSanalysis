"""
Testing module for processes, detect if the group
associated to the process has been created or not
"""

import fabio
import h5py
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from SWAXSanalysis.class_nexus_file import NexusFile
from SWAXSanalysis.nxfile_generator import generate_nexus
from .utils import *


def test_processes():
    list_created_paths = ["ENTRY/DATA"]

    # delete_files()
    EDF_PATH = create_file()
    HDF5_PATH = pathlib.Path(generate_nexus(
        edf_path=EDF_PATH,
        hdf5_path=pathlib.Path(".\\testSample_SAXS_00001.h5").absolute(),
        settings_path=pathlib.Path(".\\settings_EDF2NX_testMachine_202507281529.json").absolute()
    ))

    EDF_PATH_EMPTY = create_empty_file()
    HDF5_PATH_EMPTY = pathlib.Path(generate_nexus(
        edf_path=EDF_PATH_EMPTY,
        hdf5_path=pathlib.Path(".\\testSample_DB_SAXS_00002.h5").absolute(),
        settings_path=pathlib.Path(".\\settings_EDF2NX_testMachine_202507281529.json").absolute()
    ))

    nx_object = NexusFile([HDF5_PATH])
    try:
        nx_object.process_q_space(save=True)
        list_created_paths.append("ENTRY/DATA_Q_SPACE")

        nx_object.process_caking(save=True)
        list_created_paths.append("ENTRY/DATA_CAKED")

        nx_object.process_radial_average(save=True)
        list_created_paths.append("ENTRY/DATA_RAD_AVG")

        nx_object.process_azimuthal_average(save=True)
        list_created_paths.append("ENTRY/DATA_AZI_AVG")

        nx_object.process_horizontal_integration(save=True)
        list_created_paths.append("ENTRY/DATA_HOR_INT")

        nx_object.process_vertical_integration(save=True)
        list_created_paths.append("ENTRY/DATA_VER_INT")

        nx_object.process_absolute_intensity(save=True, db_path=HDF5_PATH_EMPTY)
        list_created_paths.append("ENTRY/DATA_ABS")
    except Exception as error:
        raise error
    finally:
        nx_object.nexus_close()

    with h5py.File(HDF5_PATH, "r") as h5py_file_obj:

        for group in list_created_paths:
            group_obj = h5py_file_obj.get(group, False)
            assert group_obj
    delete_files()