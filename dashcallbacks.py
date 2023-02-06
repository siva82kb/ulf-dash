"""Script implementing the callbacks for the UL functioning dashboard app.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 27 Oct 2022
"""

import re
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from monalysa import ulfunc
from plotly.subplots import make_subplots

import dashconfig as dcfg
from dashsupport import (_get_subject_dates, get_subject_date_details,
                         get_subject_summary_details,
                         get_summary_data_for_subject,
                         get_ulfavrg_data_for_subject,
                         get_useintact_columns_short)


# Subject Selection Dropbox Callback --> Update Table
def update_subj_table(subj_name, subjdata_ulfavrg, subjdata_summary, datadir):
    """Update subject table.
    """    
    if len(subj_name) > 0:
        _subjdetails = get_subject_summary_details(datadir, subj_name)
        # Reset subject data.
        subjdata_ulfavrg = None
        subjdata_summary = None
        return _subjdetails[:2], subjdata_ulfavrg, subjdata_summary
    else:
        return ("-", "-"), subjdata_ulfavrg, subjdata_summary

# Update data range slider.
def update_date_range_slider(subj_name, datadir):
    """Update the date range slider from the subject details.
    """
    if len(subj_name) > 0:
        _subjdetails = get_subject_summary_details(datadir, subj_name)
        _subjdates = get_subject_date_details(datadir, subj_name)
        return _subjdates + (f'Select date range for {_subjdetails[0]}: ',)
    else:
        return (0, 1, [0, 1], 'No subject selected!')

# Function to update dropdowns based on waist filter selection.
def update_measure_dropdown(waist_filter_on, datadetails):
    """Update dropdowns based on waist filter selection.
    """
    # Get column names
    all_cols = get_useintact_columns_short(datadetails)
    # Filter based on checkbox
    if len(waist_filter_on) == 0:
        _uvi = [_v for _k, _v in all_cols.items() if 'act-' in _k and '_wf' not in _k]
        _ruf = [_v for _k, _v in all_cols.items() if '_wf' not in _k]
    else:
        _uvi = [_v for _k, _v in all_cols.items() if 'act-' in _k and '_wf' in _k]
        _ruf = [_v for _k, _v in all_cols.items() if '_wf' in _k]
    return _uvi, _uvi[0], _ruf, _ruf[0]

# Function to update dropdowns based on waist filter selection for the average
# measure selection..
def update_avrg_use_measure_dropdown(waist_filter_on, datadetails):
    """Update dropdowns based on waist filter selection.
    """
    # Get column names
    all_cols = get_useintact_columns_short(datadetails)
    # Filter based on checkbox
    if len(waist_filter_on) == 0:
        _use = [_v for _k, _v in all_cols.items()
                if 'use-' in _k and '_wf' not in _k]
    else:
        _use = [_v for _k, _v in all_cols.items()
                if 'use-' in _k and '_wf' in _k]
    return _use, _use[0]

# Function to update dropdowns based on the use dropdown selection.
def update_avrg_measure_dropdown_from_use(use_val, waist_filter_on, datadetails):
    """Update average measures dropdown based on the use dropdown selection.
    """
    # Get column names
    all_cols = get_useintact_columns_short(datadetails)
    # Get key for the selected use measures
    _key = [k.split('-')[1] for k, v in all_cols.items() if v == use_val]
    if len(_key) == 0:
        return [], None, [], None, [], None

    # Get the corresponding other measures,
    if len(waist_filter_on) == 0:
        _int = [_v for _k, _v in all_cols.items()
                if _key[0] in _k and 'int-' in _k and '_wf' not in _k]
        _act = [_v for _k, _v in all_cols.items()
                if _key[0] in _k and 'act-' in _k and '_wf' not in _k]
    else:
        _int = [_v for _k, _v in all_cols.items()
                if _key[0] in _k and 'int-' in _k and '_wf' in _k] 
        _act = [_v for _k, _v in all_cols.items()
                if _key[0] in _k and 'act-' in _k and '_wf' in _k]

    return _int, _int[0], _act, _act[0], [use_val] +_int, use_val

