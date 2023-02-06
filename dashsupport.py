"""
Module with a set of supporting functions and classes for the UL Functioning
Dashboard.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 27 Oct 2022
"""

import glob
import sys
import os
import re
import json

from datetime import datetime as dt
from datetime import timedelta
from plotly.subplots import make_subplots

import pandas as pd
import plotly.graph_objects as go
from pyarrow import feather
from attrdict import AttrDict

import dashconfig as dcfg

from bookkeeping import BookKeeper


def gather_data_details(datadir: str) -> dict:
    """Reads the data directory and generates a summary of the data that is 
    available for visualization.

    Parameters
    ----------
    datadir : str
        Name of the directory with the data to be visualized.

    Returns
    -------
    dict
        Dictionary containing the details of the 
    """
    # Get the list of analysis params.
    analysisparams_list = get_list_of_analysis_params(datadir)
    if len(analysisparams_list) == 0:
        # Nothing to visualize.
        sys.stdout.write("\n > Nothing to visualize.")
        return {}

    # Read data params
    data_params = dcfg.read_data_params(f"{datadir}/data_params.json")

    # Get the list of subjects.
    subjs = {
        el.split(os.sep)[-1]: el 
        for el in glob.glob(f"{datadir}/*")
        if os.path.isdir(el) and el.split(os.sep)[-1] != dcfg.OUTPUT_DIR
    }

    # When was the last processing done?
    with open(f"{datadir}/{dcfg.OUTPUT_DIR}/bookkeeping.json", "r") as fh:
        bkdata = json.load(fh)
    recent_date = max(map(lambda x: dt.strptime(x, '%m/%d/%y %H:%M:%S'),
                          bkdata['summary'].keys()))

    return {'datadir': datadir,
            'analysis_params_list': analysisparams_list,
            'analysis_params': analysisparams_list[0],
            'data_params': data_params,
            'subjs': subjs,
            'output': f"{datadir}/{dcfg.OUTPUT_DIR}",
            'last_analysis_date': recent_date}


def is_valid_data_directory(datadir: str) -> bool:
    """Checks if the given directory is a valid data directory.

    Parameters
    ----------
    datadir : str
        Path of the data directory.

    Returns
    -------
    bool
        True if its valid else False.
    """
    # Check if the directory exists
    if os.path.exists(datadir) is False:
        sys.stdout.write(f"\n Error! '{datadir}' does not exist.")
        return False
    
    # Check if data params file exists.
    _dataparamsfile = f"{datadir}/data_params.json"
    if os.path.exists(_dataparamsfile) is False:
        sys.stdout.write(f"\n Error! '{_dataparamsfile}' does not exist.")
        return False
    
    # Check if analysis_params files exist.
    _analysisparamsfile = f"{datadir}/analysis_params.json"
    if os.path.exists(_analysisparamsfile) is False:
        sys.stdout.write(f"\n Error! '{_analysisparamsfile}' does not exist.")
        return False

    # Check if the output folder exists.
    _outdir = f"{datadir}/{dcfg.OUTPUT_DIR}"
    if os.path.exists(_outdir) is False:
        sys.stdout.write(f"\n Error! '{_outdir}' does not exist.")
        return False
    
    return True


def get_list_of_analysis_params(datadir: str) -> list[dict]:
    """Get the list of analysis param used for processing the data in the given 
    data directory.

    Parameters
    ----------
    datadir : str
        Directory containing the UL functioning data.

    Returns
    -------
    list[dict]
        List of dictionaries with the analysis parameters dictionary.
    """
    aprmslist = []
    if is_valid_data_directory(datadir) is False:
        sys.stdout.write(" Terminating process.")
        return aprmslist
    
    # Get the list of subjects.
    subjs = {
        el.split(os.sep)[-1]: el 
        for el in glob.glob(f"{datadir}/*")
        if os.path.isdir(el) and el.split(os.sep)[-1] != dcfg.OUTPUT_DIR
    }
    
    # Go through each subject and get the analysis params.
    _regexp = r'^.*_sr([\.\d]*)_avg([\.\d]*)-([\.\d]*)_summ([\.\d]*).*_summary.*$'
    for _s, _sd in subjs.items():
        _summfiles = glob.glob(f"{datadir}/{dcfg.OUTPUT_DIR}/{_s}/summary/*_summary_*.{dcfg.PROC_FILE_EXTN}")
        for _sf in _summfiles:
            _match =  re.search(_regexp, _sf).groups()
            _aprm = dict(ulfuncinstsamprate = float(_match[0]),
                         avgwindur = float(_match[1]),
                         avgwinshift = float(_match[2]),
                         summarywin = [int(_match[3])],)
            aprmslist = _addto_aanlysis_params_dict_list(_aprm, aprmslist)
    return aprmslist


