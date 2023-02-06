"""
A private module for keeping track of the status of the analysis carried out
of the given data directory.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 04 Oct 2022
"""

import glob
import sys
import os
import json
import copy
import datetime
from datetime import timedelta as tdelta
from datetime import datetime as dt
from attrdict import AttrDict
import numpy as np
import pandas as pd

import dashconfig as dcfg
import dataio as dio

DEBUG = False

class BookKeeper(object):
    """Class to handle the bookkeeping operations to keep track of what files
    have been analyzed and where the summary files can be found.
    """
    # Basename linking string
    _bnlink: str = "_-_"

    @staticmethod
    def get_analysis_param_file_strings(aparams : AttrDict) -> list:
        return [f"sr{aparams.ulfuncinstsamprate:0.2f}",
                f"avg{aparams.avgwindur:0.2f}-{aparams.avgwinshift:0.2f}",
                [f"summ{_sd:04d}" for _sd in aparams.summarywin]]

    def __init__(self, datadir: str, dataparams: AttrDict,
                 analysisparams: AttrDict) -> None:
        self.datadir = datadir
        self.dataparams = dataparams
        self.analysisparams = analysisparams
        self._currsess = dt.now().strftime("%D %T")

        # Check if the bookkeeping file exists
        if os.path.exists(self.bkfile) is False:
            with open(self.bkfile, "w") as fh:
                json.dump({}, fh, indent=4)
            sys.stdout.write(f"\n Created {self.bkfile}.")

        # Initialize error messages.
        self._log = []

        # Check what all remains to be analysed.
        self._bkdata = {'filetimes': self._read_filetimes(),
                        'summary': {}}
        self.bookkeep()

        # Update bookkeeping file.
        self._update_bookkeping_file()

    @property
    def log(self):
        return self._log

    @property
    def bkfile(self):
        return f"{self.datadir}/{dcfg.OUTPUT_DIR}/bookkeeping.json"

    @property
    def bkdata(self):
        return self._bkdata

    def logerror(self, msg: str, errtype: dcfg.ERRORTYPES):
        self.log.append(
            f"[ERROR] [{type(self).__name__}] [{errtype}] {msg}"
        )

    def logwarning(self, msg: str, warntype: dcfg.WARNINGTYPES):
        self.log.append(
            f"[WARNING] [{type(self).__name__}] [{warntype}] {msg}"
        )

    def bookkeep(self):
        """Checks if all files on disk have been analysed.
        """
        _extn = dcfg.get_datafile_extn(self.dataparams.sensor,
                                       self.dataparams.data_type)
        # Go through all subjects in the datadir.
        _subjdirs = {
            _d.split("/")[-1]: _d
            for _d in glob.glob(f"{self.datadir}/*")
            if (os.path.isdir(_d) and dcfg.OUTPUT_DIR not in _d)
        }
        _n = len(_subjdirs)
        sys.stdout.write("\n > Bookeeping:")
        for _subj, _dir in _subjdirs.items():
            # Generate the details of things that have to be analyzed for this
            # subject.
            # 1. Generate the file detials for all the sensors.
            _locfiles = self._get_loc_file_details(_dir, _extn)

            # 2(a). Check for duplicate timestamps. Following this step and the
            # one below we know which files need to be considered for reading
            # data.
            _locfiles = self._update_duplicate_timestamp_files(_locfiles)
            # 2(b)Apply filter to remove files with duplicate timestamps.
            _locfiles = self._filter_out_duplicate_timestamp_files(_locfiles)

            # 3. Generate the list of files that should be present on disk.
            _exptdfiles = self._get_expected_files_on_disk(_subj, _dir, _locfiles)

            # Check if there is data to be processed, i.e. the disk is not what
            # is expected from the source files.
            _procfiles = self._get_files_to_be_processed(_exptdfiles)
            if _procfiles:
                self._bkdata['summary'][_subj] = _procfiles
            if DEBUG:
                break
        # Update bookkeeping 
        sys.stdout.write("\n > Bookeeping: Done")

    def _read_filetimes(self):
        # Read the current bookkeeping data.
        try:
            with open(self.bkfile, "r") as fh:
                return json.load(fh)['filetimes']
        except KeyError:
            return {}
    
    def _update_bookkeping_file(self):
        # Create a new dict without datetime objects.
        _newbkdata = {
            subj: {
                k.strftime("%D-%T") if k != 'summary' else k : v.copy()
                for k, v in data.items()
            }
            for subj, data in self.bkdata['summary'].items()
        }
        
        # Read the current bookkeeping data.
        with open(self.bkfile, "r") as fh:
            _filedata = json.load(fh)
        
        # Append new data
        _filedata['filetimes'] = self._bkdata['filetimes']
        if 'summary' not in _filedata:
            _filedata['summary'] = {}
        _filedata['summary'][self._currsess] = {
            'bkdetails': _newbkdata,
            'analysisparams': self.analysisparams,
        }
        
        # Write it back to disk
        with open(self.bkfile, "w") as fh:
            json.dump(_filedata, fh, indent=4)
        
        # with open(self.bkfile, "w") as fh:
        #     json.dump(self._bkdata['filetimes'], fh, indent=4)
    
    def _get_files_to_be_processed(self, exptdfiles: dict) -> dict:
        """Check if the expected files are on disk, if so, then return an empty
        dict, else return the full dict with the files that have to be 
        processed and created.
        
        Args:
            exptdfiles (dict): Dictionary of the files expected to be found on
            disk.

        Returns:
            dict: Details of the files to be processed.
        """
        procdict = {}
        # Go through the dates.
        for _date, _ddetails in exptdfiles.items():
            if _date == "summary":
                continue
            # Geneate the procdict detials.
            procdict[_date] = {_k: [_val, not os.path.exists(_val)]
                                    for _k, _val in _ddetails.items()
                                    if _k != 'src'}
            # Source file details are simply copied.
            procdict[_date]['src'] = copy.deepcopy(_ddetails['src'])
        # Summary files to be processed
        procdict['summary'] = {
            key: [[dfn, not os.path.exists(dfn)] for dfn in keyfiles]
            for key, keyfiles in exptdfiles["summary"].items()
        }
        return procdict
    
    def _get_expected_files_on_disk(self, subj: str, dir: str, locfiles: dict) -> dict:
        """Method to generate the list of files that should be found on the
        disk for the source files found for the patient.

        Args:
            subj (str): Name of the subject.
            dir (str): Directory with the soruce data for the subject.
            locfiles (dict): Dictionary containing the details of the files that
            are valid source files. 

        Returns:
            dict: A dictionary with the files that are expected fromeach valid source file.
        """
        # Generate strings for the analysis params
        _srstr, _avgstr, _summstr = BookKeeper.get_analysis_param_file_strings(self.analysisparams)
        _srstr = f"sr{self.analysisparams.ulfuncinstsamprate:0.2f}"
        _avgstr = f"avg{self.analysisparams.avgwindur:0.2f}-{self.analysisparams.avgwinshift:0.2f}"
        _summstr = [f"summ{_sd:04d}" for _sd in self.analysisparams.summarywin]
        
        # Get the dates of interest. This will include the earlist start date
        # and the oldest stop date across the different sensor locations.
        _tlims = np.array([_el[1:3] for _l, _lv in locfiles.items()
                           for _el in _lv if _el[4]])
        _strtdt = np.datetime64(
            dt.combine(to_datetime(np.min(_tlims[:, 0])).date(),
                       datetime.time(0, 0, 0))
        )
        _stopdt = np.datetime64(
            dt.combine(to_datetime(np.max(_tlims[:, 1])),
                       datetime.time(0, 0, 0))
        )
        # list all the data for the current file.
        _alldates = list(
            map(to_datetime, np.arange(_strtdt, _stopdt + np.timedelta64(1, 'D'), np.timedelta64(1, 'D')))
        )
        # _alldates = [dt.combine(_dt.date(), datetime.time(0, 0, 0))
        #              for _dt in _alldates]
        # Go through the date, and generate the associated source file(s), and
        # the expected processed files to be present on disk.
        exptd_files = {}
        for _date in _alldates:
            exptd_files[_date] = {"src": {}}
            
            # Generate the list of source files associated with this date.
            for _l, _lv in locfiles.items():
                exptd_files[_date]["src"][_l] = []
                # Go through the sensor location files.
                for _lvd in _lv:
                    # Check if this is an file to be included in the analysis.
                    if _lvd[4] is False:
                        continue
                    # Check if the file contains data from the current date.
                    if to_datetime(_lvd[1]).date() <= _date.date() <= to_datetime(_lvd[2]).date():
                        exptd_files[_date]["src"][_l].append(_lvd[0])
            
            # Generate the expected raw, ulfuncinst, and ulfuncavrg files.
            _basedir = f"{self.datadir}/{dcfg.OUTPUT_DIR}/{subj}/"
            # Rawfile
            exptd_files[_date]["raw"] = "_".join(
                (f"{_basedir}/raw/{subj}",
                f"{_date.strftime('%y-%m-%d')}",
                f"raw.{dcfg.PROC_FILE_EXTN}")
            )
            # Instantaneous ULfunc files.
            exptd_files[_date]["ulfuncinst"] = "_".join(
                (f"{_basedir}/ulfuncinst/{subj}",
                f"{_date.strftime('%y-%m-%d')}",
                _srstr,
                f"ulfuncinst.{dcfg.PROC_FILE_EXTN}")
            )
            # Average ULfunc files.
            exptd_files[_date]["ulfuncavrg"] = "_".join(
                (f"{_basedir}/ulfuncavrg/{subj}",
                _date.strftime('%y-%m-%d'),
                _srstr,
                _avgstr,
                f"ulfuncavrg.{dcfg.PROC_FILE_EXTN}")
            )
        # Add summary files.
        exptd_files["summary"] = {
            key: [
                "_".join((f"{_basedir}/summary/{subj}",
                            _srstr,
                            _avgstr,
                            _ss,
                            f"summary_{key}.{dcfg.PROC_FILE_EXTN}"))
                for _ss in _summstr
            ]
            for key in ('hq', 'rq', 'li')
        }
        return exptd_files
    
    def _update_duplicate_timestamp_files(self, locfiles):
        """Finds files with overlapping timestamps and marks the ones with
        the largest size to keep, and the rest to discard."""
        for _l, _lv in locfiles.items():
            _olinx = find_overlaping_timesegments([_el[1:] for _el in _lv])
            
            # Update the log.
            for i, _ol in enumerate(_olinx):
                locfiles[_l][i].append(_ol)

                if len(_ol) == 0:
                    continue
                
                # Get error message.
                _errmsg = ', '.join(
                    [f"{_lv[i][0]!r}"]
                    + [f"{_lv[_o][0]!r}" for _o in _ol]
                )
                self.logerror(
                    f"{_errmsg} have overlapping timestamps.",
                    errtype=dcfg.ERRORTYPES.DUPLICATE_TIMESTAMPS
                )
        return locfiles
    
    def _filter_out_duplicate_timestamp_files(self, locfiles):
        """Removes files with duplicate timestamps.
        """
        # Decide on which files to keep.
        # For now, the very first file is kept, the rest are removed.
        # TODO: We might need a more sophisticated approach to deciding 
        # which ones to keep. (2022-10-06 08:02:48)
        
        for _l, _lv in locfiles.items():
            # We will tentaively keep all files.
            for i, _ in enumerate(_lv):
                locfiles[_l][i].append(True)
                
            # Filter out files with duplicate timestamps, except for the first
            # such file.            
            for i, _el in enumerate(locfiles[_l]):
                if _el[4] is False:
                    # File is already marked to be ignored.
                    continue
                
                # _el[4] is True
                for j in _el[3]:
                    locfiles[_l][j][4] = False
                    
                    # Get error message.
                    self.logwarning(
                        f"{_el[j]!r} will not be processed!",
                        warntype=dcfg.WARNINGTYPES.IGNORING_FILE
                    )
        return locfiles
    
    def _get_loc_file_details(self, dir, extn):
        # Returns the details of of the different sensor data files at the
        # different locations.
        sys.stdout.write("\n")
        _locfiles = {_l:[] for _l in self.dataparams.locid}
        for _l in self.dataparams.locid:
            _lfiles = glob.glob(f"{dir}/*{_l}*.{extn}")
            # Get the start and end times for the sensors files.
            for _lf in _lfiles:
                sys.stdout.write(f"\r   - {_lf}")
                sys.stdout.flush()
                # Check if file exists in the filetime dict.
                if _lf not in self._bkdata['filetimes']:
                    # File time does not exist. Read file and update file time.
                    _data = dio.read_sensor_data(
                        _lf,
                        sensname=self.dataparams.sensor,
                        datatype=self.dataparams.data_type
                    )
                    self._bkdata['filetimes'][_lf] = [
                        to_datetime(_data['TimeStamp'].values[0]).strftime("%Y-%m-%d %H:%M:%S.%f"),
                        to_datetime(_data['TimeStamp'].values[-1]).strftime("%Y-%m-%d %H:%M:%S.%f")
                    ]
                # Get the start and end timestamps.
                _locfiles[_l].append([
                    _lf, pd.to_datetime(self._bkdata['filetimes'][_lf][0], format="%Y-%m-%d %H:%M:%S.%f").to_numpy(),
                    pd.to_datetime(self._bkdata['filetimes'][_lf][1], format="%Y-%m-%d %H:%M:%S.%f").to_numpy()
                ])
        return _locfiles


