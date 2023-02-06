"""Module for processing ARIMU data.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 04 Feb 2023
"""

import sys
import glob
import struct
import json
import os
import re
import pandas as pd
import attrdict
from enum import Enum
from datetime import datetime as dt
from datetime import timedelta as tdelta

import numpy as np


class ARIMUCONFIG(object):
    S_ACCL = 16384
    S_GYRO = 131
    # Params.
    BINFILEFMTPARAMS = attrdict.AttrDict({
        'rowsz': 7 + 12,
        'rowfmt': ("<2L", "<6h")
    })


def read_arimu_data_file(fname, params=ARIMUCONFIG.BINFILEFMTPARAMS):
    """Function to read the raw ARIMU binary data from a sensor.

    Parameters
    ----------
    fname : str
        Full address of the file to read.
    params : _type_
        Format details of the binary data file.

    Returns
    -------
    attrdict.AttrDict
        AttrDict object with the details of the file: contains details from the 
        header, and the IMU data.
    """
    # Read binary data file and decode information
    with open(fname, "rb") as fh:
        bindata = bytearray(fh.read())
    
    data = attrdict.AttrDict()

    # Device name
    _inx = bindata.index(b',')
    data.devname = bindata[:_inx].decode()

    # Remove the bytes.
    del bindata[:_inx+1]

    # Subject name
    _inx = bindata.index(b',')
    data.subjname = bindata[:_inx].decode()

    # Remove the bytes.
    del bindata[:_inx+1]

    # Read start time and micros data
    _dtval = struct.unpack('<7L', bindata[:28])
    data.dstrt = dt(_dtval[0], _dtval[1], _dtval[2], _dtval[3],
                    _dtval[4], _dtval[5], _dtval[6])
    del bindata[:28]
    data.microstrt = struct.unpack('<L', bindata[:4])[0]
    del bindata[:4]

    # Check if the footer bytes are present.
    if (len(bindata) - 4) % params.rowsz == 0:
        # Get the last four bytes to get the file closing time
        data.microstp = struct.unpack("<L", bindata[-4:])[0]
        del bindata[-4:]


    # Parse data rows.
    N = len(bindata)
    data.imu = np.empty((N // params.rowsz, 7), dtype=object)
    for i in range(0, N, params.rowsz):
        _i = i // params.rowsz
        # Check this is not a row of all zeros.
        _temp = struct.unpack("<7B", bindata[i:i+7])
        _ts = (f'{_temp[0]:02d}-{_temp[1]:02d}-{_temp[2]:02d}'
               + f'T{_temp[3]}:{_temp[4]}:{_temp[5]}.{_temp[6]:02d}')
        _currdt = dt.strptime(_ts, '%y-%m-%dT%H:%M:%S.%f')
        data.imu[_i, :] = [_currdt,
                           *struct.unpack("<6h", bindata[i+7:i+19])]
    return data


def interpolate_raw_arimu_data(rawdata):
    """Interpolate raw data from the arimu device at 100Hz.

    Parameters
    ----------
    rawdata : AttrDict
        AttrDict object obtained from calling the read_arimu_data_file function.

    Returns
    -------
    np.array
        A 2D numpy array with the interpolated data.
    """
    _inxold = [int(_tv.seconds * 100 + _tv.microseconds / 1e4)
               for _tv in (rawdata.imu[:, 0] - rawdata.imu[0, 0])]
    _inxnew = np.arange(0, _inxold[-1] + 1)
    _ynew = np.array([np.interp(_inxnew, _inxold, rawdata.imu[:, i].astype(float))
                    for i in range(1, rawdata.imu.shape[1])]).T
    t_new = np.arange(rawdata.imu[0, 0], rawdata.imu[-1, 0] + tdelta(seconds=0.01),
                    tdelta(seconds=0.01))
    return np.hstack((np.array([t_new]).T, _ynew.astype(object)))


def generate_dataframe(interped_data,
                       df_cols=('datetime', 'ax', 'ay', 'az', 'gx', 'gy', 'gz'),
                       s_accl=ARIMUCONFIG.S_ACCL,
                       s_gyro=ARIMUCONFIG.S_GYRO):
    """Generate a pandas dataframe from the interpolated data."""
    _df = pd.DataFrame(interped_data, columns=df_cols)
    _df[['ax', 'ay', 'az', 'gx', 'gy', 'gz']] = _df[['ax', 'ay', 'az', 'gx', 'gy', 'gz']].astype(float)
    # Convert to g and deg/sec units
    _df['ax'] /= s_accl
    _df['ay'] /= s_accl
    _df['az'] /= s_accl
    _df['gx'] /= s_gyro
    _df['gy'] /= s_gyro
    _df['gz'] /= s_gyro
    return _df