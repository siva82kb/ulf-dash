"""
Module containing configuration informaiton for the ULFunc Analysis Dashboard
application.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 04 Oct 2022
"""

from enum import Enum
from attrdict import AttrDict
import json
import numpy as np

import sys
from monalysa import readers
import tempsupport as tmpsprt

# Constants
SUPPORTED_SENSORS = {
    "ActiGraphGt3x": {
        "name": "ActiGraphGt3x Sensor",
        "Raw Data": {
            "extn": "gt3x",
            "samplingrate": 100,
            "reader": None,
        },
        "Vector Magnitude": {
            "extn": "csv",
            "samplingrate": 1,
            "reader": readers.ActiGraphData.read_organize_data,
        },
    },
    "ARIMU": {
        "name": "Arm Use IMU Sensor",
        "Raw Data": {
            "extn": "csv",
            "samplingrate": 100,
            "reader": tmpsprt.ARIMU.read_organize_data,
        }
    }
}
MEASURE_LABELS = {
    'use': {
        'vm1': 'Single Th.',
        'vm2': 'Double Th.',
        'vm1_wf': 'Single Th. (Waist Filt.)',
        'vm2_wf': 'Double Th. (Waist Filt.)',
        'gmac': 'Gross Movement + Activity Counts',
    },
    'int': {
        'vm1': 'Vec. Mag. Single Th.',
        'vm2': 'Vec. Mag. Double Th.',
        'vm1_wf': 'Vec. Mag. Single Th. (Waist Filt.)',
        'vm2_wf': 'Vec. Mag. Double Th. (Waist Filt.)',
        'gsm_gmac': 'Gravity Subtracted Magnitude'
    },
    'latinx': {
        'use_vm1': 'Single Th.',
        'use_vm2': 'Double Th.',
        'use_vm1_wf': 'Single Th. (Waist Filt.)',
        'use_vm2_wf': 'Double Th. (Waist Filt.)',
        'use_gmac': 'Gross Movement + Activity Counts',
        'int_vm1': 'Vec. Mag. Single Th.',
        'int_vm2': 'Vec. Mag. Double Th.',
        'int_gsm': 'Gravity Subtracted Magnitude',
        'int_vm1_wf': 'Vec. Mag. Single Th. (Waist Filt.)',
        'int_vm2_wf': 'Vec. Mag. Double Th. (Waist Filt.)',
    }
}
MEASURE_SHORT_LABELS = {
    'use': {
        'vm1': 'Sin. Th.',
        'vm2': 'Dob. Th.',
        'vm1_wf': 'Sin. Th. (WF)',
        'vm2_wf': 'Dob. Th. (WF)',
        'gmac': 'GM  + AC',
    },
    'int': {
        'vm1': 'VM Sin. Th.',
        'vm2': 'VM Dob. Th.',
        'vm1_wf': 'VM Sin. Th. (WF)',
        'vm2_wf': 'VM Dob. Th. (WF)',
        'gsm_gmac': 'Grav. Sub. Mag.',
    },
    'latinx': {
        'use_vm1': 'Sin. Th.',
        'use_vm2': 'Dob. Th.',
        'use_vm1_wf': 'Sin. Th. (WF)',
        'use_vm2_wf': 'Dob. Th. (WF)',
        'use_gmac': 'GM  + AC',
        'int_vm1': 'Vec. Mag. Sin. Th.',
        'int_vm2': 'Vec. Mag. Dob. Th.',
        'int_vm1_wf': 'Vec. Mag. Sin. Th. (WF)',
        'int_vm2_wf': 'Vec. Mag. Dob. Th. (WF)',
        'int_gsm': 'Grav. Sub. Mag.',
    }
}
SUPPORTED_SENSOR_LOCATIONS = {
    "ActiGraphGt3x": {
        "Right Wrist": 'R',
        "Left Wrist": 'L',
        "Waist": 'W'
    },
    "ARIMU": {
        "Right Wrist": 'RIGHT',
        "Left Wrist": 'LEFT',
    },
}
TEMPORAL_SUMM_MEASURES = {
    "ActiGraphGt3x": {
        "Hq": "vm2_wf*vm2_wf",
        "LI": "vm2_wf",
    },
    "ARIMU": {
        "Hq": "gmac*gsm_gmac",
        "LI": "gsm_gmac",
    },
}

OUTPUT_DIR = "_output"
PROC_FILE_EXTN = "aipc"

# Maximum ULFUNC measures sampling rate (in Hz)
MIN_ULFUNC_SAMPLETIME = 10.

