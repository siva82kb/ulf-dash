"""
Script that processes all data in the given data folder. This script can be
called whenever there is data to be processed. This will only process files that 
have not been processed before. 

If there are files that the user wants re-analysed then they can simply delete 
the previoulsy analyzed files. This automaticaly make this script re-process the 
missing processed files.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 26 Oct 2022
"""

import os
import glob
import sys
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
from attrdict import AttrDict

import arimulib
import dashconfig as dcfg
import bookkeeping as bk
import preprocess
import dashsupport


def _is_sumary_to_be_generated(subjdata: str) -> bool:
    """Checks if any of the summary files are to be geneated.

    Parameters
    ----------
    subjdata : str
        Bookkeeping dict for a subject from the BookKeeper class.

    Returns
    -------
    bool
        Whether or not any summary files are to be generated. True if even one 
        file is to be generated.
    """
    _gensummfile = False
    for _fdetails in subjdata['summary']['hq']:
        _gensummfile = _gensummfile or _fdetails[1]
    for _fdetails in subjdata['summary']['rq']:
        _gensummfile = _gensummfile or _fdetails[1]
    for _fdetails in subjdata['summary']['li']:
        _gensummfile = _gensummfile or _fdetails[1]
    return _gensummfile


def preprocess_arimu_binaryfiles(datadir: str):
    """Precprocess the ARIMU raw binary files in the given data directory.

    Parameters
    ----------
    datadir : str
        Full path of the directory containing the files to be processed.
    """
    def get_csv_fname(_f):
        return f"{datadir}/{_sval}/" + _f.split(os.sep)[-1].split('.bin')[0] + '.csv'
    
    sys.stdout.write("\n > Precprocessing ARIMU binary files...")
    # Get all subjects in the data directory.
    _subjs = {_d.split(os.sep)[-1]: _d for _d in glob.glob(f"{datadir}/*")
              if os.path.isdir(_d) and _d != f"{datadir}/_output"}
    sys.stdout.write(f" {len(_subjs)} subject found.")
    
    # Go through the subjects and generating the missing processed files.
    for _sinx, _sval in enumerate(_subjs.keys()):
        sys.stdout.write(f"\n   - [{_sinx+1:3d} / {len(_subjs):3d}] {_sval}")
        # Get the list of files that need to be processed.
        _rawdir = f"{datadir}/{_sval}/rawdata/"
        _files = [
            _f for _f in glob.glob(f"{_rawdir}/*{_sval}*.bin")
            if not os.path.isfile(get_csv_fname(_f))
        ]
        for _finx, _fval in enumerate(_files):
            sys.stdout.write(f"\r   - [{_sinx+1:3d} / {len(_subjs):3d}] {_sval} [{_finx+1:3d} / {len(_files):3d}] {_fval.split(os.sep)[-1]}     ")
            # Read the file.
            _data = arimulib.read_arimu_data_file(_fval)
            # Interpolate
            intrpd_data = arimulib.interpolate_raw_arimu_data(_data)
            # Create interpolate dataframe and save it.
            alldata_df = arimulib.generate_dataframe(intrpd_data)
            # Save fiile.
            with open(get_csv_fname(_fval), 'w') as _fh:
                _prehdrstr = ' | '.join((f"# Device Name: {_data.devname}",
                                         f"Subject Name: {_data.subjname}",
                                         f"Data Start Time: {_data.dstrt.strftime('%Y-%m-%d %H:%M:%S.%f')}"))
                _fh.write(_prehdrstr + "\n")
                _fh.write(alldata_df.to_csv(index=False, header=True))


def display_datatype_summary(data_params: AttrDict):
    # Check if the sensor and data types are supported.
    _dispstr = [" > Data Analysis Details"]
    if dcfg.is_sensor_supported(data_params.sensor) is False:
        sys.stdout.write(f"\n Error! '{data_params.sensor}' is not supported. Nothing to analyze.")
        sys.stdout.write("\n Goodbye.")
        return
    else:
        _dispstr += [f"Sensor: {data_params.sensor}"]
    
    # Check if the datatype for the sensor is supported.
    if dcfg.is_datatype_supported(data_params.sensor, data_params.data_type) is False:
        sys.stdout.write(f"\n Error! '{data_params.data_type}' for '{data_params.sensor}' is not supported. Nothing to analyze.")
        sys.stdout.write("\n Goodbye.")
        return
    else:
        _dispstr += [f"Data type: {data_params.data_type}"]
    
    # Check of the listed sensor locations are supported.
    if dcfg.is_sensor_locs_supported(data_params.locs) is False:
        sys.stdout.write(f"\n Error! '{data_params.locs}'is not supported. Nothing to analyze.")
        sys.stdout.write("\n Goodbye.")
        return
    else:
        _dispstr += [f"Sensor locations: {data_params.locs}"]
    
    # Display string
    sys.stdout.write("\n   - ".join(_dispstr))


