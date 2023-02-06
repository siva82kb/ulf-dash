"""
A module implementing all the preprocessing functionalities required for
extracting useful UL functioning information from the raw data. The goal here
is to implement all the steps that will make the next step - UL functioning
construct - quantification relatively easy.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 06 Oct 2022
"""

import os
import sys
import re
import pathlib
import datetime
from datetime import datetime as dt
from datetime import timedelta as tdelta
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from attrdict import AttrDict
import pyarrow.feather as feather
from monalysa import ulfunc
import _test

import dashconfig as dcfg
import dataio
import bookkeeping
from bookkeeping import to_datetime

from tempsupport import grav_sub_mag


def generate_save_raw_dayfile(day:datetime.date,
                              srcfile: list[str],
                              rawfilename: str,
                              dataparams: AttrDict,
                              analysisparams: AttrDict) -> None:
    """Function to generate and save to disk the raw day file from the given 
    source files. The file will be stored in the HDF5 with heirarchical indexing
    for the different sensors. The time stamps will be common across the
    different sensors.


    Args:
        day (datetime.date): The day for which the rawfile is to be generated.
        srcfile (list[str]): List of source file that contain data for the
        give date.
        rawfilename (str): Name of the rawfile that is to be saved.
        dataparams (AttrDict): An AttrDict that contains the details of the 
        data being analysed.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.
    """
    # Generate the timestamps for the day.
    # Ensure that the start time of day is 00:00:00.
    day = dt.combine(day.date(), datetime.time(0, 0, 0))
    _dayts = np.arange(day, day + tdelta(days=1),
                       tdelta(seconds=analysisparams['samptr']['raw'][0]))
    # Read the individual source files for each location.
    locdata = {}
    for loc, locsrcfiles in srcfile.items():
        daydf = pd.DataFrame.from_dict({
            "TimeStamp": list(map(bookkeeping.to_datetime, _dayts))
        }).set_index('TimeStamp')
        print(locsrcfiles)
        for srcfl in locsrcfiles:
            # Read the source file.
            data = dataio.read_sensor_data(srcfl, sensname=dataparams.sensor,
                                           datatype=dataparams.data_type)
            # Select only data for the day.
            _daydata = data[data['Date'] == day.date()].set_index('TimeStamp')
            if daydf.shape[1] == 0:
                daydf = daydf.join(other=_daydata, on="TimeStamp", how="left")
            else:
                daydf.loc[daydf.index.isin(_daydata.index), :] = _daydata
        # daydf = daydf.reset_index()
        daydf.drop(labels=['Date', 'Time'], axis='columns', inplace=True)
        # Remove ActiGraph columns of no interest.
        try:
            # Try to remove
            daydf.drop(labels=['Steps', 'Lux'], axis='columns', inplace=True)
        except KeyError:
            pass
        daydf.drop(labels=[_c for _c in daydf.columns
                           if 'Inclinometer' in _c],
                   axis='columns', inplace=True)
        locdata[loc] = daydf
    
    # Save the multi-column-index dataframe
    rawdf = pd.concat(locdata, axis=1).reset_index()
    # Write data to disk.
    pathlib.Path(os.sep.join(rawfilename.split(os.sep)[:-1])).mkdir(parents=True, exist_ok=True)
    feather.write_feather(rawdf, rawfilename)
    rawdf.to_csv(f"{rawfilename.split('.aipc')[0]}.csv")
    # sys.stdout.write(f" [Generated {rawfilename}]")


def generate_save_ulfuncinst_dayfile(rawfilename: str,
                                     ulfuncinstfilename: str,
                                     dataparams: AttrDict,
                                     analysisparams: AttrDict,
                                     measuresparams: AttrDict) -> None:
    """Function to the generate the different instantaneous UL functioning
    constructs from the raw data file. This function must be called only after
    the raw data files have been generated.

    Args:
        rawfilename (str): Name of the raw data file.
        ulfuncinstfilename (str): Name of the file to which the ulfunc
        instantaneous constrcuts are to be saved.
        dataparams (AttrDict): An AttrDict that contains the details of the 
        population parameters i.e., the details of the data being analysed.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.
        measuresparams (AttrDict): An AttrDict that contains the details of the 
        parameters to be used with the different measures for computing the 
        different constructs.
    """
    # Make sure the raw file exists.
    if not os.path.exists(rawfilename):
        sys.stdout.write(f"\n  Error! {rawfilename} not found!")
        return

    # Read and process the raw file to get ULFUNC constructs.
    rawdf = feather.read_feather(rawfilename)
    locdfdict = {}
    for loc in rawdf.columns.levels[0]:
        if loc == 'TimeStamp':
            continue
        # Compute the ulfunc instantaneous constructs for the different sensors.
        _locdf = rawdf[loc].copy()
        _locdf['TimeStamp'] = rawdf['TimeStamp']
        locdfdict[loc] = compute_ulfuncinst_measures(_locdf,
                                                     dataparams,
                                                     analysisparams,
                                                     measuresparams[loc]['use'])

    # Waist filtering if waist sensor is available.
    if 'W' in rawdf.columns.levels[0]:
        # Get the wait dataframe.
        _waistdf = rawdf['W'].copy()
        _nowaistmove = 1.0 * (_waistdf['Vector Magnitude'] == 0).values
        _nowaistmove[np.isnan(_waistdf['Vector Magnitude'].values)] = np.NaN
        for loc in locdfdict.keys():
            if loc == 'TimeStamp' or loc == 'W':
                continue
            # Go through the use columns
            for _col in locdfdict[loc]['use'].columns:
                locdfdict[loc]['use', f"{_col}_wf"] = (locdfdict[loc]['use'][_col].values
                                                      * _nowaistmove)
                locdfdict[loc] = locdfdict[loc].sort_index(axis=1)
            # Go through the int columns
            for _col in locdfdict[loc]['int'].columns:
                locdfdict[loc]['int', f"{_col}_wf"] = (locdfdict[loc]['int'][_col].values
                                                      * _nowaistmove)
                locdfdict[loc] = locdfdict[loc].sort_index(axis=1)

    # Compute instantaneous laterality index.
    locdfdict['LatIndex'] = compute_inst_laterality_index(locdfdict, dataparams, analysisparams)

    # Combine the instantaneous measures to a single dataframe.
    ulfuncinstdf = pd.concat(locdfdict, axis=1).reset_index()

    # Save the ulfuc instantaneous file.
    _filepath = os.sep.join(ulfuncinstfilename.split(os.sep)[:-1])
    pathlib.Path(_filepath).mkdir(parents=True, exist_ok=True)
    feather.write_feather(ulfuncinstdf, ulfuncinstfilename)
    ulfuncinstdf.to_csv(f"{ulfuncinstfilename.split('.aipc')[0]}.csv")


