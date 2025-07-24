import h5py

from .class_nexus_file import NexusFile
from .utils import replace_h5_dataset
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

file_path = Path(r"C:\Users\AT280565\Desktop\Data Treatment Center\Treated Data\instrument - "
                 r"XEUSS\250513_Gouze\cap_2mm\AgBeCap_SAXS_img00123.h5")
db_path = Path(r"C:\Users\AT280565\Desktop\Data Treatment Center\Treated Data\instrument - "
               r"XEUSS\250513_Gouze\cap_2mm\AgBeCap_SAXS_img00123.h5_DB.h5")

with h5py.File(file_path, "r+") as nx_file:
    replace_h5_dataset(nx_file, "ENTRY/INSTRUMENT/DETECTOR/SDD", 0.348)

nx_obj = NexusFile([file_path])
try:
    nx_obj.process_absolute_intensity(db_path)
except Exception as err:
    raise err
finally:
    nx_obj.nexus_close()

nx_obj = NexusFile([file_path], input_data_group="DATA_ABS")
try:
    nx_obj.process_q_space(save=True)
    nx_obj.process_radial_average( save=True)
    dict_param, dict_inten = nx_obj.get_raw_data("DATA_RAD_AVG")
except Exception as err:
    raise err
finally:
    nx_obj.nexus_close()

plt.figure()

for key in dict_param.keys():
    data_adr = dict_inten[key]
    plt.plot(dict_param[key], dict_inten[key]*1.1)
    # plt.xscale("log")
    # plt.yscale("log")

# Nom du fichier à lire
filename = r"C:\Users\AT280565\PycharmProjects\EdfToHdf5\AgBe Benoît en ang-1.dat"

# Listes pour stocker les colonnes
col1 = []
col2 = []
col3 = []

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Ignorer les deux premières lignes d'en-tête
data_lines = lines[2:]

for line in data_lines:
    # Remplacer les virgules par des points pour respecter la notation décimale Python
    line = line.replace(',', '.')

    # Séparer la ligne en colonnes (en supposant qu'elles sont séparées par des tabulations ou des espaces multiples)
    parts = line.split()

    # Convertir en float et ajouter aux listes
    if len(parts) == 3:
        col1.append(float(parts[0]))
        col2.append(float(parts[1]))
        col3.append(float(parts[2]))

# plt.plot(np.array(col1)*10, col2)
plt.plot(np.array(col1)*10, col3)
plt.xlim([0.75, 10])
plt.ylim([0, 2.1])
plt.show()
