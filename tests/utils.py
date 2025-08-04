"""
Utils function used in test modules
"""

import os
import pathlib

import fabio
import numpy as np


HEADER = {
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

DIMS = [1028, 1062]


def gauss(x, mu, sigma, A):
    return A * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


def create_file():
    x_list = np.linspace(0, DIMS[0], DIMS[0]) - HEADER["x_center"]
    y_list = np.linspace(0, DIMS[1], DIMS[1]) - HEADER["y_center"]

    x_mesh, y_mesh = np.meshgrid(x_list, y_list)
    z_mesh = x_mesh + y_mesh * 1j

    r_mesh = np.abs(z_mesh)

    data = gauss(r_mesh, 800, 5, 7.5) + gauss(r_mesh, 0, 25, 10)

    edf_file = fabio.edfimage.EdfImage(data=data, header=HEADER)

    edf_path = pathlib.Path(".\\test_0_00001.edf")
    edf_path = edf_path.absolute()
    edf_file.write(edf_path)
    return edf_path


def create_empty_file():
    x_list = np.linspace(0, DIMS[0], DIMS[0]) - HEADER["x_center"]
    y_list = np.linspace(0, DIMS[1], DIMS[1]) - HEADER["y_center"]

    x_mesh, y_mesh = np.meshgrid(x_list, y_list)
    z_mesh = x_mesh + y_mesh * 1j

    r_mesh = np.abs(z_mesh)

    data = gauss(r_mesh, 0, 25, 15)

    edf_file = fabio.edfimage.EdfImage(data=data, header=HEADER)

    edf_path = pathlib.Path(".\\empty_0_00002.edf")
    edf_path = edf_path.absolute()
    edf_file.write(edf_path)
    return edf_path


def delete_files():
    os.remove(".\\test_0_00001.edf")
    os.remove(".\\testSample_SAXS_00001.h5")
    os.remove(".\\empty_0_00002.edf")
    os.remove(".\\testSample_DB_SAXS_00002.h5")
