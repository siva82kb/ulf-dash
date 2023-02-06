"""Main script for the UL functioning dashboard for clinical use.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 11 Nov 2022
"""

import sys

import plotly.graph_objects as go
from dash import Dash, Input, Output
from dash import html, dcc

from dashcallbacks import (gen_clinical_summary_temporal_plot,
                           update_subj_table)
from dashlayouts import setup_clinical_app_layout
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
    
    retval, SUBJDATA_ULFAVRG, SUBJDATA_SUMMARY = update_subj_table(subj_name,
                                                                   SUBJDATA_ULFAVRG,
                                                                   SUBJDATA_SUMMARY,
                                                                   DATADIR)
    return retval


#
# Overall measure temporal plot tab selection callback --> Update temporal plot.
@app.callback(
    Output('tab-content-clinical-summary', 'children'),
    Input('clinical-summary-temporal-plot-tabs', 'value'),
    Input('subj-name-dropdown', 'value'))
def callback_clinical_summary_temporal_plot_tab_selection(tab_value, subj_name):
    """Handle the selection of the tab for the overall measure temporal plot.
    """
    global SUBJDATA_SUMMARY
    global DATADETAILS
    fig_config = {
        'toImageButtonOptions': {
            'format': 'svg', # one of png, svg, jpeg, webp
            'filename': 'custom_image',
        }
    }
    if tab_value == 'tab-daily-summary-graph':
        fig, SUBJDATA_SUMMARY = gen_clinical_summary_temporal_plot(subj_name,
                                                                   SUBJDATA_SUMMARY,
                                                                   DATADETAILS)
        return dcc.Graph(figure=fig, config=fig_config)
    else:
        return dcc.Graph()


if __name__ == '__main__':
    # The second system argument is the data folder
    DATADIR = sys.argv[1]
    
    # Initialize the subject data to None.
    SUBJDATA_ULFAVRG = None
    SUBJDATA_SUMMARY = None

    # Gather data details.
    DATADETAILS = gather_data_details(DATADIR)

    # Setup the app.
    app.layout = setup_clinical_app_layout(DATADETAILS)

    # Run the dashboard app
    app.run_server(debug=True)