def find_overlaping_timesegments(tsegs: list[list[np.datetime64]]) -> list[list[int]]:
    """Retuns a list of list indicating which of the given time segments have
    an overlap. The input time segments are lists of list of numpy datetime64s.
    Eacn inner list has two timestamps, the start and end times of each segment. 

    Args:
        tsegs (list[list[np.datetime64]]): List of time segment. Each
        element of the list if an list with two np.datetime64s. This inner
        list provides the start and stop times of a time segment.

    Returns:
        list[list[int]]: Returns the list of list of integers that provides the
        indices of the input list with which any particular time segment
        overlaps.
    """
    assert np.all([len(_el) == 2 for _el in tsegs]),\
        "The input list's elements must be lists of length two."
    assert np.all([_el[0] <= _el[1] for _el in tsegs]),\
        "The start time of each time segments must be less than or equal to the stop time." 
    olap_inx = []
    for i, _ti in enumerate(tsegs):
        olap_inx.append([])
        for j, _tj in enumerate(tsegs[i+1:]):
            # Check of the jth time sgment overlaps with the ith timesegment.
            if (_ti[0] <= _tj[0] <= _ti[1]) or ((_ti[0] <= _tj[1] <= _ti[1])):
                olap_inx[-1].append(i + j + 1)
    return olap_inx


def to_datetime(date):
    """
    Converts a numpy datetime64 object to a python datetime object 
    Input:
      date - a np.datetime64 object
    Output:
      DATE - a python datetime object
    """
    timestamp = ((date - np.datetime64('1970-01-01T00:00:00'))
                 / np.timedelta64(1, 's'))
    return dt.utcfromtimestamp(timestamp)