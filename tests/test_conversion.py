"""
test module to see if the conversion took place
correctly or not
"""

import fabio
import h5py
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from SWAXSanalysis.nxfile_generator import generate_nexus
from .utils import *


def test_basic_conversion():
    edf_path = create_file()

    generate_nexus(
        edf_path=edf_path,
        hdf5_path=pathlib.Path(".\\testSample_SAXS_00001.h5").absolute(),
        settings_path=pathlib.Path(".\\settings_EDF2NX_testMachine_202507281529.json").absolute()
    )

    delete_files()
