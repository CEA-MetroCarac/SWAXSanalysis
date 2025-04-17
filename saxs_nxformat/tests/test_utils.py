"""
Testing module to test the utils functions
"""

"""
This file tests the viability of some of the utilitary function of the package
"""
from pathlib import Path
import re
import random
import math
import tkinter as tk
from tkinter import ttk
from typing import Any

import h5py
import numpy as np
from ..utils import *
from .. import DICT_UNIT


def test_convert():
    input_value = random.random() * 10
    print(input_value)
    predicted_length_value = [1, 1e3, 1e9, 1e10,
                              1e-3, 1, 1e6, 1e7,
                              1e-9, 1e-6, 1, 1e1,
                              1e-10, 1e-7, 1e-1, 1]
    predicted_per_length_value = [1, 1e-9, 1e-10,
                                  1e9, 1, 1e-1,
                                  1e10, 1e1, 1]
    predicted_angle_value = [1, 1 / 360, 6.283185307179586 * 1 / 360,
                             360, 1, 6.283185307179586,
                             360 * 1 / 6.283185307179586, 1 / 6.283185307179586, 1]
    for unit_type in DICT_UNIT:
        conversion_number = 0
        for start_unit in DICT_UNIT[unit_type]:
            for end_unit in DICT_UNIT[unit_type]:
                output_value = convert(input_value, start_unit, end_unit, True)
                if unit_type == "NX_LENGTH":
                    assert math.isclose(
                        output_value,
                        input_value * predicted_length_value[conversion_number],
                        rel_tol=1e-5
                    )
                elif unit_type == "NX_PER_LENGTH":
                    assert math.isclose(
                        output_value,
                        input_value * predicted_per_length_value[conversion_number],
                        rel_tol=1e-5
                    )
                elif unit_type == "NX_ANGLE":
                    assert math.isclose(
                        output_value,
                        input_value * predicted_angle_value[conversion_number],
                        rel_tol=1e-5
                    )
                conversion_number = conversion_number + 1


def test_str2value():
    test_values = [
        "None",
        "dEfaUlt",
        "",
        "1e4",
        "1.56e4",
        "26.397e-3",
        "TruE",
        "FAlsE",
        "368",
        "UppER_SnAKE_CasE",
        "DumMY sTRiNG"
    ]
    predicted_values = [
        None,
        None,
        None,
        10000,
        15600,
        0.026397,
        True,
        False,
        368,
        "UPPER_SNAKE_CASE",
        "DumMY sTRiNG"
    ]
    for index, test in enumerate(test_values):
        assert string_2_value(test) == predicted_values[index]


def test_extract():
    file_path = Path("./files/dummySample_img0.h5")
    with h5py.File(file_path) as h5_obj:
        wav = extract_from_h5(h5_obj, "ENTRY/INSTRUMENT/SOURCE/incident_wavelength")
        assert math.isclose(wav, 0.2, rel_tol=1e-5)
        wav_unit = extract_from_h5(h5_obj, "ENTRY/INSTRUMENT/SOURCE/incident_wavelength", "attribute", "units")
        assert wav_unit == "nm"
