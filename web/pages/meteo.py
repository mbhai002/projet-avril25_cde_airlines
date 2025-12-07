"""
Page Meteo - Observations et Previsions
"""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime, timedelta

dash.register_page(__name__, path='/meteo', name='Meteo')

API_URL = "http://127.0.0.1:8000"
DELAY_THRESHOLD = 10

def fetch_api(endpoint):
    try:
        response = requests.get(f"{API_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except:
        return None

def create_metric_card(title, value, subtitle, icon, color):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} fa-2x", style={'color': color}),
                html.H3(value, className="mt-2 mb-0", style={'color': color, 'fontWeight': 'bold'}),
                html.P(title, className="text-muted mb-0", style={'fontSize': '0.9rem'}),
                html.Small(subtitle, className="text-secondary")
            ], className="text-center")
        ])
    ], className="shadow-sm h-100")

layout = html.Div([
    dcc.Interval(id='interval-meteo', interval=120000, n_intervals=0),
    
    dbc.Row([
        dbc.Col([
            html.H2("Analyse Meteorologique", className="text-center mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Label([
                            html.I(className="fas fa-calendar-alt me-2"),
                            html.Strong("Periode d'analyse meteo")
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                dcc.DatePickerSingle(
                                    id='meteo-date-start',
                                    date=datetime.now().strftime('%Y-%m-%d'),
                                    display_format='DD/MM/YYYY',
                                    placeholder='Date debut',
                                    first_day_of_week=1,
                                    style={'width': '100%'}
                                )
                            ], width=4),
                            dbc.Col([
                                dcc.DatePickerSingle(
                                    id='meteo-date-end',
                                    date=datetime.now().strftime('%Y-%m-%d'),
                                    display_format='DD/MM/YYYY',
                                    placeholder='Date fin',
                                    first_day_of_week=1,
                                    style={'width': '100%'}
                                )
                            ], width=4),
                            dbc.Col([
                                html.Small("Par defaut: aujourd'hui. Selectionnez 2 dates pour une periode", 
                                          className="text-muted d-block mt-2")
                            ], width=4),
                        ], className="g-2")
                    ], className="text-center")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),
    
    dbc.Row(id='meteo-kpi-cards', className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Categories de Vol (METAR)", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-flight-categories', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Conditions Meteorologiques", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-weather-conditions', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.H4("Analyse Visibilite", className="mb-3 mt-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Distribution Visibilite", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-visibility-distribution', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Evolution Visibilite Moyenne", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-visibility-timeline', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Temperature et Point de Rosee", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-temperature-dewpoint', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Vitesse du Vent", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-wind-speed', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Definitions", className="mb-3"),
                    html.Ul([
                        html.Li([html.Strong("METAR:"), " Observation meteorologique actuelle"]),
                        html.Li([html.Strong("TAF:"), " Prevision meteorologique aeronautique"]),
                        html.Li([html.Strong("VFR:"), " Vol a vue (>= 5 miles, plafond >= 3000 ft)"]),
                        html.Li([html.Strong("IFR:"), " Vol aux instruments (< 3 miles ou plafond < 1000 ft)"]),
                        html.Li([html.Strong("MVFR:"), " VFR marginal (3-5 miles ou 1000-3000 ft)"]),
                        html.Li([html.Strong("LIFR:"), " IFR limite (< 1 mile ou plafond < 500 ft)"])
                    ], style={'fontSize': '0.9rem'})
                ])
            ], className="shadow-sm")
        ])
    ])
])

