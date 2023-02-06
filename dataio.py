"""
Module to take care of reading and writing files as part of the ULFUNC dashboard
library.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 05 Oct 2022
"""

import pandas
import dashconfig as dcfg


def read_sensor_data(filename: str, sensname: str, datatype: str) -> pandas.DataFrame:
    """A generic function to read data from any supported sensor and data type.
    The function takes the filename, sensorname, and datatype, and calls the 
    appropriate reader to return a pandas DataFrame with the file's data.

    Args:
        filename (str): Name of the file that is to be read.
        sensname (str): Name of the supported sensor type.
        datatype (str): Data type from the sensor.

    Returns:
        pandas.DataFrame: DataFrame with the data read from the given file.
    """
    # Ensure the sensor and the data type are supported.
    assert dcfg.is_datatype_supported(sensname, datatype),\
        f"Sensor: {sensname!r}  and/or Data type: {datatype!r} not supported."
        
    # Choose the appropriate reader based on the sensor and data type.
    # Check to make sure that there is a reader available.
    _reader = dcfg.SUPPORTED_SENSORS[sensname][datatype]["reader"]
    return _reader(filename)