def get_actvity_columns(datadetails: dict) -> list[str]:
    """Returns the list of UL average activity columns for the given data.

    Parameters
    ----------
    datadetails : dict
        Dictionary with the details of the data to be visualized. This is the 
        dict returned by the `gather_data_details` function in this module.

    Returns
    -------
    list[str]
        List of the columns names for the different average activtiy measures.
    """
    _fname = ''
    for _subj in list(datadetails['subjs'].keys()):
        _files = glob.glob(f"{datadetails['output']}/{_subj}/ulfuncavrg/*.{dcfg.PROC_FILE_EXTN}")
        if len(_files) > 0:
            _fname = _files[0]
    _data = feather.read_feather(_fname)
    
    # Data params.
    data_params = dcfg.read_data_params(f"{datadetails['datadir']}/data_params.json")
    actcols = {}
    for _c in list(_data[data_params.locid[0]]['act'].columns):
        _usec, _intc = _c.split('*')
        actcols[_c] = ' * '.join((dcfg.MEASURE_LABELS['use'][_usec],
                                  dcfg.MEASURE_LABELS['int'][_intc]))
    return actcols


def get_useintact_columns(datadetails: dict) -> list[str]:
    """Returns the list of all use, int, and activity columns for the given
    data.

    Parameters
    ----------
    datadetails : dict
        Dictionary with the details of the data to be visualized. This is the 
        dict returned by the `gather_data_details` function in this module.

    Returns
    -------
    list[str]
        List of the columns names for the different average use, intensity, 
        and activtiy measures.
    """
    _fname = ''
    for _subj in list(datadetails['subjs'].keys()):
        _files = glob.glob(f"{datadetails['output']}/{_subj}/ulfuncavrg/*.{dcfg.PROC_FILE_EXTN}")
        if len(_files) > 0:
            _fname = _files[0]
    _data = feather.read_feather(_fname)
    
    # Data params.
    data_params = dcfg.read_data_params(f"{datadetails['datadir']}/data_params.json")
    allcols = {}
    for _c in list(_data[data_params.locid[0]]['use'].columns):
        allcols['use-' + _c] = 'Use - ' + dcfg.MEASURE_LABELS['use'][_c]
    for _c in list(_data[data_params.locid[0]]['int'].columns):
        allcols['int-' + _c] = 'Intensity - ' + dcfg.MEASURE_LABELS['int'][_c]
    for _c in list(_data[data_params.locid[0]]['act'].columns):
        _usec, _intc = _c.split('*')
        allcols['act-' + _c] = ('Activity - '
                                + ' * '.join((dcfg.MEASURE_LABELS['use'][_usec],
                                              dcfg.MEASURE_LABELS['int'][_intc])))
    return allcols


def get_useintact_columns_short(datadetails: dict) -> list[str]:
    """Returns the list of all use, int, and activity columns for the given
    data.

    Parameters
    ----------
    datadetails : dict
        Dictionary with the details of the data to be visualized. This is the 
        dict returned by the `gather_data_details` function in this module.

    Returns
    -------
    list[str]
        List of the columns names for the different average use, intensity, 
        and activtiy measures.
    """
    _fname = ''
    for _subj in list(datadetails['subjs'].keys()):
        _files = glob.glob(f"{datadetails['output']}/{_subj}/ulfuncavrg/*.{dcfg.PROC_FILE_EXTN}")
        if len(_files) > 0:
            _fname = _files[0]
    _data = feather.read_feather(_fname)
    
    # Data params.
    data_params = dcfg.read_data_params(f"{datadetails['datadir']}/data_params.json")
    allcols = {}
    for _c in list(_data[data_params.locid[0]]['use'].columns):
        allcols['use-' + _c] = 'Use - ' + dcfg.MEASURE_SHORT_LABELS['use'][_c]
    for _c in list(_data[data_params.locid[0]]['int'].columns):
        allcols['int-' + _c] = 'Intensity - ' + dcfg.MEASURE_SHORT_LABELS['int'][_c]
    for _c in list(_data[data_params.locid[0]]['act'].columns):
        _usec, _intc = _c.split('*')
        allcols['act-' + _c] = ('Activity - '
                                + ' * '.join((dcfg.MEASURE_SHORT_LABELS['use'][_usec],
                                              dcfg.MEASURE_SHORT_LABELS['int'][_intc])))
    return allcols


