import fabio
import h5py
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import pathlib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from SWAXSanalysis.src.nxfile_generator import generate_nexus


def gauss(x, mu, sigma, A):
    return A * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def create_file():
    header = {
        "x_p_size": 75E-6,
        "y_p_size": 75E-6,
        "x_beam_stop": 0,
        "y_beam_stop": 0,
        "incident_wav": 1e-9,
        "incident_angle": 0,
        "experiment_geo": "transmission",
        "detect_name": "Dectris EIGER2 Si 1M, S/N E-02-0299",
        "rot_x": 0,
        "rot_y": 0,
        "rot_z": 0,
        "x_center": 1000,
        "y_center": 1000,
        "samp_det_dist": 1
    }

    dims = [1028, 1062]

    x_list = np.linspace(0, dims[0], dims[0]) - header["x_center"]
    y_list = np.linspace(0, dims[1], dims[1]) - header["y_center"]

    x_mesh, y_mesh = np.meshgrid(x_list, y_list)
    z_mesh = x_mesh + y_mesh * 1j

    r_mesh = np.abs(z_mesh)

    data = gauss(r_mesh, 800, 5, 7.5) + gauss(r_mesh, 0, 25, 10)

    edf_file = fabio.edfimage.EdfImage(data=data, header=header)

    edf_path = pathlib.Path(".\\test_0_00001.edf")
    edf_path = edf_path.absolute()
    edf_file.write(edf_path)
    return edf_path


def delete_files():
    os.remove(".\\test_0_00001.edf")
    os.remove(".\\testSample_SAXS_00001.h5")


def test_conversion():
    edf_path = create_file()

    generate_nexus(
        edf_path=edf_path,
        hdf5_path=pathlib.Path(".\\testSample_SAXS_00001.h5").absolute(),
        settings_path=pathlib.Path(".\\settings_EDF2NX_testMachine_202507281529.json").absolute()
    )

    delete_files()