def processalldata(datadir: str):
    """Function to process all un-processed data in the given data folder.

    Parameters
    ----------
    datadir : str
        Full path (realtive or absolute) of the data directory.
    """
    # Check if the given directory is a valid data directory.
    if dashsupport.is_valid_data_directory(datadir) is False:
        sys.stdout.write(" Nothing to analyse.")
        sys.stdout.write("\n Goodbye!")
        return
    
    # Read Data, Analysis, and Measures params files.
    data_params = dcfg.read_data_params(f"{datadir}/data_params.json")
    analysis_params = dcfg.read_analysis_params(f"{datadir}/analysis_params.json",
                                                data_params)
    measures_params = dcfg.read_measures_params(f"{datadir}/measures_params.json",)
    
    # Display data type summar.y
    display_datatype_summary(data_params)
    
    # Right and Left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[data_params.sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[data_params.sensor]['Left Wrist']
    
    # Preprocess ARIMU files.
    if data_params['sensor'] == 'ARIMU':
        # Read, interpolate and save raw ARIMU data.
        preprocess_arimu_binaryfiles(datadir)
    
    # Do bookkeeping first to see what has been already processed and what has
    # not been yet.
    _bk = bk.BookKeeper(datadir, data_params, analysis_params)
    
    # Go through the bookkeeping data process that files that need to be
    # processed.
    sys.stdout.write("\n > Processing data:")
    n_subj = len(_bk.bkdata.keys())
    for i, (subj, subjdata) in enumerate(_bk.bkdata['summary'].items()):
        # Go through the individual dates and process them.
        # Generate raw data
        sys.stdout.write(f"\n   - [{i:3d}/{n_subj:3d}] {subj:<4}: Raw ")
        for _date in subjdata:
            if _date == "summary":
                continue
            if subjdata[_date]['raw'][1] is False:
                continue
            sys.stdout.write(f" {_date.strftime('%D')}")
            sys.stdout.flush()
            preprocess.generate_save_raw_dayfile(
                _date,
                subjdata[_date]['src'],
                subjdata[_date]['raw'][0],
                data_params,
                analysis_params
            )
            
        # Generate ULFUNC inst data
        sys.stdout.write(f"\n   - [{i:3d}/{n_subj:3d}] {subj:<4}: Ulfunc Inst. ")
        for _date in subjdata:
            if _date == "summary":
                continue
            if subjdata[_date]['ulfuncinst'][1] is False:
                continue
            sys.stdout.write(f" {_date.strftime('%D')}")
            sys.stdout.flush()
            preprocess.generate_save_ulfuncinst_dayfile(
                subjdata[_date]['raw'][0],
                subjdata[_date]['ulfuncinst'][0],    
                data_params,
                analysis_params,
                measures_params
            )
        
        # Generate ULFUNC average data
        sys.stdout.write(f"\n   - [{i:3d}/{n_subj:3d}] {subj:<4}: Ulfunc Avrg. ")
        for _date in subjdata:
            if _date == "summary":
                continue
            if subjdata[_date]['ulfuncavrg'][1] is False:
                continue
            sys.stdout.write(f" {_date.strftime('%D')}")
            sys.stdout.flush()
            preprocess.generate_save_ulfuncavrg_dayfile(
                subjdata[_date]['raw'][0],
                subjdata[_date]['ulfuncinst'][0],    
                subjdata[_date]['ulfuncavrg'][0],    
                data_params,
                analysis_params
            )
        
        # Generate ULFUNC summary data.    
        # Check if any summary is to be generated.
        if _is_sumary_to_be_generated(subjdata):    
            sys.stdout.write(f"\n   - [{i:3d}/{n_subj:3d}] {subj:<4}: Summary")
            preprocess.generate_save_ulfunc_summary(
                subjdata,
                data_params,
                analysis_params,
                domnaff=rlbl,
                ndomaff=llbl
            )
    sys.stdout.write("\n > Processing done.\n")


if __name__ == '__main__':
    # The second system argument is the data folder
    datadir = sys.argv[1]
    
    # Call the processing function.
    processalldata(datadir)