def _addto_aanlysis_params_dict_list(aprmdict: dict, aprmlist: list[dict]) -> list[dict]:
    """Add the given analysis param dict to the list of analysis param dicts.
    If the given dict matches an existing one, things will be combined, else 
    the dict witll be added as a new element to the list.
    """
    for _aprmd in aprmlist:
        # check if the given aprmdict matches for the first three parameters.
        if (_aprmd["ulfuncinstsamprate"] == aprmdict["ulfuncinstsamprate"]
            and _aprmd["avgwindur"] == aprmdict["avgwindur"]
            and _aprmd["avgwinshift"] == aprmdict["avgwinshift"]):
            # Check if the summary value exists.
            if aprmdict['summarywin'][0] not in _aprmd['summarywin']:
                _aprmd['summarywin'] += aprmdict['summarywin']
                _aprmd['summarywin'].sort()
                
            return aprmlist
    # No match. Just append the dict.
    aprmlist.append(aprmdict)
    return aprmlist

# ########################################################################## #
# Data extraction functions used by the callback functions by the dashboard.
# ########################################################################## #
# 
# Get dates for the subject.
def _get_subject_dates(datadir: str, subjname: str) -> list[dt]:
    _basename = f"{datadir}/{dcfg.OUTPUT_DIR}/{subjname}/raw/"
    _dates = [
        dt.strptime(re.search(r"_(\d{2}-\d{2}-\d{2})_", _f).groups()[0],
                    '%y-%m-%d')
        for _f in glob.glob(f"{_basename}/*{dcfg.PROC_FILE_EXTN}")
    ]
    _dates.sort()
    return _dates
    
#
# Function get the detials of the subject to be dispalyed on the table.
def get_subject_summary_details(datadir: str, subjname: str) -> tuple[str]:
    _fmt = '%d %b, %Y'
    _dates = _get_subject_dates(datadir, subjname)
    return (subjname,
            f"{min(_dates).strftime(_fmt)} - {max(_dates).strftime(_fmt)}")

#
# Function get the date details of the subject to be dispalyed.
def get_subject_date_details(datadir: str, subjname: str) -> tuple:
    _dates = _get_subject_dates(datadir, subjname)
    return (0, len(_dates) - 1, [0, len(_dates) - 1],
            {i: {'label': d.strftime("%d,%b'%y"),
                 'style': {'fontSize': '20px'}}
             for i, d in enumerate(_dates)})

#
# Function to get the ULFUNC average measures for the chosen subject.
def get_ulfavrg_data_for_subject(datadetails: dict, subj_name: str) -> pd.DataFrame:
    """Returns a dataframe with ULFUNC average measures for the chosen subject.

    Parameters
    ----------
    datadetails : dict
        Dictionary with the details of the data to be visualized. This is the 
        dict returned by the `gather_data_details` function in this module.
    subj_name : str
        Name of the subject whose data is to be returned.

    Returns
    -------
    pd.DataFrame
        The pandas dataframe with the data from the chosen subject.
    """
    uvi_data = pd.DataFrame()
    # analysis string
    _aprm_str = BookKeeper.get_analysis_param_file_strings(AttrDict(datadetails['analysis_params']))
    _fname = os.sep.join((datadetails['output'],
                          subj_name,
                          "ulfuncavrg",
                          f"*_{_aprm_str[0]}_{_aprm_str[1]}_*.{dcfg.PROC_FILE_EXTN}"))
    for i, _f in enumerate(glob.glob(_fname)):
        # Get file name
        # print(i)
        uvi_data = pd.concat([uvi_data, feather.read_feather(_f)],
                             axis=0, ignore_index=True)
    # Add subject column. Just ensure there are not errors when the data is
    # used for visulization.
    uvi_data['subject'] = subj_name
    uvi_data.set_index('TimeStamp', inplace=True)
    uvi_data.sort_index(inplace=True)
    uvi_data.reset_index(inplace=True)
    return uvi_data


