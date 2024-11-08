"""
This file contains all the function that are used to generates the .h5 file with a NeXus standard
"""
import tkinter.messagebox
import os
from datetime import datetime
import h5py

from .nexus_format import dictStructureNXsas, dictUnit, dictParamNXsas


def convert(number, unit_start, unit_end, testing=False):
    """
    Converts a value that is expressed in the unitStart into a value expressed in the unitEnd

    Parameters
    ----------

    number
        the value that needs to be converted

    unit_start
        the starting unit of the value

    unit_end
        the unit we want to convert it to

    testing
        a boolean var to know if we are in testing conditions or not

    Returns
    -------
    The converted value

    """
    if number is None:
        return number
    unit_type1 = None
    unit_type2 = None
    for key, value in dictUnit.items():
        if unit_start in value:
            unit_type1 = key

        if unit_end in value:
            unit_type2 = key

    if unit_type1 is None or unit_type2 is None or unit_type1 != unit_type2 and not testing:
        tkinter.messagebox.showerror("Error",
                                     f"The value {number} {unit_start} could not be converted to "
                                     f"{unit_end} :\n")
    elif unit_type1 is None or unit_type2 is None or unit_type1 != unit_type2 and testing:
        return "fail"

    unit_type = unit_type1

    if unit_type == "NX_ANGLE":
        starting_unit = dictUnit[unit_type][unit_start]
        intermediate_unit = dictUnit[unit_type]["turn"]
        ending_unit = dictUnit[unit_type][unit_end]

        number = number * (intermediate_unit / starting_unit)
        number = number * (ending_unit / intermediate_unit)
    else:
        starting_unit = dictUnit[unit_type][unit_start]
        ending_unit = dictUnit[unit_type][unit_end]

        number = number * (starting_unit / ending_unit)

    # print(number_start, unitStart, number, unitEnd)
    return number


def generate_nxsas_file(param_dict, data, output_directory="./"):
    """
    This function generated the hdf5 file based on the filled out NXsas parameters dictionnary and
    the data contained in the edf file.

    Parameters
    ----------
    param_dict
        the filled out dictionary

    data
        the data extracted from the edf file

    output_directory
        the directory where the file will be saved
    """
    sample_name = str(param_dict["/entry/sample/name"][1])
    exp_type = str(param_dict["/entry/experiment_type"][1])
    current_time = datetime.now()
    time_stamp = str(current_time.strftime("%Y-%m-%dT%H-%M-%S"))

    # Create the HDF5 file
    file_name = os.path.join(output_directory, f"{sample_name}_{exp_type}_{time_stamp}.h5")
    with h5py.File(file_name, 'w') as h5file:
        # Create the structure as specified in dictStructureNXsas
        for key_group, value_group in dictStructureNXsas.items():
            group = h5file.require_group(key_group)

            # Add attributes to the group
            for key_attribute, value_attribute in value_group[1].items():
                group.attrs[key_attribute] = value_attribute

        h5file["/entry/data/data"] = h5py.SoftLink('/entry/instrument/detector/data')

        # Loop through paramDict to create datasets
        for key_dataset, value_dataset in param_dict.items():
            dataset_name = value_dataset[0]
            dataset_value = value_dataset[1]
            if "units" in value_dataset[3].keys():
                unit = value_dataset[3]["units"]
                forced_unit = dictParamNXsas[key_dataset][3]["units"]

                dataset_value = convert(dataset_value, unit, forced_unit)

                value_dataset[3]["units"] = forced_unit

            # Create the full path to the dataset's group
            dataset_group = h5file.require_group(
                os.path.dirname(key_dataset))  # This gets the group path

            # Create the dataset in the correct group
            if key_dataset == "/entry/data/data":
                dataset = h5file.require_group(os.path.dirname(key_dataset))
            elif key_dataset == "/entry/instrument/detector/data":
                dataset = dataset_group.create_dataset(name=dataset_name, data=data, maxshape=None)
            else:
                if dataset_value is None:
                    value_type = value_dataset[3]["type"]
                    if value_type == "NX_FLOAT":
                        dataset_value = 0.0
                    elif value_type == "NX_CHAR":
                        dataset_value = "N/A"
                    elif value_type == "NX_DATE_TIME":
                        dataset_value = "0000-00-00T00:00:00"
                    else:
                        dataset_value = "None"
                dataset = dataset_group.create_dataset(name=dataset_name, data=dataset_value,
                                                       maxshape=None)

            # Add attributes to the dataset
            for key_attribute, value_attribute in value_dataset[3].items():
                dataset.attrs[key_attribute] = value_attribute