def generate_save_ulfuncavrg_dayfile(rawfilename: str,
                                     ulfuncinstfilename: str,
                                     ulfuncavrgfilename: str,
                                     dataparams: AttrDict,
                                     analysisparams: AttrDict) -> None:
    """Function to the generate the different average UL functioning
    constructs from the raw and ulfunc pd.DataFrametantaneous day files. This function
    must be called only after the raw and the A dataframe with the columns contianing the laterality index computed from the different use and intensity signals.  data files
    have been generated.
    lidf = pd.DataFrame()

    # Go through the use columns first and compute the instantaneous laterality 
    # index for each of them.
    
    return lidf
        rawfilename (str): Name of the raw data file.
        ulfuncinstfilename (str): Name of the ulfunc instantaneous file.
        ulfuncavrgfilename (str): Name of the file to which the ulfunc
        average constrcuts are to be saved.
        dataparams (AttrDict): An AttrDict that contains the details of the 
        population parameters i.e., the details of the data being analysed.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.
    """
    # Make sure the raw file exists.
    if not os.path.exists(rawfilename):
        sys.stdout.write(f"\n  Error! {rawfilename} not found!")
        return

    # Make sure the ulfuc instantaneous file exists.
    if not os.path.exists(ulfuncinstfilename):
        sys.stdout.write(f"\n  Error! {ulfuncinstfilename} not found!")
        return

    # Read and process the raw file to get ULFUNC constructs.
    rawdf = feather.read_feather(rawfilename)
    ulfuncinstdf = feather.read_feather(ulfuncinstfilename)
    locdfdict = {}
    for loc in rawdf.columns.levels[0]:
        if loc == 'TimeStamp' or loc == 'LatIndex':
            continue

        # Preare the raw and ulfuncinst dfs.
        _locrawdf = rawdf[loc].copy()
        _locrawdf['TimeStamp'] = rawdf['TimeStamp']
        _loculfuncinstdf = ulfuncinstdf[loc].copy()
        _loculfuncinstdf['TimeStamp'] = ulfuncinstdf['TimeStamp']

        # Compute the ulfunc average constructs for the different sensors.
        locdfdict[loc] = compute_ulfuncavrg_measures(_locrawdf,
                                                     _loculfuncinstdf,
                                                     analysisparams)

    # Compute average of the instantaneous laterality index.
    _loculfuncinstdf = ulfuncinstdf['LatIndex'].copy()
    _loculfuncinstdf['TimeStamp'] = ulfuncinstdf['TimeStamp']
    locdfdict['LatIndex'] = compute_avrg_of_laterality_index(_loculfuncinstdf,
                                                             analysisparams)
    locdfdict['LatIndexoA'] = compute_laterality_index_of_avrg(locdfdict,
                                                               dataparams,
                                                               analysisparams)
    # Combine into a single average dataframe.
    ulfuncavrgdf = pd.concat(locdfdict, axis=1).reset_index()
    # Save the ulfuc instantaneous file.
    # Write data to disk.
    _filepath = os.sep.join(ulfuncavrgfilename.split(os.sep)[:-1])
    pathlib.Path(_filepath).mkdir(parents=True, exist_ok=True)
    feather.write_feather(ulfuncavrgdf, ulfuncavrgfilename)
    ulfuncavrgdf.to_csv(f"{ulfuncavrgfilename.split('.aipc')[0]}.csv")
    # sys.stdout.write(f" [Generated {ulfuncavrgfilename}]")