#
# Function to get the ULFUNC summary measures for the chosen subject.
def get_summary_data_for_subject(datadetails: dict, subj_name: str) -> dict:
    """Returns a dataframe with ULFUNC summary measures for the chosen subject.

    Parameters
    ----------
    datadetails : dict
        Dictionary with the details of the data to be visualized. This is the 
        dict returned by the `gather_data_details` function in this module.
    subj_name : str
        Name of the subject whose data is to be returned.

    Returns
    -------
    dict
        Dictionary containing the summary data for the hq and li measures for the chosen subject.
    """
    summ_data = {'hq': pd.DataFrame(),
                 'li': pd.DataFrame()}
    # analysis string
    _aprm_str = BookKeeper.get_analysis_param_file_strings(AttrDict(datadetails['analysis_params']))

    # Go through all summary times.
    # print(subj_name, datadetails['analysis_params']['summarywin'])
    for _summstr in _aprm_str[2]:
        # Extract summary window size.
        _summwin = int(re.search(r'summ([0-9]*)', _summstr).groups(0)[0])

        # Get file name for Hq
        _fname_hq = os.sep.join((datadetails['output'],
                                 subj_name,
                                 "summary",
                                 f"*_{_aprm_str[0]}_{_aprm_str[1]}_{_summstr}*_hq.{dcfg.PROC_FILE_EXTN}"))
        # Read Hq data.
        _summdata = feather.read_feather(glob.glob(_fname_hq)[0])
        _summdata['summwin'] = _summwin
        _summdata['subject'] = subj_name
        summ_data['hq'] = pd.concat([summ_data['hq'], _summdata],
                                    axis=0, ignore_index=True)

        # Get file name for LI
        _fname_li = os.sep.join((datadetails['output'],
                                 subj_name,
                                 "summary",
                                 f"*_{_aprm_str[0]}_{_aprm_str[1]}_{_summstr}*_li.{dcfg.PROC_FILE_EXTN}"))
        _summdata = feather.read_feather(glob.glob(_fname_li)[0])
        _summdata['summwin'] = _summwin
        _summdata['subject'] = subj_name
        summ_data['li'] = pd.concat([summ_data['li'], _summdata],
                                    axis=0, ignore_index=True)
    return summ_data


# #
# # Function to plot the daily summary of Hq and LI.
# def summary_temporal_hq_li_plots(subjdata_summary, start_date, winsz):
#     """Function to generate the Hq and LI temporal plots.
#     """
#     _fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
#                          vertical_spacing=0.1,
#                          subplot_titles=("UL Activity", "Laterality Index"))
#     _fig.update_annotations(font_size=22)
    
#     # Hq
#     _inx = subjdata_summary['hq']['summwin'] == winsz
#     _fig.add_trace(
#         go.Scatter(x=subjdata_summary['hq']['TimeStamp'][_inx],
#                    y=subjdata_summary['hq']['R']['vm2_wf*vm2_wf'][_inx],
#                    name="Hq (Right)"),
#         row=1, col=1
#     )
#     _fig.add_trace(
#         go.Scatter(x=subjdata_summary['hq']['TimeStamp'][_inx],
#                    y=subjdata_summary['hq']['L']['vm2_wf*vm2_wf'][_inx],
#                    name="Hq (Left)"),
#         row=1, col=1
#     )
#     _fig.update_traces(mode='lines+markers',
#                        marker=dict(size=5, line=dict(width=1, color='DarkSlateGrey')),
#                        row=1, col=1)
#     _fig.update_layout(
#         template='plotly_white',
#         font=dict( 
#             family="Helvetica",
#             size=18,
#             color="Black"
#         ),
#         legend=dict(
#             orientation="h",
#             yanchor="bottom",
#             y=1.02,
#             xanchor="right",
#             x=1.0
#         )
#     )
#     _fig.update_xaxes(showline=True, linewidth=1, linecolor='black',
#                       range=[start_date - timedelta(days=2),
#                              start_date + timedelta(days=7)], row=1, col=1)
#     _fig.update_yaxes(showline=True, linewidth=1, linecolor='black', row=1, col=1)

#     # LI
#     _inx = subjdata_summary['li']['summwin'] == winsz
#     _fig.add_trace(
#         go.Scatter(x=subjdata_summary['li']['TimeStamp'][_inx],
#                    y=subjdata_summary['li']['LatIndex']['int']['vm2_wf'][_inx],
#                    name="Laterality Index"),
#         row=2, col=1
#     )
#     _fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="black", row=2, col=1)
#     _fig.add_hrect(y0=0, y1=1.2, line_width=0, fillcolor="green", opacity=0.05, row=2, col=1)
#     _fig.add_hrect(y0=0, y1=-1.2, line_width=0, fillcolor="red", opacity=0.05, row=2, col=1)
#     _fig.update_traces(mode='lines+markers',
#                        marker=dict(size=5, line=dict(width=1, color='DarkSlateGrey')),
#                        row=2, col=1)
#     _fig.update_xaxes(showline=True, linewidth=2, linecolor='black',
#                       range=[start_date - timedelta(days=2),
#                              start_date + timedelta(days=7)], row=2, col=1)
#     _fig.update_yaxes(showline=True, linewidth=2, linecolor='black',
#                       range=[-1.1, 1.1], row=2, col=1)
#     _fig.update_layout(height=600)

#     return _fig