# Fucntion to generate the UVI plot.
def gen_uvi_plot(measure_name, subj_name, date_vals, subjdata_ulfavrg, datadetails):
    """Generate UVI plot.
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Left Wrist']
    
    # Get subject dates.
    _subjdates = _get_subject_dates(datadetails['datadir'], subj_name)

    # Check if subject data is None. If so, get the data.
    if subjdata_ulfavrg is None:
        subjdata_ulfavrg = get_ulfavrg_data_for_subject(datadetails, subj_name)
    elif subjdata_ulfavrg['subject'][0] != subj_name:
        subjdata_ulfavrg = get_ulfavrg_data_for_subject(datadetails, subj_name)

    # Find which use and int columns are to be used for the display.
    all_cols = get_useintact_columns_short(datadetails)
    _ucol, _icol = [_k.split('-')[1]
                    for _k, _v in all_cols.items()
                    if measure_name == _v][0].split('*')
    _acol = [_k.split("-")[1] for _k, _v in all_cols.items() if measure_name == _v][0]

    # Get right and left data
    _rightdata = pd.DataFrame.from_dict({'TimeStamp': subjdata_ulfavrg['TimeStamp'],
                                         'use': subjdata_ulfavrg[rlbl]['use'][_ucol].values,
                                         'int': subjdata_ulfavrg[rlbl]['int'][_icol].values,
                                         'act': subjdata_ulfavrg[rlbl]['act'][_acol].values,
                                         'arm': ['Right'] * len(subjdata_ulfavrg[rlbl]['int'][_icol].values)})
    _leftdata = pd.DataFrame.from_dict({'TimeStamp': subjdata_ulfavrg['TimeStamp'],
                                        'use': subjdata_ulfavrg[llbl]['use'][_ucol].values,
                                        'int': -subjdata_ulfavrg[llbl]['int'][_icol].values,
                                        'act': subjdata_ulfavrg[llbl]['act'][_acol].values,
                                         'arm': ['Left'] * len(subjdata_ulfavrg[rlbl]['int'][_icol].values)})
    _data = pd.concat([_rightdata, _leftdata], axis=0, ignore_index=True)

    # Get date indices.
    _dateinx = ((_data['TimeStamp'] >= _subjdates[date_vals[0]])
                & (_data['TimeStamp'] <= (_subjdates[date_vals[1]] + timedelta(days=1))))

    # Compute Hq
    _hqr = ulfunc.measures.Hq(_rightdata['act'][_dateinx].values, q=95)
    _hql = ulfunc.measures.Hq(_leftdata['act'][_dateinx].values, q=95)

    # Scatter plot
    _fig = px.scatter(_data[_dateinx], x='int', y='use', color='arm')
    _fig.update_traces(marker_size=10, opacity=0.5)
    _fig.update_layout(go.Layout(
        template='plotly_white',
        xaxis_title='Intensity (' + re.search(r'\s-\s.*\*\s(.*).*', measure_name).groups()[0] + ')',
        yaxis_title='Use (' + re.search(r'\s-\s(.*)\s\*.*', measure_name).groups()[0] + ')',
        legend_title="Upper limbs",
        font=dict(
            family="Helvetica",
            size=16,
            color="black"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    ))
    # Updat axes
    _xrange = 1.05 * np.array([-1, 1]) * np.max(_data['int'])
    _yrange = [-0.05, 1.05]
    _fig.update_xaxes(showline=True, linewidth=1, linecolor='black', range=_xrange)
    _fig.update_yaxes(showline=True, linewidth=1, linecolor='black', range=_yrange)

    return _fig, f'Hq (Right) = {_hqr:3.2f}', f'Hq (Left) = {_hql:3.2f}', subjdata_ulfavrg

# Function to generate the RUF plot.
def gen_ruf_plot(measure_name, subj_name, date_vals, subjdata_ulfavrg, datadetails):
    """Generate RUF plot.
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Left Wrist']
    
    # Get subject dates.
    _subjdates = _get_subject_dates(datadetails['datadir'], subj_name)
    # Check if subject data is None. If so, get the data.
    if subjdata_ulfavrg is None:
        subjdata_ulfavrg = get_ulfavrg_data_for_subject(datadetails, subj_name)
    elif subjdata_ulfavrg['subject'][0] != subj_name:
        subjdata_ulfavrg = get_ulfavrg_data_for_subject(datadetails, subj_name)

    # Find which use and int columns are to be used for the display.
    all_cols = get_useintact_columns_short(datadetails)
    _col = [_k.split('-')
            for _k, _v in all_cols.items()
            if measure_name == _v][0]

    # Get right and left data
    _data = pd.DataFrame.from_dict({'TimeStamp': subjdata_ulfavrg['TimeStamp'],
                                    'right': subjdata_ulfavrg[rlbl][_col[0]][_col[1]].values,
                                    'left': subjdata_ulfavrg[llbl][_col[0]][_col[1]].values,
                                    'lioa': subjdata_ulfavrg['LatIndexoA'][_col[0]][_col[1]].values},)

    # Get date indices.
    _dateinx = ((_data['TimeStamp'] >= _subjdates[date_vals[0]])
                & (_data['TimeStamp'] < (_subjdates[date_vals[1]] + timedelta(days=1))))

    # Scatter plot
    _fig = px.scatter(_data[_dateinx], x='right', y='left')
    _fig.update_traces(marker_size=10, opacity=0.25, marker_color='green')
    _measure_label = re.search(r'\s-\s(.*)$', measure_name).groups()[0]
    _fig.update_layout(go.Layout(
        template='plotly_white',
        xaxis_title=f"Right - {_measure_label}",
        yaxis_title=f"Left - {_measure_label}",
        font=dict(
            family="Helvetica",
            size=16,
            color="black"
        ),
        showlegend=False
    ))
    # Update axes
    if _col[0] == 'use':
        _range = [-0.05, 1.05]
    else:
        _range = np.array([-0.05, 1.05]) * np.nanmax(_data[['right', 'left']].values)
    _fig.update_xaxes(showline=True, linewidth=1, linecolor='black', range=_range)
    _fig.update_yaxes(showline=True, linewidth=1, linecolor='black', range=_range)
    # Add the x = y line
    _fig.add_trace(
        go.Scatter(x=_range, y=_range, mode="lines",
                   line=dict(color="red", width=2, dash='dot'))
    )
    _fig['data'][0]['showlegend'] = False
    
    # Compute Laterality Index
    _lioa = (np.nanmean(_data[_dateinx]['lioa'].values)
             if not np.all(np.isnan(_data[_dateinx]['lioa'].values))
             else np.NaN)

    return _fig, f'Laterality Index: {_lioa:+1.3f}', subjdata_ulfavrg