def generate_save_ulfunc_summary(bkdata: dict,
                                 dataparams: AttrDict,
                                 analysisparams: AttrDict,
                                 domnaff: str,
                                 ndomaff: str) -> None:
    """Function to the generate the summary measures from the ulfunc average
    constructs. This function must be called only after the ulfunc average
    measures have been computed.

    Args:
        bkdata (dict): Book keeping dictionary data.
        dataparams (AttrDict): An AttrDict that contains the details of the 
        population parameters i.e., the details of the data being analysed.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.
        domnaff (str): Name of the sensor corresponding to the dominant or the
        non-affected upper limb.
        ndomaff (str): Name of the sensor corresponding to the non-dominant or
        the affected upper limb. 
    Returns:
        None
    """
    alldates = [dt.combine(k.date(), datetime.time(0, 0, 0))
                for k in bkdata.keys() if k != 'summary']
    
    # Make sure all the ulfunc average files are available.
    if np.all([os.path.exists(bkdata[_date]["ulfuncavrg"][0])
               for _date in alldates]) is False:
        sys.stdout.write("\n  Error! Not all ULFUNC average files were found!")
        return
    # Start nad Stop times.
    start_ts = alldates[0]
    stop_ts = alldates[-1] + tdelta(days=1)

    # Generate and save Hq summary files.
    _gen_save_hq_summary(bkdata, domnaff, ndomaff, alldates, start_ts, stop_ts)
    
    # Generate and save Rq summary files.
    _gen_save_rq_summary(bkdata, domnaff, ndomaff, alldates, start_ts, stop_ts)
    
    # Generate and save Laterality Index summary files.
    _gen_save_laterality_index_summary(bkdata, alldates, analysisparams)


def compute_ulfuncinst_measures(rawdf: pd.DataFrame, dataparams: AttrDict,
                                analysisparams: AttrDict,
                                measuresparams: dict) -> pd.DataFrame:
    """Computes the different instantaneous UL functioning constructs of
    interest from the  given raw data dataframe. The exact measures that are
    computed will depend on the  sensor and the data type.

    Args:
        rawdf (pd.DataFrame): Dataframe containing the containig the raw data.
        dataparams (AttrDict): An AttrDict that contains the details of the 
        population parameters i.e., the details of the data being analysed.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.
        measuresparams (dict): An dictionary with the parameters for the 
        different UL use measures.

    Returns:
        pd.DataFrame: Dataframe with the computed instantaneous UL functioning
        measures.
    """
    stime, _, sratio = analysisparams["samptr"]["ulfuncinst"]
    # Generate the combined dataframe.
    ulfuncts = np.arange(
        rawdf['TimeStamp'].iloc[0],
        rawdf['TimeStamp'].iloc[-1] + tdelta(seconds=stime),
        tdelta(seconds=stime)
    )
    ulfuncts = np.array([
        _ts for _ts in ulfuncts
        if to_datetime(_ts).date() == to_datetime(ulfuncts[0]).date()
    ])
    # UL use measures
    _uluse_funcs = {
        "ActiGraphGt3x": {
            "Raw Data": actigraph_raw_uluse,
            "Vector Magnitude": actigraph_vecmag_uluse,
        },
        "ARIMU": {
            "Raw Data": arimu_raw_uluse,
        }
    }
    _ulusefunc = _uluse_funcs[dataparams.sensor][dataparams.data_type]
    _ulusedf = _ulusefunc(rawdf, measuresparams)
    _ulusedf['TimeStamp'] = ulfuncts

    # UL intensity measures
    _ulint_funcs = {
        "ActiGraphGt3x": {
            "Raw Data": actigraph_raw_ulint,
            "Vector Magnitude": actigraph_vecmag_ulint,
        },
        "ARIMU": {
            "Raw Data": arimu_raw_ulint,
        }
    }
    _ulintfunc = _ulint_funcs[dataparams.sensor][dataparams.data_type]
    _ulintdf = _ulintfunc(rawdf, _ulusedf, sratio, measuresparams)
    _ulintdf['TimeStamp'] = ulfuncts
    return pd.concat({'use': _ulusedf.set_index('TimeStamp'),
                      'int': _ulintdf.set_index('TimeStamp')},
                     axis=1)


