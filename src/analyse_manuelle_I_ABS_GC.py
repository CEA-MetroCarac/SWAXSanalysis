import h5py

from .class_nexus_file import NexusFile
from .utils import replace_h5_dataset
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

file_paths = [
    Path(r"C:\Users\AT280565\Desktop\Data Treatment Center\Treated Data\instrument - "
         r"XEUSS\GC\Glassy_Carbon_WAXS_img00001.h5"),
    Path(r"C:\Users\AT280565\Desktop\Data Treatment Center\Treated Data\instrument - "
         r"XEUSS\GC\Glassy_Carbon_WAXS_img00004.h5")
]

nx_obj = NexusFile(file_paths)
try:
    dict_param, dict_I = nx_obj.get_raw_data("DATA_RAD_AVG_ABS")
    list_file = nx_obj.get_file()
    for index, (key, item) in enumerate(dict_I.items()):
        h5_file = list_file[index]
        new_data = item * (1/400)
        replace_h5_dataset(h5_file, "ENTRY/DATA_RAD_AVG_ABS/I", new_data)
except Exception as e:
    raise e
finally:
    nx_obj.nexus_close()

