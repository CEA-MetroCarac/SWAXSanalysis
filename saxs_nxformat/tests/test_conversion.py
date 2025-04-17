"""
Module to test everything regarding the conversion from edf to hdf5
"""
import os
import math
import numpy as np
from pathlib import Path

import h5py
from saxs_nxformat.nxfile_generator import generate_nexus
from saxs_nxformat.class_nexus_file import extract_smi_param

original_param_dict = {
    'beam stop': [[0, 0]],
    'wavelength': 2e-10,
    'incident angle': 0,
    'detector name': 'Eiger1M_xeuss',
    'detector rotation': [[0, 0, 0]],
    'beam center': [500, 500],
    'distance': 2000.0
}


def gauss(x, x0, sig, amp):
    return amp * np.exp((-(x - x0) ** 2) / sig ** 2)


mesh_x, mesh_y = np.mgrid[:1000, :1000]
mesh_circle = (mesh_x - 500) ** 2 + (mesh_y - 500) ** 2
mask1 = np.logical_and(mesh_circle < 30 ** 2, mesh_circle > 0 ** 2)
data1 = gauss(np.sqrt(mesh_circle), 0, 20, 50) * mask1

mask2 = np.logical_and(mesh_circle < 250 ** 2, mesh_circle > 200 ** 2)
data2 = gauss(np.sqrt(mesh_circle), 225, 10, 15) * mask2

original_data = data1 + data2

def test_conversion():
    h5_path = generate_nexus("files/dummy_test_0_0.edf", "./files/", "./files/settings_EDF2NX_XEUSS_202503250953.json")
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