# Function to generate summary temporal plot.
def gen_summ_temporal_plot(tab_value, subj_name, date_vals, subjdata_summary, datadetails):
    """Generated summary temporal plot.
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Left Wrist']
    
    # Get subject dates.
    _subjdates = _get_subject_dates(datadetails['datadir'], subj_name)
    # Check if subject data is None. If so, get the data.
    if subjdata_summary is None:
        subjdata_summary = get_summary_data_for_subject(datadetails, subj_name)
    if subjdata_summary['hq']['subject'][0] != subj_name:
        subjdata_summary = get_ulfavrg_data_for_subject(datadetails, subj_name)

    # Show the appropriate graph depending on the selected tab.
    winsz = int(re.search(r'tab-([0-9]*)-graph', tab_value).groups(0)[0]) * 60
    start_date = _subjdates[date_vals[0]]
    
    # Create figure
    _fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         vertical_spacing=0.1,
                         subplot_titles=("UL Activity", "Laterality Index"))
    _fig.update_annotations(font_size=22)
    
    # Hq
    _hqlbl = dcfg.TEMPORAL_SUMM_MEASURES[datadetails['data_params'].sensor]['Hq']
    _inx = subjdata_summary['hq']['summwin'] == winsz
    _fig.add_trace(
        go.Scatter(x=subjdata_summary['hq']['TimeStamp'][_inx],
                   y=subjdata_summary['hq'][rlbl][_hqlbl][_inx],
                   name="Hq (Right)"),
        row=1, col=1
    )
    _fig.add_trace(
        go.Scatter(x=subjdata_summary['hq']['TimeStamp'][_inx],
                   y=subjdata_summary['hq'][llbl][_hqlbl][_inx],
                   name="Hq (Left)"),
        row=1, col=1
    )
    _fig.update_traces(mode='lines+markers',
                       marker=dict(size=5, line=dict(width=1, color='DarkSlateGrey')),
                       row=1, col=1)
    _fig.update_layout(
        template='plotly_white',
        font=dict( 
            family="Helvetica",
            size=18,
            color="Black"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0
        )
    )
    _fig.update_xaxes(showline=True, linewidth=1, linecolor='black',
                      range=[start_date - timedelta(days=2),
                             start_date + timedelta(days=7)], row=1, col=1)
    _fig.update_yaxes(showline=True, linewidth=1, linecolor='black', row=1, col=1)

    # LI
    _lilbl = dcfg.TEMPORAL_SUMM_MEASURES[datadetails['data_params'].sensor]['LI']
    _inx = subjdata_summary['li']['summwin'] == winsz
    _fig.add_trace(
        go.Scatter(x=subjdata_summary['li']['TimeStamp'][_inx],
                   y=subjdata_summary['li']['LatIndex']['int'][_lilbl][_inx],
                   name="Laterality Index",
                   line=dict(color='rgba(0, 0, 0, 0.6)')),
        row=2, col=1
    )
    _fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="black", row=2, col=1)
    _fig.add_hrect(y0=0, y1=1.2, line_width=0, fillcolor="green", opacity=0.05, row=2, col=1)
    _fig.add_hrect(y0=0, y1=-1.2, line_width=0, fillcolor="red", opacity=0.05, row=2, col=1)
    _fig.update_traces(mode='lines+markers',
                       marker=dict(size=5, line=dict(width=1, color='DarkSlateGrey')),
                       row=2, col=1)
    _fig.update_xaxes(showline=True, linewidth=2, linecolor='black',
                      range=[start_date - timedelta(days=2),
                             start_date + timedelta(days=7)], row=2, col=1)
    _fig.update_yaxes(showline=True, linewidth=2, linecolor='black',
                      range=[-1.1, 1.1], row=2, col=1)
    _fig.update_layout(height=600)

    return _fig, subjdata_summary

# Function to generate average temporal plot.
def gen_avrg_temporal_plot(use_val, int_val, act_val, li_val, subj_name, date_vals,
                           subjdata_ulfavrg, datadetails):
    """Generated average temporal plot.
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Left Wrist']
    
    # Get subject dates.
    _subjdates = _get_subject_dates(datadetails['datadir'], subj_name)

    # Check if subject data is None. If so, get the data.
    if subjdata_ulfavrg is None:
        subjdata_ulfavrg = get_ulfavrg_data_for_subject(datadetails, subj_name)
    elif subjdata_ulfavrg['subject'][0] != subj_name:
        subjdata_ulfavrg = get_ulfavrg_data_for_subject(datadetails, subj_name)

    # Find which use and int columns are to be used for the display.
    all_cols = get_useintact_columns_short(datadetails)
    _ucol = [_k.split('-')[1] for _k, _v in all_cols.items() if use_val == _v][0]
    _icol = [_k.split('-')[1] for _k, _v in all_cols.items() if int_val == _v][0]
    _acol = [_k.split('-')[1] for _k, _v in all_cols.items() if act_val == _v][0]
    
    _lidetails = [_k for _k, _v in all_cols.items() if li_val == _v][0].split('-')
    
    # Get right and left data
    _rightdata = pd.DataFrame.from_dict({'TimeStamp': subjdata_ulfavrg['TimeStamp'],
                                         'use': subjdata_ulfavrg[rlbl]['use'][_ucol].values,
                                         'int': subjdata_ulfavrg[rlbl]['int'][_icol].values,
                                         'act': subjdata_ulfavrg[rlbl]['act'][_acol].values,
                                         'arm': ['Right'] * len(subjdata_ulfavrg[rlbl]['int'][_icol].values)})
    _leftdata = pd.DataFrame.from_dict({'TimeStamp': subjdata_ulfavrg['TimeStamp'],
                                        'use': subjdata_ulfavrg[llbl]['use'][_ucol].values,
                                        'int': subjdata_ulfavrg[llbl]['int'][_icol].values,
                                        'act': subjdata_ulfavrg[llbl]['act'][_acol].values,
                                        'arm': ['Left'] * len(subjdata_ulfavrg[rlbl]['int'][_icol].values)})
    _data = pd.concat([_rightdata, _leftdata], axis=0, ignore_index=True)
    
    # Get date indices.
    _dateinx = ((_data['TimeStamp'] >= _subjdates[date_vals[0]])
                & (_data['TimeStamp'] <= (_subjdates[date_vals[1]] + timedelta(days=1))))
    
    # Create figure
    _fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                         vertical_spacing=0.025,
                         subplot_titles=("UL Use",
                                         "Intensity",
                                         "Activity",
                                         "Laterality Index"))
    _fig.update_annotations(font_size=22)
    
    # Use
    _rinx = _data['arm'] == 'Right'
    _linx = _data['arm'] == 'Left'
    _fig.add_trace(
        go.Scatter(x=_data[_rinx]['TimeStamp'][_dateinx],
                   y=_data[_rinx]['use'][_dateinx],
                   name='Right Use',
                   legendgroup='1',
                   line=dict(color='rgba(0, 0, 255, 0.6)')),
        row=1, col=1
    )
    _fig.add_trace(
        go.Scatter(x=_data[_linx]['TimeStamp'][_dateinx],
                   y=-_data[_linx]['use'][_dateinx],
                   name='Left use',
                   legendgroup='1',
                   line=dict(color='rgba(255, 0, 0, 0.6)')),
        row=1, col=1
    )
    _fig.update_yaxes(showline=True, linewidth=2, linecolor='black',
                      row=1, col=1)
    
    # Intensity
    _fig.add_trace(
        go.Scatter(x=_data[_rinx]['TimeStamp'][_dateinx],
                   y=_data[_rinx]['int'][_dateinx],
                   name='Right int.',
                   legendgroup='2',
                   line=dict(color='rgba(0, 0, 255, 0.6)')),
        row=2, col=1
    )
    _fig.add_trace(
        go.Scatter(x=_data[_linx]['TimeStamp'][_dateinx],
                   y=-_data[_linx]['int'][_dateinx],
                   name='Left int.',
                   legendgroup='2',
                   line=dict(color='rgba(255, 0, 0, 0.6)')),
        row=2, col=1
    )
    _fig.update_yaxes(showline=True, linewidth=2, linecolor='black',
                      row=2, col=1)
    # Intensity max.
    _intmax = np.nanmax([np.nanmax(_data[_rinx]['int'][_dateinx]),
                         np.nanmax(_data[_linx]['int'][_dateinx])])
    
    # Activity
    _fig.add_trace(
        go.Scatter(x=_data[_rinx]['TimeStamp'][_dateinx],
                   y=_data[_rinx]['act'][_dateinx],
                   name='Right act.',
                   legendgroup='3',
                   line=dict(color='rgba(0, 0, 255, 0.6)')),
        row=3, col=1
    )
    _fig.add_trace(
        go.Scatter(x=_data[_linx]['TimeStamp'][_dateinx],
                   y=-_data[_linx]['act'][_dateinx],
                   name='Left act.',
                   legendgroup='3',
                   line=dict(color='rgba(255, 0, 0, 0.6)')),
        row=3, col=1
    )
    _fig.update_yaxes(showline=True, linewidth=2, linecolor='black',
                      row=3, col=1)
    # Activity max.
    _actmax = np.nanmax([np.nanmax(_data[_rinx]['act'][_dateinx]),
                         np.nanmax(_data[_linx]['act'][_dateinx])])

    # Laterality Index
    _dateinx = ((subjdata_ulfavrg['TimeStamp'] >= _subjdates[date_vals[0]])
                & (subjdata_ulfavrg['TimeStamp'] <= (_subjdates[date_vals[1]] + timedelta(days=1))))
    _fig.add_trace(
        go.Scatter(x=subjdata_ulfavrg['TimeStamp'][_dateinx],
                   y=subjdata_ulfavrg['LatIndex'][_lidetails[0]][_lidetails[1]][_dateinx],
                   name='Lat. Index',
                   legendgroup='4',
                   line=dict(color='rgba(0, 0, 0, 0.6)')),
        row=4, col=1
    )
    _fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="black", row=4, col=1)
    _fig.add_hrect(y0=0, y1=1.2, line_width=0, fillcolor="green", opacity=0.05, row=4, col=1)
    _fig.add_hrect(y0=0, y1=-1.2, line_width=0, fillcolor="red", opacity=0.05, row=4, col=1)
    _fig.update_yaxes(showline=True, linewidth=2, linecolor='black', row=4, col=1)
    _fig.update_xaxes(showline=True, linewidth=2, linecolor='black', row=4, col=1)
    _fig.update_layout(template='plotly_white')
    _fig.update_layout(height=1000)
    _xrange = [_subjdates[date_vals[0]],
               _subjdates[date_vals[1]] + timedelta(days=1  )]
    _fig.update_layout(
        legend_tracegroupgap=180,
        font=dict(
            family="Helvetica",
            size=16,
            color="black"
        ),
        xaxis1_range=_xrange,
        xaxis2_range=_xrange,
        xaxis3_range=_xrange,
        xaxis4_range=_xrange,
        yaxis1_range=[-1.2, 1.2],
        yaxis2_range=np.array([-1.1, 1.1]) * _intmax,
        yaxis3_range=np.array([-1.1, 1.1]) * _actmax,
        yaxis4_range=[-1.2, 1.2],
    )
    return _fig, subjdata_ulfavrg