class ERRORTYPES(Enum):
    DUPLICATE_TIMESTAMPS = 0


class WARNINGTYPES(Enum):
    IGNORING_FILE = 0


def is_sensor_supported(sensname: str) -> bool:
    """Checks if the given sensors name is supporred.

    Args:
        sensname (str): Name of the sensor used.

    Returns:
        bool: True if the sensor is currently supported, else its False.
    """
    return sensname in SUPPORTED_SENSORS


def is_datatype_supported(sensname: str, datatype: str) -> bool:
    """Checks if the data type is supported for the given sensor type.

    Args:
        sensname (str): Name of the sensor used.
        datatype (str): Name of the data type for the sensor used. 

    Returns:
        bool: True of the sensor AND the datatype are supported, else False. 
    """
    return (sensname in SUPPORTED_SENSORS
            and datatype in SUPPORTED_SENSORS[sensname])


def is_sensor_locs_supported(locs: list[str]) -> list[bool]:
    """Checks if the list of sensor locations is currently supported. This
    function returns a list of bool for all sensor locations that are
    supported.

    Args:
        locs (list[str]): List of location for the sensors.

    Returns:
        list[bool]: List of bools of the same length as the input list,
        indicating if each individual location is supported.
    """
    return [l in SUPPORTED_SENSOR_LOCATIONS for l in locs]


def get_datafile_extn(sensname: str, data_type: str) -> str:
    """Returns the file extension for the give sensor and data type.

    Args:
        sensname (str): Name of the sensor used.
        data_type (str): Name of the data type for the sensor used.

    Returns:
        str: Extension of the file containing the data.
    """
    return SUPPORTED_SENSORS[sensname][data_type]["extn"]


def get_sampling_rate(sensname: str, data_type: str) -> float:
    """Returns the sampling rate for the give sensor and data type.

    Args:
        sensname (str): Name of the sensor used.
        data_type (str): Name of the data type for the sensor used.

    Returns:
        float: Sampling rate for the given sensor and data type.
    """
    return SUPPORTED_SENSORS[sensname][data_type]["samplingrate"]


def read_data_params(fname: str) -> AttrDict:
    """Read the data params json file and returns a AttrDict.

    Parameters
    ----------
    datadir : str
        Name of the data_params files.

    Returns
    -------
    AttrDict
        AttrDict with the detials of the data params.
    """
    # Read population_params.json file
    with open(fname, "r") as fh:
        data_params = AttrDict(json.load(fh))
    data_params.locid = [SUPPORTED_SENSOR_LOCATIONS[data_params.sensor][_l]
                         for _l in data_params.locs]
    return data_params


def read_analysis_params(fname: str, dataparams: AttrDict) -> AttrDict:
    """Read the analysis parameters file and compute the different rates
    associated with the different types of information that is to be computed
    during the analysis.

    Args:
        fname (str): Name of the analysis parameters json file.
        sensorparams (AttrDict): An AttrDict contains the data parameters that
        has the details of the data to be analysed.
        
    Returns:
        AttrDict: AttrDict contains the details of the analysis parameters.
    """
    with open(fname, "r") as fh:
        analysis_params = AttrDict(json.load(fh))
    
    # Compute the different sampling rates and their corresponding sampling rate
    # ratios.
    _srateraw = get_sampling_rate(sensname=dataparams.sensor,
                                  data_type=dataparams.data_type)
    _srateulfi = np.min([analysis_params['ulfuncinstsamprate'],
                         MIN_ULFUNC_SAMPLETIME,
                         _srateraw])
    _srateulfa = 1 / analysis_params["avgwinshift"]
    analysis_params['samptr'] = {
        "raw": [1 / _srateraw, _srateraw, 1],
        "ulfuncinst": [1 / _srateulfi, _srateulfi, int(_srateraw / _srateulfi)],
        "ulfuncavrg": [1 / _srateulfa, _srateulfa, int(_srateulfi / _srateulfa)],
        "summary": [[_sw * 60, 1 / (_sw * 60), int(_sw * 60 * _srateulfa)]
                    for _sw in analysis_params['summarywin']]
    }
    return analysis_params


def read_measures_params(fname: str) -> AttrDict:
    """Read the measures params json file and returns a AttrDict.

    Parameters
    ----------
    datadir : str
        Name of the measures_params file.

    Returns
    -------
    AttrDict
        AttrDict with the detials of the meaures params.
    """
    # Read population_params.json file
    with open(fname, "r") as fh:
        measures_params = AttrDict(json.load(fh))
    return measures_params
