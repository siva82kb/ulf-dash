"""Main script for the UL functioning dashboard.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 26 Oct 2022
"""

import sys

import plotly.graph_objects as go
from dash import Dash, Input, Output

from dashcallbacks import (gen_avrg_temporal_plot,
                           gen_clinical_summary_temporal_plot, gen_ruf_plot,
                           gen_summ_temporal_plot, gen_uvi_plot,
                           update_avrg_measure_dropdown_from_use,
                           update_avrg_use_measure_dropdown,
                           update_date_range_slider, update_measure_dropdown,
                           update_subj_table)
from dashlayouts import setup_research_app_layout
from dashsupport import gather_data_details

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


# TODO:
# 1. Choose analysis param dict from a dropdown.
# 2. Remove the possibility for overlapping time windows for average calculation.

app = Dash(__name__, external_stylesheets=external_stylesheets)

# ################## #
# Dahsboard Callbaks #
# ################## #
#
# Subject Selection Dropbox Callback --> Update Table
@app.callback(
    Output('subj-name-table', 'children'),
    Output('subj-days-table', 'children'),
    Input('subj-name-dropdown', 'value'))
def callback_update_table_from_subj_selection(subj_name):
    """Callback to update the table with subject details.
    """
    global SUBJDATA_ULFAVRG
    global SUBJDATA_SUMMARY
    global DATADIR
    global DATADETAILS
    
    retval, SUBJDATA_ULFAVRG, SUBJDATA_SUMMARY = update_subj_table(subj_name,
                                                                   SUBJDATA_ULFAVRG,
                                                                   SUBJDATA_SUMMARY,
                                                                   DATADIR)
    return retval

#
# Subject Selection Dropbox Callback --> Update Date SLider
@app.callback(
    Output('date-selector-slider', "min"),
    Output('date-selector-slider', "max"),
    Output('date-selector-slider', "value"),
    Output('date-selector-slider', "marks"),
    Output('date-selector-label', 'children'),
    Input('subj-name-dropdown', 'value'))
def callback_date_range_selector_from_subj_selection(subj_name):
    """Callback to update the date range slider from the subject details.
    """
    global DATADIR

    return update_date_range_slider(subj_name, DATADIR)

#
# Waist Filter Checkbox -- > Update UVI and RUF Measure Selection Dropdowns.
@app.callback(
    Output('uvi-measures-dropdown', 'options'),
    Output('uvi-measures-dropdown', 'value'),
    Output('ruf-measures-dropdown', 'options'),
    Output('ruf-measures-dropdown', 'value'),
    Input('waist-filter-checkbox', 'value'))
def callback_waist_filter_measure_selection_dropdown(waist_filter_on):
    """Callback to update the measure selection dropdowns based on the waist filter.
    """
    global DATADETAILS
    return update_measure_dropdown(waist_filter_on, DATADETAILS)

#
# UVI Measure Selection Dropbox Callback --> Update UVI plot.
@app.callback(
    Output('uvi-scatter-plot', "figure"),
    Output('right-hq-value', "children"),
    Output('left-hq-value', "children"),
    Input('uvi-measures-dropdown', 'value'),
    Input('subj-name-dropdown', 'value'),
    Input('date-selector-slider', 'value'))
def callback_uvi_figure_from_measure_selection(measure_name, subj_name, date_vals):
    """Callback to update the UVI scatter plot.
    """
    global SUBJDATA_ULFAVRG
    global DATADETAILS

    fig, rinfo, linfo, SUBJDATA_ULFAVRG = gen_uvi_plot(measure_name, subj_name,
                                                       date_vals, SUBJDATA_ULFAVRG,
                                                       DATADETAILS)

    return fig, rinfo, linfo

#
# RUF Measure Selection Dropbox Callback --> Update UVI plot.
@app.callback(
    Output('ruf-scatter-plot', "figure"),
    Output('li-value', "children"),
    Input('ruf-measures-dropdown', 'value'),
    Input('subj-name-dropdown', 'value'),
    Input('date-selector-slider', 'value'))
def callback_ruf_figure_from_measure_selection(measure_name, subj_name, date_vals):
    """Callback to update the RUF scatter plot.
    """
    global SUBJDATA_ULFAVRG
    global DATADETAILS

    fig, info, SUBJDATA_ULFAVRG = gen_ruf_plot(measure_name, subj_name, date_vals,
                                               SUBJDATA_ULFAVRG, DATADETAILS)

    return fig, info


