"""
This file tests the viability of some of the utilitary function of the package
"""
from ..nexus_generation import convert
from ..gui_edf2h5 import string_2_value
from ..nexus_format import dictUnit

from pytest import approx
from random import random, randrange, choice


def test_convert():
    input_value = random() * 10
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
    for unit_type in dictUnit:
        conversion_number = 0
        for start_unit in dictUnit[unit_type]:
            for end_unit in dictUnit[unit_type]:
                output_value = convert(input_value, start_unit, end_unit, True)
                if unit_type == "NX_LENGTH":
                    assert output_value == approx(
                        input_value * predicted_length_value[conversion_number])
                elif unit_type == "NX_PER_LENGTH":
                    assert output_value == approx(
                        input_value * predicted_per_length_value[conversion_number])
                elif unit_type == "NX_ANGLE":
                    assert output_value == approx(
                        input_value * predicted_angle_value[conversion_number])
                conversion_number = conversion_number + 1


def test_str2value():
    for i in range(10):
        dummy = random()
        if dummy <= 0.2:
            predicted_output = random() * 10
            input = str(predicted_output)
        elif 0.2 < dummy <= 0.4:
            predicted_output = int(randrange(0, 11))
            input = str(predicted_output)
        elif 0.4 < dummy <= 0.6:
            predicted_output = "dummy"
            input = "duMmY"
        elif 0.6 < dummy <= 0.8:
            predicted_output = \
                float(
                    str(
                        float(random() * 10)) + "e" + str(
                        randrange(-5, 5)))
            input = str(predicted_output)
        else:
            predicted_output = choice(["None", ""])
            input = predicted_output

        assert predicted_output == string_2_value(input)