# Function to generate summary temporal plot for the clinical version of the
# dashboard.
def gen_clinical_summary_temporal_plot(subj_name, subjdata_summary, datadetails):
    """Generated summary temporal plot.
    """
    # Right and left labels.
    rlbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Right Wrist']
    llbl = dcfg.SUPPORTED_SENSOR_LOCATIONS[datadetails['data_params'].sensor]['Left Wrist']
    
    # Get subject dates.
    _subjdates = _get_subject_dates(datadetails['datadir'], subj_name)
    
    # Check if subject data is None. If so, get the data.
    if subjdata_summary is None:
        subjdata_summary = get_summary_data_for_subject(datadetails, subj_name)
    if subjdata_summary['hq']['subject'][0] != subj_name:
        subjdata_summary = get_ulfavrg_data_for_subject(datadetails, subj_name)

    # Show the appropriate graph depending on the selected tab.
    winsz = 24 * 60
    start_date = _subjdates[0]
    
    # Create figure
    _fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         vertical_spacing=0.1,
                         subplot_titles=("How much are the limbs used?",
                                         "Percentage of affect limb use"))
    _fig.update_annotations(font_size=26)
    
    # Hq
    _hqlbl = dcfg.TEMPORAL_SUMM_MEASURES[datadetails['data_params'].sensor]['Hq']
    _inx = subjdata_summary['hq']['summwin'] == winsz
    _fig.add_trace(
        go.Scatter(x=subjdata_summary['hq']['TimeStamp'][_inx],
                   y=subjdata_summary['hq'][rlbl][_hqlbl][_inx],
                   name="Right"),
        row=1, col=1
    )
    _fig.add_trace(
        go.Scatter(x=subjdata_summary['hq']['TimeStamp'][_inx],
                   y=subjdata_summary['hq'][llbl][_hqlbl][_inx],
                   name="Left"),
        row=1, col=1
    )
    _fig.update_traces(mode='lines+markers',
                       marker=dict(size=10, line=dict(width=2, color='DarkSlateGrey')),
                       row=1, col=1)
    _fig.update_layout(
        template='plotly_white',
        font=dict( 
            family="Helvetica",
            size=22,
            color="Black"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0
        )
    )
    _fig.update_xaxes(showline=True, linewidth=1, linecolor='black',
                      range=[start_date - timedelta(days=1),
                             start_date + timedelta(days=15)], row=1, col=1)
    _fig.update_yaxes(showline=True, linewidth=1, linecolor='black', row=1, col=1)

    # LI
    _lilbl = dcfg.TEMPORAL_SUMM_MEASURES[datadetails['data_params'].sensor]['LI']
    _inx = subjdata_summary['li']['summwin'] == winsz
    _fig.add_trace(
        go.Bar(x=subjdata_summary['li']['TimeStamp'][_inx],
               y=(subjdata_summary['li']['LatIndex']['int'][_lilbl][_inx] + 1) * 50,
               name="Percentage use"),
        row=2, col=1
    )
    _fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="black", row=2, col=1)
    _fig.update_xaxes(showline=True, linewidth=2, linecolor='black',
                      range=[start_date - timedelta(days=1),
                             start_date + timedelta(days=15)], row=2, col=1)
    _fig.update_yaxes(showline=True, linewidth=2, linecolor='black',
                      range=[-1, 105], row=2, col=1)
    _fig.update_layout(height=800)

    return _fig, subjdata_summary


# Function to geneate the daily details for the clinical version of the dashboard.
def get_clinical_daily_details_tab(subj_name, subjdata_ulfavrg, datadetails):
    """Creates the layout for daily details of the dashboard for clinical purposes.
    """
    # Gene
    pass
