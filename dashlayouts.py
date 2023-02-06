"""
Module containing different functions to generate different layouts for the 
UL functioning dashboard.

Author: Sivakumar Balasubramanian
Email: siva82kb@cmcvellore.ac.in
Date: 01 Nov 2022
"""

from dash import html, dcc
from dashsupport import (get_useintact_columns_short,)

DEBUG_BORDER = '0px black solid'

def common_elements(datadetails):
    # Define different components of the dashboard
    # Header
    header = html.Div(
        [html.H1('Upper-Limb Functioning Dashboard',
                 style={'margin': '0px'})],
        id="header",
        style={'textAlign': 'center',
               'padding': '1% 0%',
               'backgroundColor': '#333',
               'color': '#fff',
               'margin': '0.% auto',
               'width': '100%'}
    )
    
    #
    # Footer
    footer = html.Div(
        [html.P("Developed through the ARTHub initiative by SHRS, Univ. of Queensland",
                style={'fontSize': '15px',
                       'color': '#555'})],
        id="footer",
        style={'textAlign': 'right',
               'border-top': '1px #888 solid',
               'padding': '0.5% 0%',
               'margin': '0 auto',
               'margin-top': '50px',
               'width': '100%',
               'clear': 'both'}
    )
    
    #
    # Data details row.
    _rowtitle = html.Div([
        html.P((" | ".join((datadetails['data_params'].sensor,
                            datadetails['data_params'].data_type,
                            ', '.join(datadetails['data_params'].locs)))),
                style={'fontSize': '20px',
                       'margin': '0%',
                       'padding': '0% 10px'}),
        ],
        style={'backgroundColor': '#666',
               'color': '#fff',
               'margin-bottom': '0.5%'}
    )
    datadetailsrow = html.Div([
        _rowtitle,
        ],
        style={'width': '100%',
               'margin': '0% 1% 0% 0%',
               'padding': '0%',}
    )
    
    #
    # Subject Dropdown box and Details.
    _subjs = list(datadetails['subjs'].keys())
    # Subject selection
    _subjsel = html.Div([
        html.H5('Select Subject: '),
        dcc.Dropdown(_subjs, _subjs[0], id='subj-name-dropdown',
                     clearable=False)
        ],
        style={'width': '49%',
               'margin': '0% 1% 0% 0%',
               'padding': '0%',
               'float': 'left'}
    )
    # Subjects details table
    _subjtable = html.Div([
        html.Table([
            html.Tr([html.Td([html.B('Name:', style={'font-size': '20px'})],
                             style={'border': 'none',
                                    'padding': '10px'}),
                     html.Td(id='subj-name-table', 
                             style={'font-size': '20px',
                                    'border': 'none',
                                    'padding': '10px'})],
                    style={'border': 'none'}),
            html.Tr([html.Td([html.B('Days of recording: ', style={'font-size': '20px'})],
                             style={'border': 'none',
                                    'padding': '10px'}),
                     html.Td(id='subj-days-table',
                             style={'font-size': '20px',
                                    'border': 'none'})],
                    style={'border': 'none',
                           'padding': '10px'}),],
            style={'margin': '0% 0% 0% 1%',
                   'width': '49%',
                   'float': 'right',
                   'backgroundColor': 'rgba(220, 220, 220, 0.3)'}
        )],
        id="subj-data-table",
        style={})
    # Overall element
    subj_details_row = html.Div(
        [_subjsel, _subjtable],
        id="subj-selection-details-div",
        style={'height': '110px',
               'margin': '0px 0px 20px 0px',
               'border': DEBUG_BORDER}
    )

    return header, footer, datadetailsrow, subj_details_row