def compute_inst_laterality_index(locdfdict: dict, dataparams: AttrDict,
                                  analysisparams: AttrDict) -> pd.DataFrame:
    """Computes the instantaneous UL laterality index from the different instantaneous use and intensity measures from the two upper-limbs.

    Parameters
    ----------
    locdfdict : dict
        Dictionary with the dataframes from the different sensor locations. These dataframes contain the instantaneous use and intensity signals.
    dataparams : AttrDict
        An AttrDict that contains the details of the population parameters i.e., the details of the data being analysed.
    analysisparams : AttrDict
        An AttrDict that contains the details of the analysis parameters to be used for computing the different constructs and the summary variables.

    Returns
    -------
    pd.DataFrame
        A dataframe with the columns contianing the laterality index computed from the different use and intensity signals.  
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[dataparams.sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[dataparams.sensor]['Left Wrist']
    
    _uselidf = pd.DataFrame()
    _intlidf = pd.DataFrame()
    # Go through the use columns first and compute the instantaneous laterality 
    # index for each of them.
    for _col in locdfdict[rlbl]['use'].columns:
        _, _uselidf[f'{_col}'] = _test.instantaneous_latindex(
            domnaff=locdfdict[rlbl]['use'][_col].values,
            ndomaff=locdfdict[llbl]['use'][_col].values
        )
    _uselidf['TimeStamp'] = locdfdict[rlbl].index
    # Go through the int columns first and compute the instantaneous laterality 
    # index for each of them.
    for _col in locdfdict[rlbl]['int'].columns:
        _, _intlidf[f'{_col}'] = _test.instantaneous_latindex(
            domnaff=locdfdict[rlbl]['int'][_col].values,
            ndomaff=locdfdict[llbl]['int'][_col].values
        )
    _intlidf['TimeStamp'] = locdfdict[rlbl].index
    return pd.concat({'use': _uselidf.set_index('TimeStamp'),
                      'int': _intlidf.set_index('TimeStamp')}, axis=1)


def compute_ulfuncavrg_measures(rawdf: pd.DataFrame,
                                ulfuncinstdf: pd.DataFrame,
                                analysisparams: AttrDict) -> pd.DataFrame:
    """Computes the different average UL functioning constructs of interest
    from the given raw data dataframe. The exact measures thata re computed
    will depend on the  sensor and the data type.

    Args:
        rawdf (pd.DataFrame): Dataframe containing the containig the raw data.
        ulfuncinstdf (pd.DataFrame): Dataframe containing the instantaneous 
        ulfunc data.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.

    Returns:
        pd.DataFrame: Dataframe with the computed average UL functioning measures.
    """
    _ulfits = ulfuncinstdf['TimeStamp'].copy().values

    # Get the use and intensity columns
    _usecols = list(ulfuncinstdf['use'].columns)
    # _intcols = list(ulfuncinstdf['int'].columns)

    # Use Average
    _useavrgdf = pd.DataFrame()
    for colname, colval in ulfuncinstdf['use'].iteritems():
        # Get the avarage use signal.
        _inx, _auu = ulfunc.uluse.average_uluse(
            usesig=colval.values,
            windur=analysisparams['avgwindur'],
            winshift=analysisparams['avgwinshift'],
            sample_t=analysisparams["samptr"]['raw'][0]
        )
        _useavrgdf[colname] = _auu

    # Intensity Average
    _intavrgdf = pd.DataFrame()
    for colname, colval in ulfuncinstdf['int'].iteritems():
        # Get the avarage use signal.
        _ucol = _get_usecol_for_intcol(colname, _usecols)
        if _ucol is None:
            sys.stdout.write(f"\n  Weird! The use column for the incol (={colname}) was not found.")
            continue
        _inx, _aiu = ulfunc.ulint.average_intuse(
            intsig=colval.values,
            usesig=ulfuncinstdf['use'][_ucol].values,
            windur=analysisparams['avgwindur'],
            winshift=analysisparams['avgwinshift'],
            sample_t=analysisparams["samptr"]['raw'][0]
        )
        _intavrgdf[colname] = _aiu

    # Activity average. Computed by multiplying the appropriate avarage use and
    # intensity columns.
    _actavrgdf = pd.DataFrame()
    for _uc in _useavrgdf:
        for _ic in _intavrgdf:
            # Check the use column is int he intensity column.
            _cond1 = _uc in _ic
            _cond2 = '_wf' in _uc and '_wf' in _ic
            _cond3 = '_wf' not in _uc and '_wf' not in _ic
            if _cond1 and (_cond2 or _cond3):
                # Compute the average upper limb activity.
                _actavrgdf[f'{_uc}*{_ic}'] = _useavrgdf[_uc] * _intavrgdf[_ic]

    # Add timestamps.
    _useavrgdf['TimeStamp'] = _ulfits[_inx]
    _intavrgdf['TimeStamp'] = _ulfits[_inx]
    _actavrgdf['TimeStamp'] = _ulfits[_inx]
    return pd.concat({'use': _useavrgdf.set_index('TimeStamp'),
                      'int': _intavrgdf.set_index('TimeStamp'),
                      'act': _actavrgdf.set_index('TimeStamp')
                      }, axis=1)


def compute_avrg_of_laterality_index(latinxinstdf: pd.DataFrame,
                                     analysisparams: AttrDict) -> pd.DataFrame:
    """Computes the average laterality index from the different instantaneous 
    laterality index measures.

    Args:
        latinxinstdf (pd.DataFrame): Dataframe containing the instantaneous 
        laterality index from use and intensity signals.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.

    Returns:
        pd.DataFrame: Dataframe with the computed average laterality index.
    """
    _ulfits = latinxinstdf['TimeStamp'].copy().values

    # Go through the use columns first and compute the average laterality 
    # index for each of them.
    _uselidf = pd.DataFrame()
    for _colname, _colval in latinxinstdf['use'].iteritems():
        _inx, _ali = _test.average_latindex(_colval.values,
                                            windur=analysisparams['avgwindur'],
                                            winshift=analysisparams['avgwinshift'],
                                            sample_t=analysisparams["samptr"]['raw'][0])
        _uselidf[_colname] = _ali

    # Go through the int columns first and compute the average laterality 
    # index for each of them.
    _intlidf = pd.DataFrame()
    for _colname, _colval in latinxinstdf['int'].iteritems():
        _inx, _ali = _test.average_latindex(_colval.values,
                                            windur=analysisparams['avgwindur'],
                                            winshift=analysisparams['avgwinshift'],
                                            sample_t=analysisparams["samptr"]['raw'][0])
        _intlidf[_colname] = _ali

    # Add timestamps.
    _uselidf['TimeStamp'] = _ulfits[_inx]
    _intlidf['TimeStamp'] = _ulfits[_inx]
    return pd.concat({'use': _uselidf.set_index('TimeStamp'),
                      'int': _intlidf.set_index('TimeStamp'),
                      }, axis=1)


def compute_laterality_index_of_avrg(locdfdict: pd.DataFrame,
                                     dataparams: AttrDict,
                                     analysisparams: AttrDict) -> pd.DataFrame:
    """Computes the laterality index from the different averages of the use and
    intensity signal.

    Args:
        locdfdict (pd.DataFrame): Dictionary with the dataframes from the different sensor locations. These dataframes contain the average use and intensity signals.
        dataparams (AttrDict): An AttrDict that contains the details of the 
        data being analysed.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.

    Returns:
        pd.DataFrame: Dataframe with the computed laterality index from the avar.
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[dataparams.sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[dataparams.sensor]['Left Wrist']
    
    _uselidf = pd.DataFrame()
    _intlidf = pd.DataFrame()
    _actlidf = pd.DataFrame()
    # Go through the use columns first and compute the average laterality 
    # index for each of them.
    for _col in locdfdict[rlbl]['use'].columns:
        _, _uselidf[f'{_col}'] = _test.instantaneous_latindex(
            domnaff=locdfdict[rlbl]['use'][_col].values,
            ndomaff=locdfdict[llbl]['use'][_col].values
        )
    _uselidf['TimeStamp'] = locdfdict[rlbl].index
    # Go through the int columns first and compute the instantaneous laterality 
    # index for each of them.
    for _col in locdfdict[rlbl]['int'].columns:
        _, _intlidf[f'{_col}'] = _test.instantaneous_latindex(
            domnaff=locdfdict[rlbl]['int'][_col].values,
            ndomaff=locdfdict[llbl]['int'][_col].values
        )
    _intlidf['TimeStamp'] = locdfdict[rlbl].index
    # Go through the int columns first and compute the instantaneous laterality 
    # index for each of them.
    for _col in locdfdict[rlbl]['act'].columns:
        _, _actlidf[f'{_col}'] = _test.instantaneous_latindex(
            domnaff=locdfdict[rlbl]['act'][_col].values,
            ndomaff=locdfdict[llbl]['act'][_col].values
        )
    _actlidf['TimeStamp'] = locdfdict[rlbl].index
    return pd.concat({'use': _uselidf.set_index('TimeStamp'),
                      'int': _intlidf.set_index('TimeStamp'),
                      'act': _actlidf.set_index('TimeStamp')}, axis=1)


def compute_ulfunc_activity(ulfuncavrgdf: pd.DataFrame) -> float:
    """Computes the different average UL functioning constructs of interest
    from the given raw data dataframe. The exact measures thata re computed
    will depend on the  sensor and the data type.

    Args:
        rawdf (pd.DataFrame): Dataframe containing the containig the raw data.
        ulfuncinstdf (pd.DataFrame): Dataframe containing the instantaneous 
        ulfunc data.
        analysisparams (AttrDict): An AttrDict that contains the details of the 
        analysis parameters to be used for computing the different constructs
        and the summary variables.

    Returns:
        pd.DataFrame: Dataframe with the computed average UL functioning measures.
    """
    pass


def actigraph_vecmag_uluse(rawdf: pd.DataFrame,
                           measuresparams: dict) -> pd.DataFrame:
    """Computes ULUse measures using the vector magnitude data from the
    ActiGraph sensor.

    Args:
        rawdf (pd.DataFrame): Dataframe containing the containig the raw data.
        measuresparams (dict): An dictionary with the parameters for the 
        different UL use measures.

    Returns:
        pd.DataFrame: Dataframe with the computed UL use measures.
    """
    ulusedf = pd.DataFrame()
    
    # 1. Single threshold from vector magnitude
    _, _uluse = ulfunc.uluse.from_vector_magnitude1(
        rawdf["Vector Magnitude"],
        threshold=measuresparams['vm1']['threshold']
    )
    ulusedf['vm1'] = _uluse

    # 2. Double threshold from vector magnitude
    _, _uluse = ulfunc.uluse.from_vector_magnitude2(
        rawdf["Vector Magnitude"],
        threshold0=measuresparams['vm2']['threshold0'],
        threshold1=measuresparams['vm2']['threshold1']
    )
    ulusedf['vm2'] = _uluse
    return ulusedf


def actigraph_raw_uluse(datadf: pd.DataFrame,
                        tstamps: np.array) -> pd.DataFrame:
    # TO BE IMPLEMENTED
    pass


def arimu_raw_uluse(datadf: pd.DataFrame,
                    measuresparams: dict) -> pd.DataFrame:
    """Computes ULUse measures using the raw acceleration data from the
    ARIMU sensor.

    Args:
        rawdf (pd.DataFrame): Dataframe containing the containig the raw data.
        measuresparams (dict): An dictionary with the parameters for the 
        different UL use measures.

    Returns:
        pd.DataFrame: Dataframe with the computed UL use measures.
    """
    ulusedf = pd.DataFrame()
    
    # GMAC
    _, _uluse = ulfunc.uluse.from_gmac(acc_forearm=datadf['ax'],
                                       acc_ortho1=datadf['ay'],
                                       acc_ortho2=datadf['az'],
                                       sampfreq=dcfg.SUPPORTED_SENSORS['ARIMU']['Raw Data']['samplingrate'])
    ulusedf['gmac'] = _uluse
    return ulusedf


def actigraph_vecmag_ulint(datadf: pd.DataFrame,
                           ulusedf: pd.DataFrame,
                           srratio: int,
                           measuresparams: dict) -> pd.DataFrame:
    """Computes UL Intensity measures using the vector magnitude data from the
    ActiGraph sensor.

    Args:
        datadf (pd.DataFrame): Dataframe containing the containig the raw data.
        ulusedf (pd.DataFrame): Dataframe containing the containig UL use
        signals quantified using different measures.
        srratio (int): A non-zero positive integer that is the ratio of the 
        sampling rates
        measuresparams (dict): An dictionary with the parameters for the 
        different UL intensity measures.

    Returns:
        pd.DataFrame: Dataframe with the computed UL intensity measures.
    """
    ulintdf = pd.DataFrame()
    # The vector magnitude can be used as a measure of intensity. The UL 
    # instantaneous intensity is computed using the different UL use signals.
    # From vecmag1th use signal
    _, _ulint = ulfunc.ulint.from_vector_magnitude(datadf["Vector Magnitude"],
                                                   ulusedf['vm1'],
                                                   nsample=srratio)
    ulintdf['vm1'] = _ulint
    # From vecmag2th use signal
    _, _ulint = ulfunc.ulint.from_vector_magnitude(datadf["Vector Magnitude"],
                                                   ulusedf['vm2'],
                                                   nsample=srratio)
    ulintdf['vm2'] = _ulint
    return ulintdf


def actigraph_raw_ulint(datadf: pd.DataFrame,
                        tstamps: np.array) -> pd.DataFrame:
    # TO BE IMPLEMENTED
    pass


def arimu_raw_ulint(datadf: pd.DataFrame,
                    ulusedf: pd.DataFrame,
                    srratio: int,
                    measuresparams: dict) -> pd.DataFrame:
    """Computes UL Intensity measures using the raw acceleration data from the
    ARIMU sensor.

    Args:
        datadf (pd.DataFrame): Dataframe containing the containig the raw data.
        ulusedf (pd.DataFrame): Dataframe containing the containig UL use
        signals quantified using different measures.
        srratio (int): A non-zero positive integer that is the ratio of the 
        sampling rates
        measuresparams (dict): An dictionary with the parameters for the 
        different UL intensity measures.

    Returns:
        pd.DataFrame: Dataframe with the computed UL intensity measures.
    """
    ulintdf = pd.DataFrame()
    _, _ulint = grav_sub_mag(np.linalg.norm(datadf[['ax', 'ay', 'az']], ord=2, axis=1),
                             ulusedf['gmac'],
                             nsample=srratio)
    ulintdf['gsm_gmac'] = _ulint
    return ulintdf


# ################################### #
# Other supporting internal functions #
# ################################### #
def _get_day_raw_df(data: pd.DataFrame, dfname: str, dfcreate: bool,
                    partialdf: pd.DataFrame, dataparams: AttrDict) -> None:
    # Get timestamp column.
    allts = data['TimeStamp'].values
    alldates = list(
        map(lambda x:  x.date(),
            list(map(bookkeeping.to_datetime, allts)))
    )
    _dates = np.sort(np.unique(alldates))
    _samplerate = dcfg.get_sampling_rate(sensname=dataparams.sensor,
                                         data_type=dataparams.data_type)

    # Get data corresponding to the date and combine it with the partial DF.
    if not dfcreate:
        return None
    
    # Get date.
    dfdate = dt.strptime(dfname.split('_')[-2], "%y-%m-%d").date()
    dinx = np.array(alldates) == dfdate
    ddf = _gen_time_column_for_day(dfdate, _samplerate)
    _others = ((partialdf.set_index('TimeStamp'), data[dinx].set_index('TimeStamp'))
                if partialdf is not None and data['Date'][0] == _dates[0]
                else data[dinx].set_index('TimeStamp'))
    ddf = ddf.join(_others, on='TimeStamp')
    return ddf


def _get_usecol_for_intcol(intcol: str, usecols: list[str]) -> str:
    for _uc in usecols:
        # Make sure both are either wf columns or both are not.
        _wfcond = (('_wf' in _uc and '_wf' in intcol)
                   or ('_wf' not in _uc and '_wf' not in intcol))
        if _wfcond and (_uc == intcol or _uc in intcol):
            return _uc
    return None


def _gen_time_column_for_day(day: dt.date, samplerate: float) -> pd.DataFrame:
    return pd.DataFrame.from_dict(
        {'TimeStamp': np.arange(day, day + tdelta(days=1),
                                tdelta(milliseconds=1000 / samplerate))}
    )


def _gen_save_hq_summary(bkdata, domnaff, ndomaff, alldates, start_ts, stop_ts):
    for summfname, summfcreate in bkdata['summary']['hq']:
        if summfcreate is False:
            continue
        summwin = int(re.search(r'^.*_summ([0-9]*)_.*$', summfname).group(1))

        # Get complete set of timestamps for the give summary window size.
        _allsummts = np.arange(start_ts, stop_ts, tdelta(minutes=summwin))

        # Go through dates and compute activity summary.
        _summhq_dna = []
        _summhq_nda = []
        for _date in alldates:
            _datedf = feather.read_feather(bkdata[_date]['ulfuncavrg'][0])
            _actcols = list(_datedf[domnaff]['act'])
            # Compute summary for different time segments.
            _tsinx = np.all(np.array([_allsummts >= _date,
                                      _allsummts < _date + tdelta(days=1)]),
                            axis=0)
            for _strtts in _allsummts[_tsinx]:
                # _start and _stop times for the time semgent.
                _stopts = (bookkeeping.to_datetime(_strtts)
                           + tdelta(minutes=summwin))

                # Select data in this time window.
                _dfinx = ((_datedf['TimeStamp'] >= _strtts)
                          & (_datedf['TimeStamp'] < _stopts))
                # Dominant/Non-affected limb
                _summhq_dna.append([
                    ulfunc.measures.Hq(_datedf[domnaff]['act'][_ac][_dfinx].values,
                                       q=95)
                    for _ac in _actcols
                ])
                # Non-dominant/Affected limb
                _summhq_nda.append([
                    ulfunc.measures.Hq(_datedf[ndomaff]['act'][_ac][_dfinx].values,
                                       q=95)
                    for _ac in _actcols
                ])
        # Create dataframes.
        _summhq_dna_df = pd.DataFrame(data=np.array(_summhq_dna),
                                      columns=_actcols)
        _summhq_dna_df['TimeStamp'] = _allsummts
        _summhq_nda_df = pd.DataFrame(data=np.array(_summhq_nda),
                                      columns=_actcols)
        _summhq_nda_df['TimeStamp'] = _allsummts
        _summhq_df =  pd.concat({domnaff: _summhq_dna_df.set_index('TimeStamp'),
                                 ndomaff: _summhq_nda_df.set_index('TimeStamp')},
                                axis=1).reset_index()

        # Save the ulfuc instantaneous file.
        # Write data to disk.
        pathlib.Path(os.sep.join(summfname.split(os.sep)[:-1])).mkdir(parents=True, exist_ok=True)
        feather.write_feather(_summhq_df, summfname)
        _summhq_df.to_csv(f"{summfname.split('.aipc')[0]}.csv")
        # sys.stdout.write(f" [Generated {summfname}]")


def _gen_save_laterality_index_summary(bkdata, alldates, analysisparams):
    for summfname, summfcreate in bkdata['summary']['li']:
        if summfcreate is False:
            continue

        # Summry window
        summwin = int(re.search(r'^.*_summ([0-9]*)_.*$', summfname).group(1))

        # Go through dates and compute activity summary.
        _useaoli = {'TimeStamp': []}
        _intaoli = {'TimeStamp': []}
        _uselioa = {'TimeStamp': []}
        _intlioa = {'TimeStamp': []}
        _actlioa = {'TimeStamp': []}
        for _date in alldates:
            _datedf = feather.read_feather(bkdata[_date]['ulfuncavrg'][0])

            # Average of LI
            _samp = analysisparams['avgwindur'] / 60.0
            #
            # Go through use column laterality index.
            for _colname, _colval in _datedf['LatIndex']['use'].iteritems():
                # Add colums if not already present.
                if _colname not in _useaoli:
                    _useaoli[_colname] = []
                # Compute average
                _inx, _ali = _test.average_latindex(_colval.values,
                                                    windur=summwin,
                                                    winshift=summwin,
                                                    sample_t=_samp)
                _useaoli[_colname] += list(_ali)
            _useaoli['TimeStamp'] += list(_datedf['TimeStamp'].values[_inx])
            #
            # # Go through int column laterality index.
            for _colname, _colval in _datedf['LatIndex']['int'].iteritems():
                # Add colums if not already present.
                if _colname not in _intaoli:
                    _intaoli[_colname] = []
                # Compute average
                _inx, _ali = _test.average_latindex(_colval.values,
                                                    windur=summwin,
                                                    winshift=summwin,
                                                    sample_t=_samp)
                _intaoli[_colname] += list(_ali)
            _intaoli['TimeStamp'] += list(_datedf['TimeStamp'].values[_inx])
            
            # LI of Average
            _windur = summwin
            #
            # Go through use column laterality index.
            for _colname, _colval in _datedf['LatIndexoA']['use'].iteritems():
                # Add colums if not already present.
                if _colname not in _uselioa:
                    _uselioa[_colname] = []
                # Compute average
                _inx, _ali = _test.average_latindex(_colval.values,
                                                    windur=_windur,
                                                    winshift=_windur,
                                                    sample_t=_samp)
                _uselioa[_colname] += list(_ali)
            _uselioa['TimeStamp'] += list(_datedf['TimeStamp'].values[_inx])
            #
            # Go through int column laterality index.
            for _colname, _colval in _datedf['LatIndexoA']['int'].iteritems():
                # Add colums if not already present.
                if _colname not in _intlioa:
                    _intlioa[_colname] = []
                # Compute average
                _inx, _ali = _test.average_latindex(_colval.values,
                                                    windur=_windur,
                                                    winshift=_windur,
                                                    sample_t=_samp)
                _intlioa[_colname] += list(_ali)
            _intlioa['TimeStamp'] += list(_datedf['TimeStamp'].values[_inx])
            #
            # Go through act column laterality index.
            for _colname, _colval in _datedf['LatIndexoA']['act'].iteritems():
                # Add colums if not already present.
                if _colname not in _actlioa:
                    _actlioa[_colname] = []
                # Compute average
                _inx, _ali = _test.average_latindex(_colval.values,
                                                    windur=_windur,
                                                    winshift=_windur,
                                                    sample_t=_samp)
                _actlioa[_colname] += list(_ali)
            _actlioa['TimeStamp'] += list(_datedf['TimeStamp'].values[_inx])

        # Create dataframes.
        _useaolidf = pd.DataFrame.from_dict(_useaoli)
        _intaolidf = pd.DataFrame.from_dict(_intaoli)
        _aolidf = pd.concat({'use': _useaolidf.set_index('TimeStamp'),
                             'int': _intaolidf.set_index('TimeStamp')},
                             axis=1).reset_index()
        _uselioadf = pd.DataFrame.from_dict(_uselioa)
        _intlioadf = pd.DataFrame.from_dict(_intlioa)
        _actlioadf = pd.DataFrame.from_dict(_actlioa)
        _lioadf = pd.concat({'use': _uselioadf.set_index('TimeStamp'),
                             'int': _intlioadf.set_index('TimeStamp'),
                             'act': _actlioadf.set_index('TimeStamp')},
                             axis=1).reset_index()
        _summ_li_df =  pd.concat({'LatIndex': _aolidf.set_index('TimeStamp'),
                                  'LatIndexoA': _lioadf.set_index('TimeStamp')},
                                 axis=1).reset_index()
        # Save the ulfuc instantaneous file.
        # Write data to disk.
        _filepath = os.sep.join(summfname.split(os.sep)[:-1])
        pathlib.Path(_filepath).mkdir(parents=True, exist_ok=True)
        feather.write_feather(_summ_li_df, summfname)
        _summ_li_df.to_csv(f"{summfname.split('.aipc')[0]}.csv")
        # sys.stdout.write(f" [Generated {summfname}]")


def _gen_save_rq_summary(bkdata, domnaff, ndomaff, alldates, start_ts, stop_ts):
    for summfname, summfcreate in bkdata['summary']['rq']:
        if summfcreate is False:
            continue
        summwin = int(re.search(r'^.*_summ([0-9]*)_.*$', summfname).group(1))
        
        # Get complete set of timestamps for the give summary window size.
        _allsummts = np.arange(start_ts, stop_ts, tdelta(minutes=summwin))
        
        # Go through dates and compute activity summary.
        _userq = []
        _intrq = []
        _actrq = []
        for _date in alldates:
            _datedf = feather.read_feather(bkdata[_date]['ulfuncavrg'][0])
            _usecols = list(_datedf[domnaff]['use'])
            _intcols = list(_datedf[domnaff]['int'])
            _actcols = list(_datedf[domnaff]['act'])
            
            # Comopute summary for different time segments.
            _tsinx = np.all(np.array([_allsummts >= _date,
                                      _allsummts < _date + tdelta(days=1)]),
                            axis=0)
            for _strtts in _allsummts[_tsinx]:
                # _start and _stop times for the time semgent.
                _stopts = (bookkeeping.to_datetime(_strtts)
                           + tdelta(minutes=summwin, microseconds=-1))
                
                # Select data in this time window.
                _dfinx = ((_datedf['TimeStamp'] >= _strtts)
                          & (_datedf['TimeStamp'] < _stopts))
                
                # Compute Rq from the different constructs
                # use columns
                _userq += [[
                    ulfunc.measures.Rq(domnaff=_datedf[domnaff]['use'][_col][_dfinx].values,
                                       ndomaff=_datedf[ndomaff]['use'][_col][_dfinx].values,
                                       q=95)[0]
                    for _col in _usecols
                ]]
                # intensity columns
                _intrq += [[
                    ulfunc.measures.Rq(domnaff=_datedf[domnaff]['int'][_col][_dfinx].values,
                                       ndomaff=_datedf[ndomaff]['int'][_col][_dfinx].values,
                                       q=95)[0]
                    for _col in _intcols
                ]]
                # activity columns
                _actrq += [[
                    ulfunc.measures.Rq(domnaff=_datedf[domnaff]['act'][_col][_dfinx].values,
                                       ndomaff=_datedf[ndomaff]['act'][_col][_dfinx].values,
                                       q=95)[0]
                    for _col in _actcols
                ]]
        
        # Create dataframes.
        _userq_df = pd.DataFrame(data=np.array(np.array(_userq)),
                                 columns=_usecols)
        _userq_df['TimeStamp'] = _allsummts
        _intrq_df = pd.DataFrame(data=np.array(np.array(_intrq)),
                                 columns=_intcols)
        _intrq_df['TimeStamp'] = _allsummts
        _actrq_df = pd.DataFrame(data=np.array(np.array(_actrq)),
                                 columns=_actcols)
        _actrq_df['TimeStamp'] = _allsummts
        _summrq_df =  pd.concat({'use': _userq_df.set_index('TimeStamp'),
                                 'int': _intrq_df.set_index('TimeStamp'),
                                 'act': _actrq_df.set_index('TimeStamp')},
                                axis=1).reset_index()
        
        # Save the ulfuc instantaneous file.
        # Write data to disk.
        pathlib.Path(os.sep.join(summfname.split(os.sep)[:-1])).mkdir(parents=True, exist_ok=True)
        feather.write_feather(_summrq_df, summfname)
        _summrq_df.to_csv(f"{summfname.split('.aipc')[0]}.csv")
        # sys.stdout.write(f" [Generated {summfname}]")