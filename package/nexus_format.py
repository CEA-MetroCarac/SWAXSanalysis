"""
This file is made to specify the required and optional argument of the NXsas format as described
in :
https://manual.nexusformat.org/classes/applications/NXsas.html#nxsas

the attribute of the entry group are specified as "attribute"
while the attributes of subgroups are specified as "path_to_subGroup_Attribute"

We could improve this program by asking the user what parameter in the header corresponds to a
NeXus parameter. That way this program could work for all equipment that outputs a .edf file that
needs to be translated into a NXsas .h5 file."""
import numpy as np

# We create the structure of the format via a first dictionary :
#   - key : path to NXgroup in HDF5 format
#    - value : ["groupName",
#               {NX_class: "groupClass", EX_required: "true|false"


dictStructureNXsas = {
    "/entry": ["entry",
               {"NX_class": "NXentry", "EX_required": "true",
                "entry": "SAMPLE-CHAR-DATA", "default": "data"}],
    "/entry/instrument": ["instrument",
                          {"NX_class": "NXinstrument", "EX_required": "true"}],
    "/entry/instrument/source": ["source",
                                 {"NX_class": "NXsource", "EX_required": "true"}],
    "/entry/instrument/monochromator": ["monochromator",
                                        {"NX_class": "NXmonochromator", "EX_required": "true"}],
    "/entry/instrument/aperture": ["aperture",
                                   {"NX_class": "NXaperture", "EX_required": "true"}],
    "/entry/instrument/detector": ["detector",
                                   {"NX_class": "NXdetector", "EX_required": "true"}],
    "/entry/sample": ["sample",
                      {"NX_class": "NXsample", "EX_required": "true"}],
    "/entry/data": ["data",
                    {"NX_class": "NXdata", "EX_required": "true", "signal": "data"}],

}

"""
We create the dictionary of parameters that have to be entered by the user they are filled as a 
dataset :
    - key : path to dataSet
    - value : [paramName, paramValue, [obligatoryValues], {attributeName: attributeValue}]
"""
dictParamNXsas = {
    "/entry/title": ["title", None, [],
                     {"type": "NX_CHAR", "EX_required": "true"}],
    "/entry/start_time": ["start_time", None, [],
                          {"type": "NX_DATE_TIME", "EX_required": "false"}],
    "/entry/end_time": ["end_time", None, [],
                        {"type": "NX_DATE_TIME", "EX_required": "false"}],
    "/entry/definition": ["definition", "NXsas", ["NXsas"],
                          {"type": "NX_CHAR", "EX_required": "true"}],
    "/entry/experiment_type": ["experiment_type", "SAXS", ["None", "SAXS", "WAXS"],
                               {"type": "NX_CHAR", "EX_required": "false"}],
    "/entry/instrument/name": ["name", None, [],
                               {"type": "NX_CHAR", "EX_required": "false"}],
    "/entry/instrument/source/type": ["type", None, [],
                                      {"type": "NX_CHAR", "EX_required": "false"}],
    "/entry/instrument/source/name": ["name", None, [],
                                      {"type": "NX_CHAR", "EX_required": "false"}],
    "/entry/instrument/source/probe": ["probe", None, ["None", "neutron", "x-ray"],
                                       {"type": "NX_CHAR", "EX_required": "false"}],
    "/entry/instrument/monochromator/wavelength": ["wavelength", None, [],
                                                   {"type": "NX_FLOAT", "EX_required": "true",
                                                    "units": "nm"}],
    "/entry/instrument/monochromator/wavelength_spread": ["wavelength_spread", None, [],
                                                          {"type": "NX_FLOAT",
                                                           "EX_required": "false"}],
    "/entry/instrument/aperture/shape": ["shape", None, ["None", "4-blade slit", "pinhole"],
                                         {"type": "NX_CHAR", "EX_required": "false"}],
    "/entry/instrument/aperture/x_gap": ["x_gap", None, [],
                                         {"type": "NX_FLOAT", "EX_required": "false",
                                          "units": "m"}],
    "/entry/instrument/aperture/y_gap": ["y_gap", None, [],
                                         {"type": "NX_FLOAT", "EX_required": "false",
                                          "units": "m"}],
    "/entry/instrument/detector/name": ["name", None, [],
                                        {"type": "NX_CHAR", "EX_required": "true"}],
    "/entry/instrument/detector/data": ["data", None, ["Autofilled"],
                                        {"type": "NX_CHAR", "EX_required": "true", "signal": "1"}],
    "/entry/instrument/detector/distance": ["distance", None, [],
                                            {"type": "NX_FLOAT", "EX_required": "true",
                                             "units": "mm"}],
    "/entry/instrument/detector/x_pixel_size": ["x_pixel_size", None, [],
                                                {"type": "NX_FLOAT", "EX_required": "true",
                                                 "units": "m"}],
    "/entry/instrument/detector/y_pixel_size": ["y_pixel_size", None, [],
                                                {"type": "NX_FLOAT", "EX_required": "true",
                                                 "units": "m"}],
    "/entry/instrument/detector/roll": ["roll", None, [],
                                        {"type": "NX_FLOAT", "EX_required": "false",
                                         "units": "rad"}],
    "/entry/instrument/detector/pitch": ["pitch", None, [],
                                         {"type": "NX_FLOAT", "EX_required": "true",
                                          "units": "rad"}],
    "/entry/instrument/detector/yaw": ["yaw", None, [],
                                       {"type": "NX_FLOAT", "EX_required": "true",
                                        "units": "rad"}],
    "/entry/instrument/detector/beam_center_x": ["beam_center_x", None, [],
                                                 {"type": "NX_FLOAT", "EX_required": "true",
                                                  "units": ""}],
    "/entry/instrument/detector/beam_center_y": ["beam_center_y", None, [],
                                                 {"type": "NX_FLOAT", "EX_required": "true",
                                                  "units": ""}],
    "/entry/instrument/detector/geometry": ["geometry", None, ["reflexion", "transmission"],
                                            {"type": "NX_CHAR", "EX_required": "true"}],
    "/entry/sample/name": ["name", None, [],
                           {"type": "NX_CHAR", "EX_required": "true"}],
    "/entry/sample/pitch": ["pitch", None, [],
                            {"type": "NX_FLOAT", "EX_required": "true", "units": "rad"}],
    "/entry/data/data": ["data", None, ["Autofilled"],
                         {"EX_required": "true", "target": "/entry/instrument/detector/data",
                          "signal": "1"}],

}

dictUnit = {
    "NX_LENGTH":
        {"m": 1, "mm": 1e-3, "nm": 1e-9, "angstrom": 1e-10},
    "NX_PER_LENGTH":
        {"1/m": 1, "1/nm": 1e9, "1/angstrom": 1e10},
    "NX_ANGLE":
        {"deg": 360, "turn": 1, "rad": 2 * np.pi},
    "NX_UNITLESS":
        {"": 1}
}