def setup_research_app_layout(datadetails):
    """Creates the layout for the dashboard for research purposes.
    """
    #
    # Get common UI elements.
    header, footer, datadetailsrow, subj_details_row = common_elements(datadetails)

    #
    # Controls for choosing data
    data_controls_row = html.Div(
        [html.H5('Select Date:', id='date-selector-label',
                 style={'float': 'left',
                        'width': '15%'}),
         html.Div([dcc.RangeSlider(0, 20, 1, value=[5, 15],
                                   id='date-selector-slider')],
                  style={'float': 'left',
                         'width': '65%',
                         'margin-top': '15px',
                         'margin-left': '2%'}),
         dcc.Checklist([' Use Waist Filter'] 
                       if 'W' in datadetails['data_params'].locid
                       else [],
                       [],
                       id='waist-filter-checkbox',
                       inline=True,
                       style={'float': 'right',
                              'fontSize': '22px',
                              'width': '15%'})
        ],
        style={'clear': 'both',
               'margin': '0 auto',
               'height': '50px',
               'width': '100%',
               'border': DEBUG_BORDER}
    )

    #
    # UVI, RUF plot summary
    # Get the list of subjectts
    all_cols = get_useintact_columns_short(datadetails)
    act_cols_labels = [_v for _k, _v in all_cols.items() if 'act-' in _k]
    # UVI Plot
    _hqsec = html.Div(
        [html.Div(html.H5('Use vs. Intensity Plot', style={'color': '#002880'}),
                  style={"backgroundColor": '#e6f2ff', 'color': "#000", 'padding': '3px', 'textAlign': 'center'}),
         html.Div(html.H6("Select measure: ", style={'color': '#002880'}),
                  style={'width': '24%', 'float': 'left'}),
         html.Div(dcc.Dropdown(act_cols_labels, act_cols_labels[0], id='uvi-measures-dropdown', clearable=False),
                  style={'float': 'right', 'margin-top': '5px', 'width': '74%'}),
         html.Div([html.Div(html.H5(id='left-hq-value', style={'textAlign': 'center', 'color': '#f00', 'padding': '0%', 'margin': '0%'}),
                            style={'float': 'left', 'width': '49%', 'backgroundColor': '#fff'}),
                   html.Div(html.H5(id='right-hq-value', style={'textAlign': 'center', 'color': '#00f', 'padding': '0%', 'margin': '0%'}),
                            style={'float': 'right', 'width': '49%'})],
                  style={'clear': 'both','width': '100%', 'padding': '0%', 'border': DEBUG_BORDER}),
         html.Div(dcc.Graph(id='uvi-scatter-plot', responsive=True,), style={'clear': 'both', 'margin-top': '5px'}),],
        style={'border': DEBUG_BORDER, 'width': '67%', 'height': '550px', 'float': 'left'}
    )
    # RUF Plot
    all_cols_labels = [_v for _k, _v in all_cols.items()]
    _rqsec = html.Div(
        [html.Div(html.H5('Rel. UL Functioning Plot', style={'color': '#991f00'}),
                  style={"backgroundColor": '#ffebe6', 'color': "#000", 'padding': '3px', 'textAlign': 'center'}),
         html.Div(html.H6("Select measure: ",
                          style={'color': '#991f00'}), style={'width': '32%', 'float': 'left'}),
         html.Div(dcc.Dropdown(all_cols_labels, all_cols_labels[0], id='ruf-measures-dropdown', clearable=False),
                  style={'float': 'right', 'margin-top': '5px', 'width': '68%'}),
         html.Div(html.H5(id='li-value', style={'textAlign': 'center', 'color': '#319e24', 'padding': '0%', 'margin': '0%'}),
                  style={'clear': 'both', 'width': '100%', 'padding': '0%', 'border': DEBUG_BORDER}),
         html.Div(dcc.Graph(id='ruf-scatter-plot', responsive=True), style={'clear': 'both', 'margin-top': '5px'}),],
        style={'border': DEBUG_BORDER, 'width': '30%', 'height': '550px', 'float': 'right'}
    )
    summ_plot = html.Div([_hqsec, _rqsec], style={'width': '100%', 'margin': '40px 0px 0px 0px', 'height': '600px'})

    #
    # Measures temporal evolution plots.
    FIG_CONFIG = {
        'toImageButtonOptions': {
            'format': 'svg', # one of png, svg, jpeg, webp
            'filename': 'custom_image',
        }
    }
    measures_evolution_row = html.Div(
        [html.Div(html.H5('Summary Measures Temporal Plots', style={'color': '#fff'}),
                  style={'width': '100%', 'backgroundColor': '#000', 'padding': '3px', 'textAlign': 'center'}),
         dcc.Tabs(id="summ-measure-temporal-plot-tabs", value='tab-1-graph',
                  children=[dcc.Tab(label='Daily Summary', value='tab-24-graph',
                                    className='custom-tab', selected_className='custom-tab--selected'),
                            dcc.Tab(label='12 hours Summary', value='tab-12-graph',
                                    className='custom-tab', selected_className='custom-tab--selected'),
                            dcc.Tab(label='6 hours Summary', value='tab-6-graph',
                                    className='custom-tab', selected_className='custom-tab--selected'),
                            dcc.Tab(label='Hourly Summary', value='tab-1-graph',
                                    className='custom-tab', selected_className='custom-tab--selected'),],
                  style={'margin-top': '2px'}),
         html.Div(dcc.Graph(id='hq-li-tabs-content-graph', config=FIG_CONFIG),
                  style={'textAlign': 'center'})],
        style={'clear': 'both', 'border': DEBUG_BORDER, 'height': '700px', 'width': '100%'}
    )

    #
    # Avaerage measures temporal evolution plots.
    avrg_evolution_row = html.Div(
        [html.Div(html.H5('Average UL Use, Intensity, and Activtiy Temporal Plots', style={'color': '#fff'}),
                  style={'width': '100%', 'backgroundColor': '#020966', 'padding': '3px', 'textAlign': 'center'}),
         html.Div([html.Div([html.Div(html.H6('Use: ', style={'color': '#002880'}), style={'float': 'left', 'width': '24%'}),
                             html.Div(dcc.Dropdown([], None, id='use-templot-dropdown', clearable=False),
                                      style={'float': 'right', 'width': '74%', 'margin-top': '7px'})],
                            style={'width': '18%', 'float': 'left', 'margin-left': '1%', 'margin-right': '1%'}),
                   html.Div([html.Div(html.H6('Intensity: ', style={'color': '#002880'}), style={'float': 'left', 'width': '24%'}),
                             html.Div(dcc.Dropdown([], None, id='int-templot-dropdown', clearable=False),
                                      style={'float': 'right', 'width': '74%', 'margin-top': '7px'})],
                            style={'width': '23%', 'float': 'left', 'margin-left': '1%', 'margin-right': '1%'}),
                   html.Div([html.Div(html.H6('Activity: ', style={'color': '#002880'}), style={'float': 'left', 'width': '24%'}),
                             html.Div(dcc.Dropdown([], None, id='act-templot-dropdown', clearable=False),
                                      style={'float': 'right', 'width': '74%', 'margin-top': '7px'})],
                            style={'width': '28%', 'float': 'left', 'margin-left': '1%', 'margin-right': '1%'}),
                   html.Div([html.Div(html.H6('Lat. Index: ', style={'color': '#002880'}), style={'float': 'left', 'width': '24%'}),
                             html.Div(dcc.Dropdown([], None, id='li-templot-dropdown', clearable=False),
                                      style={'float': 'right', 'width': '74%', 'margin-top': '7px'})],
                            style={'width': '23%', 'float': 'left', 'margin-left': '1%', 'margin-right': '1%'})],
                  style={'width': '100%'}),
         html.Div(dcc.Graph(id='avg-useintact-graph', config=FIG_CONFIG),
                  style={'clear': 'both', 'margin-top': '5px'})],
        style={'clear': 'both', 'border': DEBUG_BORDER, 'height': '1050px', 'width': '100%'}
    )

    #
    # Instantatneous measures temporal evolution plots.
    # TODO: Not sure if this is needed. Might implement later.

    #
    # App Layout
    return html.Div([
            header,
            datadetailsrow,
            subj_details_row,
            data_controls_row,
            summ_plot,
            measures_evolution_row,
            avrg_evolution_row,
            footer
        ],
        style={'padding': '10px 5px',    
               'margin': '0 auto',
               'width': '70%'}
    )


