"""
Module to test everything regarding the conversion from edf to hdf5
"""
import os
import math
import pathlib
import numpy as np
from pathlib import Path

import h5py
from ..nxfile_generator import generate_nexus
from ..class_nexus_file import extract_smi_param
from .generate_dummy import *


def gauss(x, x0, sig, amp):
    return amp * np.exp((-(x - x0) ** 2) / sig ** 2)


def test_conversion():
    original_param_dict = {
        'beam stop': [[0, 0]],
        'wavelength': 2e-10,
        'incident angle': 0,
        'detector name': 'Eiger1M_xeuss',
        'detector rotation': [[0, 0, 0]],
        'beam center': [50, 50],
        'distance': 2000.0
    }

    original_data = generate_sample_data()

    mod_dir_path = Path(__file__).parent
    h5_path = generate_nexus(
        mod_dir_path / "files" / "dummy_test_0_0.edf",
        mod_dir_path / "files",
        mod_dir_path / "files" / "settings_EDF2NX_XEUSS_202503250953.json"
    )
    with h5py.File(h5_path) as h5_obj:
        param_dict = extract_smi_param(h5_obj, "DATA")

    h5_path = Path(h5_path)
    h5_name = h5_path.name
    split_name = h5_name.split("_")

    try:
        # Testing the name of the file
        assert split_name[0] + "_" + split_name[1] == "dummySample_img0"

        # Testing the data
        sum_original = np.sum(original_data)
        sum_processes = np.sum(param_dict["I raw data"])
        assert math.isclose(sum_original, sum_processes, rel_tol=1e-7)

        # Testing the extracted parameters
        for key, value in original_param_dict.items():
            assert param_dict[key] == value
    except Exception as error:
        raise error
    finally:
        os.remove(h5_path)
    delete_dummies()