@callback(
    Output('meteo-kpi-cards', 'children'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_kpis(n, date_start, date_end):
    endpoint = "/meteo/stats"
    if date_start:
        endpoint += f"?date_start={date_start}"
        if date_end:
            endpoint += f"&date_end={date_end}"
    elif date_end:
        endpoint += f"?date_end={date_end}"
    
    stats = fetch_api(endpoint)
    if not stats:
        return []
    
    return [
        dbc.Col(create_metric_card(
            "METAR Observations", f"{stats['total_metar']:,}", 
            f"{stats['airports_metar']} aeroports",
            "fa-cloud", "#3498db"
        ), width=3),
        dbc.Col(create_metric_card(
            "TAF Previsions", f"{stats['total_taf']:,}", 
            f"{stats['airports_taf']} aeroports",
            "fa-cloud-sun", "#9b59b6"
        ), width=3),
        dbc.Col(create_metric_card(
            "Conditions Ciel", f"{stats['total_sky_conditions']:,}", 
            "Observations detaillees",
            "fa-cloud-meatball", "#1abc9c"
        ), width=3),
        dbc.Col(create_metric_card(
            "Periode METAR", 
            f"{stats['date_min_metar']}", 
            f"au {stats['date_max_metar']}",
            "fa-calendar", "#e67e22"
        ), width=3),
    ]

@callback(
    Output('meteo-flight-categories', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_flight_categories(n, date_start, date_end):
    endpoint = "/meteo/flight-categories"
    if date_start:
        endpoint += f"?date_start={date_start}"
        if date_end:
            endpoint += f"&date_end={date_end}"
    elif date_end:
        endpoint += f"?date_end={date_end}"
    
    data = fetch_api(endpoint)
    if not data:
        return go.Figure()
    
    colors_map = {
        'VFR': '#27ae60',
        'MVFR': '#f39c12',
        'IFR': '#e74c3c',
        'LIFR': '#8e44ad',
        'UNKNOWN': '#95a5a6'
    }
    
    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=[d['condition'] for d in data],
        values=[d['count'] for d in data],
        marker=dict(colors=[colors_map.get(d['condition'], '#95a5a6') for d in data]),
        textinfo='label+percent',
        textposition='inside',
        hovertemplate='<b>%{label}</b><br>Observations: %{value:,}<br>Pourcentage: %{percent}<extra></extra>'
    ))
    fig.update_layout(
        title="Distribution Categories Vol",
        template='plotly_white',
        height=350,
        showlegend=True
    )
    return fig

@callback(
    Output('meteo-weather-conditions', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_weather_conditions(n, date_start, date_end):
    endpoint = "/meteo/weather-conditions"
    if date_start:
        endpoint += f"?date_start={date_start}"
        if date_end:
            endpoint += f"&date_end={date_end}"
    elif date_end:
        endpoint += f"?date_end={date_end}"
    
    data = fetch_api(endpoint)
    if not data:
        return go.Figure()
    
    top_data = data[:15]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[d['condition'] if d['condition'] else 'CLEAR' for d in top_data],
        x=[d['count'] for d in top_data],
        orientation='h',
        marker_color='#3498db',
        text=[f"{d['percentage']:.1f}%" for d in top_data],
        textposition='auto'
    ))
    fig.update_layout(
        title="Top 15 Conditions Meteo",
        xaxis_title="Nombre observations",
        template='plotly_white',
        height=400
    )
    return fig

@callback(
    Output('meteo-visibility-distribution', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_visibility_distribution(n, date_start, date_end):
    endpoint = "/meteo/visibility-distribution"
    if date_start:
        endpoint += f"?date_start={date_start}"
    if date_end:
        endpoint += f"&date_end={date_end}" if "?" in endpoint else f"?date_end={date_end}"
    
    data = fetch_api(endpoint)
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['visibility_range'] for d in data],
        y=[d['count'] for d in data],
        marker_color='#3498db',
        text=[f"{d['count']:,}" for d in data],
        textposition='outside'
    ))
    fig.update_layout(
        title="Repartition des Observations par Visibilite",
        xaxis_title="Visibilite (miles)",
        yaxis_title="Nombre observations",
        template='plotly_white',
        height=350
    )
    return fig

@callback(
    Output('meteo-visibility-timeline', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_visibility_timeline(n, date_start, date_end):
    endpoint = "/meteo/visibility-timeline"
    if date_start:
        endpoint += f"?date_start={date_start}"
    if date_end:
        endpoint += f"&date_end={date_end}" if "?" in endpoint else f"?date_end={date_end}"
    
    data = fetch_api(endpoint)
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['avg_visibility'] for d in data],
        mode='lines+markers',
        marker=dict(size=8, color='#3498db'),
        line=dict(width=2, color='#3498db'),
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.2)'
    ))
    fig.update_layout(
        title="Evolution Visibilite Moyenne par Jour",
        xaxis_title="Date",
        yaxis_title="Visibilite moyenne (miles)",
        template='plotly_white',
        height=350
    )
    return fig

@callback(
    Output('meteo-temperature-dewpoint', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_temperature_dewpoint(n, date_start, date_end):
    endpoint = "/meteo/temperature-stats"
    if date_start:
        endpoint += f"?date_start={date_start}"
    if date_end:
        endpoint += f"&date_end={date_end}" if "?" in endpoint else f"?date_end={date_end}"
    
    data = fetch_api(endpoint)
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['avg_temp'] for d in data],
        mode='lines+markers',
        name='Temperature',
        marker=dict(size=6, color='#e74c3c'),
        line=dict(width=2)
    ))
    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['avg_dewpoint'] for d in data],
        mode='lines+markers',
        name='Point de rosee',
        marker=dict(size=6, color='#3498db'),
        line=dict(width=2)
    ))
    fig.update_layout(
        title="Evolution Temperature et Point de Rosee",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        template='plotly_white',
        height=350,
        hovermode='x unified'
    )
    return fig

@callback(
    Output('meteo-wind-speed', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_wind_speed(n, date_start, date_end):
    endpoint = "/meteo/wind-stats"
    if date_start:
        endpoint += f"?date_start={date_start}"
    if date_end:
        endpoint += f"&date_end={date_end}" if "?" in endpoint else f"?date_end={date_end}"
    
    data = fetch_api(endpoint)
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['wind_range'] for d in data],
        y=[d['count'] for d in data],
        marker_color='#9b59b6',
        text=[f"{d['count']:,}" for d in data],
        textposition='outside'
    ))
    fig.update_layout(
        title="Distribution Vitesse du Vent",
        xaxis_title="Vitesse (kt)",
        yaxis_title="Nombre observations",
        template='plotly_white',
        height=350
    )
    return fig
