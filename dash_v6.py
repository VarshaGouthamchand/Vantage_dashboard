import dash
import hashlib
import vantage6.client

import numpy as np
import plotly.express as px
import pandas as pd

from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State

# private module
import miscellaneous
import vantage_client


class Dashboard:
    def __init__(self):
        """"""
        # settings
        self.ColourSchemeContinuous = px.colors.sequential.Agsunset
        self.ColourSchemeCategorical = px.colors.sequential.Agsunset

        # vantage components
        self.Vantage6User = vantage_client.Vantage6Client()
        self.Organisations = None
        # organisation names are ideally retrieved from the client, but some standard names will have to be in place
        # currently names have to be changed to match specific node names
        self.OrganisationsNames = ['HN1_Maastro', 'Montreal', 'Toronto', 'HN3_Maastro']
        self.Organisations_ids_to_query = []
        self.roi_names = {'GTV Primary': 'GTV-1',
                          'GTV Node': 'GTV-2'}

        self.filter_dict = {'roo:P100018': ['C16576', 'C20197'],
                            'roo:P100244': ['C48719', 'C48720', 'C48724', 'C48728', 'C48732'],
                            'roo:P100242': ['C48705', 'C48706', 'C48786', 'C48714'],
                            'roo:P100241': ['C48699', 'C48700'],
                            'roo:P100254': ['C28554', 'C37987'],
                            'roo:P100022': ['C128839', 'C131488'],
                            'roo:P100219': ['C27966', 'C28054', 'C27970', 'C27971'],
                            'roo:P100202': ['C12762', 'C12246', 'C12420', 'C12423'],
                            'roo:P100231': ['C94626', 'C15313']}

        self.Filters_to_apply = {}

        # this 'dataset' is used to display some data when the user has not been authenticated yet
        self._PlaceholderData = {"Not an actual variable_count": {"0.0": 2, "1.0": 4}}
        self.PlaceholderDataframe = miscellaneous.convert_count_dict_to_dataframe(self._PlaceholderData,
                                                                                  self.Filters_to_apply,
                                                                                  self.Organisations_ids_to_query)

        self._PlaceholderDataHeatMap = {}
        self.PlaceholderDataFrameHeatMap, temp_dict = miscellaneous.convert_heatmap_to_appropriate_dataframe(
            pd.DataFrame(np.random.rand(10, 10), columns=[f'Column_{i}' for i in range(10)]),
            self.Organisations_ids_to_query,
            tuple(self.roi_names.values())[0])

        self._PlaceholderDataHeatMap.update(temp_dict)
        # content components
        self.DashboardTitle = ''
        self.DashboardTileTexts = ["3 countries", "4 institutions", "2000 patients"]

        self.pie_dropdown_variables = {'roo:P100018': 'Gender',
                                       'roo:P100244': 'T-stage',
                                       'roo:P100242': 'N-stage',
                                       'roo:P100241': 'M-stage',
                                       'roo:P100254': 'Survival Status',
                                       'roo:P100022': 'HPV Status',
                                       'roo:P100219': 'AJCC Stage',
                                       'roo:P100202': 'Tumour Location',
                                       'roo:P100231': 'Therapy given'}

        # refers to <folder_with_this_file>/assets/dashboard_aesthetics.css
        self.App = dash.Dash(__name__, external_stylesheets=['dashboard_aesthetics.css'])
        self.Layout = self.define_layout()
        self.register_callbacks()

    def define_layout(self):
        """"""
        self.App.layout = html.Div([
            dcc.Store(id='authentication-status', data=False),  # Store for login status

            html.Header([
                html.Div(className='primary-header', children=[
                    html.Div(id='input-container', className='input-container', children=[
                        dcc.Input(id='input-username', className='input-field', placeholder='Username', type='text'),
                        dcc.Input(id='input-password', className='input-field', placeholder='Password',
                                  type='password'),
                        html.Button('Submit', id='login-button', n_clicks=0, className='login-button')
                    ]),
                    # Welcome message
                    dcc.Markdown(id='welcome-message', className='welcome-message white-text', children=[]),
                ]),
            ]),

            html.Div([
                # Text tiles
                html.Div(id='dashboard', className='dashboard', children=[
                    html.H5(id='dashboard-title', className='dashboard-title', children=self.DashboardTitle),

                    html.Div(id='tile-1', className='tile', children=[
                        html.Div(id='tile-content-1', className='tile-content', children=self.DashboardTileTexts[0])
                    ]),

                    html.Div(id='tile-2', className='tile', children=[
                        html.Div(id='tile-content-2', className='tile-content', children=self.DashboardTileTexts[1])
                    ]),

                    html.Div(id='tile-3', className='tile', children=[
                        html.Div(id='tile-content-3', className='tile-content', children=self.DashboardTileTexts[2])
                    ])
                ]),
            ]),
            # Centered container
            html.Div(className='graph-container', children=[
                html.Div(id='auth-lock', className='authentication-lock',
                         children='Please log in on the top left to explore the data'),
                html.Div([
                    html.Label("Select institution:", style={'textAlign': 'center', 'fontSize': '18px'}),
                    dcc.Checklist(
                        id='institution-checklist',
                        options=[{'label': organisation, 'value': organisation} for organisation in
                                 self.OrganisationsNames],
                        value=[],
                        className='organisation-checklist',
                        inline=True
                    ),
                ], style={'textAlign': 'center', 'width': '50%', 'margin': '0 auto', 'marginTop': '20px'}),

                # Tabs
                dcc.Tabs(id='tabs', className='graphing-options', value='tab-pie', children=[
                    dcc.Tab(label='Pie chart', className='graph', value='tab-pie', children=[
                        dcc.Dropdown(
                            id='dataset-variable',
                            value='Not an actual variable',
                            options=[{'label': variable_label, 'value': variable_identification}
                                     for variable_identification, variable_label in
                                     self.pie_dropdown_variables.items()],
                            clearable=False,
                            className='pie-drop-down'),
                    ]),
                    # dcc.Tab(label='Scatter plot', className='graph', value='tab-scatter'),
                    dcc.Tab(label='Bar chart', className='graph', value='tab-bar'),
                ]),

                # Tab content
                html.Div(id='tab-content', className='graph-content'),
                html.Div(id='query-trigger-not-for-display'),

                # Display the heatmap below the tabs
                html.Div([
                    html.Div([
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Label("Select ROI for heatmap:", style={'fontSize': '16px'}),
                        dcc.RadioItems(
                            id='roi-checklist',
                            options=[{'label': roi_label, 'value': roi_value} for roi_label, roi_value in
                                     self.roi_names.items()],
                            value=tuple(self.roi_names.values())[0],  # Initially select first
                            style={'marginRight': '20px', 'marginTop': '20px'},  # Add some spacing between checkboxes
                        ),
                    ], style={'flex': '0.4', 'fontSize': '14px'}),
                ], style={'display': 'flex', 'flexDirection': 'row', 'vertical-align': 'top'}),

                html.Div(id='heatmap-content'),
            ])
        ])

    def register_callbacks(self):
        """"""

        @self.App.callback(
            [Output('authentication-status', 'data'),
             Output('input-container', 'style'),
             Output('welcome-message', 'children'),
             Output('auth-lock', 'style')],
            [Input('login-button', 'n_clicks')],
            [State('input-username', 'value'),
             State('input-password', 'value')]
        )
        def authenticate(n_clicks, username, password):
            """"""
            if n_clicks > 0:
                try:
                    # log in
                    self.Vantage6User.login(username, password)
                    self.Organisations = self.Vantage6User.Client.organization.list()

                    # Successful authentication, return True (logged in) and empty style for input container
                    welcome_message = [f'Welcome {username}, happy to have you here!']
                    return True, {'display': 'none'}, welcome_message, {'display': 'none'}
                except vantage6.client.AuthenticationException:
                    return False, {'display': 'block'}, [], {'display': 'block'}
            # Default: Display the login input fields, an empty welcome message, and hide the button
            return False, {'display': 'block'}, [], {'display': 'block'}

        @self.App.callback(
            Output('query-trigger-not-for-display', 'children'),
            [Input('authentication-status', 'data'),
             Input('institution-checklist', 'value')]
        )
        def select_organisations(authentication_status, organisation_to_include):
            """
            Transcribe the user's selection of organisations to ids that can be used in the Vantage6 Python client
            by directly accessing the Vantage6 Python client which are then stored it in a class object.

            The dcc.CheckList was not directly used as a callback to use Vantage6's Python client to ensure that:
             - dummy data can be displayed whilst not being an authenticated user
             - new organisations are queryable without hard-coding any of their ids.

            :param bool authentication_status: ensure that the user is authenticated to retrieve the organisation ids
            :param list organisation_to_include: list of organisations that the user has selected on the dashboard
            :return: an empty string, the query trigger is solely used to prioritise this callback over callbacks
            that actually use the selected organisations. This is done to ensure that a generic graph is visible
            whilst not being logged in by using a class object rather than callback itself
            """
            # only retrieve the organisation ids when the user is authenticated as it will otherwise break
            if authentication_status:
                self.Organisations_ids_to_query = [organisation['id'] for organisation in self.Organisations['data']
                                                   if organisation['name'] in organisation_to_include]

            return ""

        # to implement
        # @self.App.callback(
        #     Output('tile-1', 'children'),
        #     [Input('institution-checklist', 'value')],
        #     [State('tile-1', 'children')]
        # )
        # def update_tile_content(authenticated, current_content):
        #     """"""
        #     if authenticated:
        #         # retrieve the original content from the html object
        #         original_content = current_content[0]['props']['children']
        #
        #         # Use part of the original tile content and concatenate with additional information
        #         updated_content = f"{len(set([organisation['country'] for organisation in self.Organisations['data']]))}" \
        #                           f"{original_content[original_content.find(' '):]}"
        #         return updated_content
        #     return current_content  # Return the current content when not updating

        @self.App.callback(
            Output('tab-content', 'children'),
            Input('query-trigger-not-for-display', 'children'),
            Input('tabs', 'value'),
            Input("dataset-variable", "value"))
        def render_content(query_trigger, tab, dataset_variable):
            """
            to complete

            :param any query_trigger:
            :param str tab:
            :param str dataset_variable:
            :return:
            """
            if tab == 'tab-pie':
                # retrieve the data that is to be rendered
                filtered_data = self._retrieve_counts_to_render(dataset_variable)

                # create a pie chart
                fig = px.pie(filtered_data, names='Categories', values='Values',
                             color_discrete_sequence=self.ColourSchemeCategorical)

            # elif tab == 'tab-scatter':
            #     Create a scatter plot
            # fig = px.scatter(filtered_data, x='X', y='Y', title=dataset_variable)

            elif tab == 'tab-bar':
                # retrieve the data that is to be rendered
                filtered_data = self._retrieve_counts_to_render(dataset_variable)

                # create a bar chart
                fig = px.bar(filtered_data, x='Categories', y='Values',
                             color_discrete_sequence=self.ColourSchemeCategorical)

            else:
                fig = None

            return dcc.Graph(figure=fig)

        @self.App.callback(
            Output('heatmap-content', 'children'),
            Input('query-trigger-not-for-display', 'children'),
            Input("roi-checklist", "value"))
        def render_heatmap(query_trigger, roi_checklist):
            heatmap_data = self._retrieve_heatmap_to_render(roi_checklist)
            fig_heatmap = px.imshow(heatmap_data, y=heatmap_data.columns, text_auto=True, aspect="auto",
                                    title='Correlation Heatmap')
            return dcc.Graph(figure=fig_heatmap)

    def run(self, debug=None):
        """
        Start the Plotly Dash dashboard

        :param bool debug: specify whether to use debugging mode
        """
        if isinstance(debug, bool) is False:
            debug = True

        self.App.run_server(debug=debug)

    def _retrieve_counts_to_render(self, dataset_variable):
        """
        Retrieve counts of given variable, either from data already existing in the placeholder, or by querying Vantage6

        :param str dataset_variable: name or predicate of the variable to query
        :return: pandas.DataFrame consisting of the counts of the desired variable
        """

        if dataset_variable != 'Not an actual variable':
            self.Filters_to_apply = {dataset_variable: self.filter_dict[dataset_variable]}

        # do not attempt to query dummy data; the [] and [0] represent the default filter and organisation state
        if f'{dataset_variable}_count' in self._PlaceholderData.keys():
            filtered_data = self.PlaceholderDataframe[
                self.PlaceholderDataframe['HashIdentifier'] == miscellaneous.hash_information(dataset_variable,
                                                                                              {}, [])]
            return filtered_data
        else:
            # collect the data that is to be queried
            filtered_data = self.PlaceholderDataframe[self.PlaceholderDataframe['HashIdentifier'] ==
                                                      miscellaneous.hash_information(dataset_variable,
                                                                                     self.Filters_to_apply,
                                                                                     self.Organisations_ids_to_query)]

            # if it appears empty, i.e., the data for the organisation hash is not available then retrieve it
            if filtered_data.empty:
                query_name = f'Dashboard request of counts for {dataset_variable}'
                self.Vantage6User.compute_count_sparql(name=query_name,
                                                       predicates=dataset_variable,
                                                       organisation_ids=self.Organisations_ids_to_query,
                                                       filters=self.Filters_to_apply,
                                                       save_results=False)
                query_result = self.Vantage6User.Results[query_name]

                # append the query result
                self.PlaceholderDataframe = miscellaneous.convert_count_dict_to_dataframe(query_result,
                                                                                          self.Filters_to_apply,
                                                                                          self.Organisations_ids_to_query,
                                                                                          self.PlaceholderDataframe)

            # filter the placeholder to retrieve the new data
            filtered_data = self.PlaceholderDataframe[self.PlaceholderDataframe['HashIdentifier'] ==
                                                      miscellaneous.hash_information(dataset_variable,
                                                                                     self.Filters_to_apply,
                                                                                     self.Organisations_ids_to_query)]
            return filtered_data

    def _retrieve_heatmap_to_render(self, roi_checklist):
        """
        Retrieve either from data already existing in the placeholder, or by querying Vantage6

        :return: pandas.DataFrame consisting of the counts of the desired variable
        """
        # build in a check for the filter or alike thing, to ensure that it is not directly querying data
        # collect the data that is to be queried
        expl_vars = ['Fmorph.pca.elongation', 'Fmorph.pca.flatness', 'Fmorph.diam']
        censor_col = 'censor'

        # if organizations ids are selected, check the hash id if already present and fetch it
        if self.Organisations_ids_to_query:
            OrganisationHash = hashlib.sha256(
                (str(tuple(self.Organisations_ids_to_query)) + roi_checklist).encode()).hexdigest()
        # else get the default hash id with organization ids [] and roi filter as GTV-1
        else:
            OrganisationHash = hashlib.sha256(
                (str(tuple(self.Organisations_ids_to_query)) + 'GTV-1').encode()).hexdigest()

        if OrganisationHash in self._PlaceholderDataHeatMap:
            columns_to_fetch = self._PlaceholderDataHeatMap[OrganisationHash]['columns']
            roi_to_fetch = self._PlaceholderDataHeatMap[OrganisationHash]['ROI']

            heatmap_data = self.PlaceholderDataFrameHeatMap[columns_to_fetch]
            heatmap_data = heatmap_data[(self.PlaceholderDataFrameHeatMap['ROI'] == roi_to_fetch) &
                                        (self.PlaceholderDataFrameHeatMap['OrganisationHash'] == OrganisationHash)]
            heatmap_data = heatmap_data.drop(columns=['ROI', 'OrganisationHash'])

            return heatmap_data

        else:
            query_name = f'Heatmap for {self.Organisations_ids_to_query} with filter ROI'

            # TODO use right task
            self.Vantage6User.compute_hm_sparql(name=query_name,
                                                expl_vars=expl_vars,
                                                censor_col=censor_col,
                                                roitype=roi_checklist,
                                                organisation_ids=self.Organisations_ids_to_query,
                                                save_results=False)

            query_result = self.Vantage6User.Results[query_name]

            # append the query result
            self.PlaceholderDataFrameHeatMap, temp_dict = miscellaneous.convert_heatmap_to_appropriate_dataframe(
                query_result,
                self.Organisations_ids_to_query,
                roi_checklist,
                self.PlaceholderDataFrameHeatMap)

            self._PlaceholderDataHeatMap.update(temp_dict)

            columns_to_fetch = self._PlaceholderDataHeatMap[OrganisationHash]['columns']
            roi_to_fetch = self._PlaceholderDataHeatMap[OrganisationHash]['ROI']

            # collect the data that is to be queried
            heatmap_data = self.PlaceholderDataFrameHeatMap[columns_to_fetch]
            heatmap_data = heatmap_data[(self.PlaceholderDataFrameHeatMap['ROI'] == roi_to_fetch) &
                                        (self.PlaceholderDataFrameHeatMap['OrganisationHash'] == OrganisationHash)]
            heatmap_data = heatmap_data.drop(columns=['ROI', 'OrganisationHash'])

        return heatmap_data


if __name__ == '__main__':
    dash_app = Dashboard()
    dash_app.run()