def setup_clinical_app_layout(datadetails):
    """Creates the layout for the dashboard for clinical purposes.
    """
    #
    # Get common UI elements.
    header, footer, datadetailsrow, subj_details_row = common_elements(datadetails)

    #
    # Measures temporal evolution plots.
    measures_evolution_row = html.Div(
        [dcc.Tabs(id="clinical-summary-temporal-plot-tabs", value='tab-daily-summary-graph',
                  children=[dcc.Tab(label='Daily Summary', value='tab-daily-summary-graph',
                                    className='custom-tab-clinical', selected_className='custom-tab-clinical--selected'),
                            dcc.Tab(label='Daily Details', value='tab-daily-details-graph',
                                    className='custom-tab-clinical', selected_className='custom-tab-clinical--selected'),],
                  style={'margin-top': '2px'}),
         html.Div(id='tab-content-clinical-summary',
                  style={'textAlign': 'center'})],
        style={'clear': 'both', 'border': DEBUG_BORDER, 'height': '850px', 'width': '100%'}
    )

    #
    # App Layout
    return html.Div([
            header,
            datadetailsrow,
            subj_details_row,
            measures_evolution_row,
            footer
        ],
        style={'padding': '10px 5px',    
               'margin': '0 auto',
               'width': '70%'}
    )
    