import fabio
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def gauss(x, x0, sig, amp):
    return amp * np.exp((-(x - x0) ** 2) / sig ** 2)


def generate_sample_data():
    dict_param = {
        "ExposureTime": 30,
        "Geometry": "Transmission",
        "SampleDistance": 2.0,
        "WaveLength": 2e-10,
        "alpha": 0,
        "Center_1": 500,
        "Center_2": 500,
        "PSize_1": 7.5e-05,
        "PSize_2": 7.5e-05,
        "Sample": "dummySample",
        "DetectorModel": "Dectris EIGER2 Si 1M, S/N E-02-0299",
        "Delta": 0,
        "Gamma": 0,
    }

    mesh_x, mesh_y = np.mgrid[:100, :100]
    mesh_circle = (mesh_x - 50) ** 2 + (mesh_y - 50) ** 2
    mask1 = np.logical_and(mesh_circle < 3 ** 2, mesh_circle > 0 ** 2)
    data1 = gauss(np.sqrt(mesh_circle), 0, 2, 5) * mask1

    mask2 = np.logical_and(mesh_circle < 25 ** 2, mesh_circle > 20 ** 2)
    data2 = gauss(np.sqrt(mesh_circle), 25, 1, 1.5) * mask2

    data = data1 + data2

    fabio_obj = fabio.edfimage.edfimage()

    for key, value in dict_param.items():
        fabio_obj.header[key] = value

    fabio_obj.data = data

    mod_dir_path = Path(__file__).parent
    file_path = mod_dir_path / "files" / "dummy_test_0_0.edf"
    fabio_obj.write(file_path)


def generate_sample_db():
    dict_param = {
        "ExposureTime": 30,
        "Geometry": "Transmission",
        "SampleDistance": 2.0,
        "WaveLength": 2e-10,
        "alpha": 0,
        "Center_1": 50,
        "Center_2": 50,
        "PSize_1": 7.5e-05,
        "PSize_2": 7.5e-05,
        "Sample": "dummySample",
        "DetectorModel": "Dectris EIGER2 Si 1M, S/N E-02-0299",
        "Delta": 0,
        "Gamma": 0,
    }

    mesh_x, mesh_y = np.mgrid[:100, :100]
    mesh_circle = (mesh_x - 50) ** 2 + (mesh_y - 50) ** 2
    mask1 = np.logical_and(mesh_circle < 3 ** 2, mesh_circle > 0 ** 2)
    data1 = gauss(np.sqrt(mesh_circle), 0, 2, 7) * mask1

    data = data1

    fabio_obj = fabio.edfimage.edfimage()

    for key, value in dict_param.items():
        fabio_obj.header[key] = value

    fabio_obj.data = data

    mod_dir_path = Path(__file__).parent
    file_path = mod_dir_path / "files" / "dummy_test_0_1.edf"
    fabio_obj.write(file_path)
    return data


def delete_dummies():
    files_path = Path(__file__).parent / "files"
    os.remove(files_path / "dummy_test_0_0.edf")
    os.remove(files_path / "dummy_test_0_1.edf")

generate_sample_db()
generate_sample_data()