#
# Overall measure temporal plot tab selection callback --> Update temporal plot.
@app.callback(
    Output('hq-li-tabs-content-graph', 'figure'),
    Input('summ-measure-temporal-plot-tabs', 'value'),
    Input('subj-name-dropdown', 'value'),
    Input('date-selector-slider', 'value'))
def callback_summ_overall_measure_temporal_plot_tab_selection(tab_value, subj_name, date_vals): 
    """Handle the selection of the tab for the overall measure temporal plot.
    """
    global SUBJDATA_SUMMARY
    global DATADETAILS

    fig, SUBJDATA_SUMMARY = gen_summ_temporal_plot(tab_value, subj_name, date_vals,
                                                   SUBJDATA_SUMMARY, DATADETAILS)
    return fig


#
# Waist Filter Checkbox -- > Update UVI and RUF Measure Selection Dropdowns.
@app.callback(
    Output('use-templot-dropdown', 'options'),
    Output('use-templot-dropdown', 'value'),
    Input('waist-filter-checkbox', 'value'))
def callback_waist_filter_avg_measure_selection_dropdown(waist_filter_on):
    """Callback to update the average measure selection dropdowns based on the waist filter.
    """
    global DATADETAILS
    return update_avrg_use_measure_dropdown(waist_filter_on, DATADETAILS)


#
# # Avrg. measures dropdown update based on use dropdown selection.
@app.callback(
    Output('int-templot-dropdown', 'options'),
    Output('int-templot-dropdown', 'value'),
    Output('act-templot-dropdown', 'options'),
    Output('act-templot-dropdown', 'value'),
    Output('li-templot-dropdown', 'options'),
    Output('li-templot-dropdown', 'value'),
    Input('use-templot-dropdown', 'value'),
    Input('waist-filter-checkbox', 'value'))
def callback_avg_measure_selection_dropdown_from_use_dropdown(use_val, waist_filter_on):
    """Callback to update the average measure selection dropdowns based on the use dropdown.
    """
    global DATADETAILS
    return update_avrg_measure_dropdown_from_use(use_val, waist_filter_on, DATADETAILS)


#
# Overall measure temporal plot tab selection callback --> Update temporal plot.
@app.callback(
    Output('avg-useintact-graph', 'figure'),
    Input('use-templot-dropdown', 'value'),
    Input('int-templot-dropdown', 'value'),
    Input('act-templot-dropdown', 'value'),
    Input('li-templot-dropdown', 'value'),
    Input('date-selector-slider', 'value'),
    Input('subj-name-dropdown', 'value'))
def callback_avg_temporal_plot_measure_selection(use_val, int_val, act_val, li_val,
                                                 date_vals, subj_name):
    """Handle the selection of the tab for the overall measure temporal plot.
    """
    global SUBJDATA_ULFAVRG
    global DATADETAILS

    # make sure there is something selected
    if use_val is None:
        return go.Figure()
    
    fig, SUBJDATA_ULFAVRG = gen_avrg_temporal_plot(use_val, int_val, act_val, li_val,
                                                   subj_name, date_vals,
                                                   SUBJDATA_ULFAVRG, DATADETAILS)
    return fig

# # Clinical version callbacks
# #
# # Overall measure temporal plot tab selection callback --> Update temporal plot.
# @app.callback(
#     Output('act-reluse-tabs-content-graph', 'figure'),
#     Input('clinical-summary-temporal-plot-tabs', 'value'),
#     Input('subj-name-dropdown', 'value'))
# def callback_clinical_summary_temporal_plot_tab_selection(tab_value, subj_name):
#     """Handle the selection of the tab for the overall measure temporal plot.
#     """
#     global SUBJDATA_SUMMARY
#     global DATADETAILS

#     if tab_value == 'tab-daily-summary-graph':
#         fig, SUBJDATA_SUMMARY = gen_clinical_summary_temporal_plot(subj_name,
#                                                                    SUBJDATA_SUMMARY,
#                                                                    DATADETAILS)
#     return fig


if __name__ == '__main__':
    # The second system argument is the data folder
    DATADIR = sys.argv[1]
    
    # Initialize the subject data to None.
    SUBJDATA_ULFAVRG = None
    SUBJDATA_SUMMARY = None

    # Gather data details.
    DATADETAILS = gather_data_details(DATADIR)

    # Setup the app.
    app.layout = setup_research_app_layout(DATADETAILS)

    # Run the dashboard app
    app.run_server(debug=True)
