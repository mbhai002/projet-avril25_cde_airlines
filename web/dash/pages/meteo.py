"""
Page Meteo - Analyse Meteorologique
METAR, TAF et conditions meteo
"""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import requests
import os

dash.register_page(__name__, path='/meteo', name='Meteo')

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
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
            dbc.Card([
                dbc.CardHeader(html.H5("Top 20 Aeroports - Observations Meteo", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-top-airports', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H3("Correlations Meteo → Retards", className="mb-3 mt-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Impact Visibilite sur Retards", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-corr-visibility', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Impact Vent sur Retards", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-corr-wind', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Top Conditions Meteo avec Retards Eleves", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='meteo-corr-conditions', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ])
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
    Input('interval-meteo', 'n_intervals')
)
def update_kpis(n):
    stats = fetch_api("/meteo/stats")
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
    Input('interval-meteo', 'n_intervals')
)
def update_flight_categories(n):
    data = fetch_api("/meteo/flight-categories")
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
    Input('interval-meteo', 'n_intervals')
)
def update_weather_conditions(n):
    data = fetch_api("/meteo/weather-conditions")
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
    Output('meteo-top-airports', 'figure'),
    Input('interval-meteo', 'n_intervals')
)
def update_top_airports(n):
    data = fetch_api("/meteo/top-airports?limit=20")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['airport'] for d in data],
        y=[d['observations'] for d in data],
        marker_color='#9b59b6',
        text=[f"{d['observations']:,}" for d in data],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Observations: %{y:,}<br>Temp moyenne: %{customdata[0]:.1f}°C<br>Vent moyen: %{customdata[1]:.1f} kt<br>Visibilite: %{customdata[2]:.1f} mi<extra></extra>',
        customdata=[[d['avg_temp'], d['avg_wind_speed'], d['avg_visibility']] for d in data]
    ))
    fig.update_layout(
        title="Aeroports avec le Plus d'Observations",
        xaxis_title="Aeroport",
        yaxis_title="Nombre observations",
        template='plotly_white',
        height=400
    )
    return fig

@callback(
    Output('meteo-corr-visibility', 'figure'),
    Input('interval-meteo', 'n_intervals')
)
def update_corr_visibility(n):
    data = fetch_api(f"/correlations/visibility-delays?delay_threshold={DELAY_THRESHOLD}")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Total vols',
        x=[d['visibility_range'] for d in data],
        y=[d['total_flights'] for d in data],
        marker_color='#3498db',
        yaxis='y',
        offsetgroup=1
    ))
    fig.add_trace(go.Scatter(
        name='Taux retard',
        x=[d['visibility_range'] for d in data],
        y=[d['delay_rate'] for d in data],
        marker_color='#e74c3c',
        yaxis='y2',
        mode='lines+markers',
        line=dict(width=3)
    ))
    fig.update_layout(
        title="Correlation Visibilite - Retards",
        xaxis_title="Plage visibilite",
        yaxis=dict(title="Nombre vols", side='left'),
        yaxis2=dict(title="Taux retard (%)", side='right', overlaying='y'),
        template='plotly_white',
        height=400,
        hovermode='x unified'
    )
    return fig

@callback(
    Output('meteo-corr-wind', 'figure'),
    Input('interval-meteo', 'n_intervals')
)
def update_corr_wind(n):
    data = fetch_api(f"/correlations/wind-delays?delay_threshold={DELAY_THRESHOLD}")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Total vols',
        x=[d['wind_range'] for d in data],
        y=[d['total_flights'] for d in data],
        marker_color='#9b59b6',
        yaxis='y',
        offsetgroup=1
    ))
    fig.add_trace(go.Scatter(
        name='Taux retard',
        x=[d['wind_range'] for d in data],
        y=[d['delay_rate'] for d in data],
        marker_color='#e74c3c',
        yaxis='y2',
        mode='lines+markers',
        line=dict(width=3)
    ))
    fig.update_layout(
        title="Correlation Vent - Retards",
        xaxis_title="Vitesse vent (kt)",
        yaxis=dict(title="Nombre vols", side='left'),
        yaxis2=dict(title="Taux retard (%)", side='right', overlaying='y'),
        template='plotly_white',
        height=400,
        hovermode='x unified'
    )
    return fig

@callback(
    Output('meteo-corr-conditions', 'figure'),
    Input('interval-meteo', 'n_intervals')
)
def update_corr_conditions(n):
    data = fetch_api(f"/correlations/meteo-delays?delay_threshold={DELAY_THRESHOLD}")
    if not data:
        return go.Figure()
    
    top_data = sorted(data, key=lambda x: x['delay_rate'], reverse=True)[:20]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{d['flight_category']} - {d['wx_string'] if d['wx_string'] else 'CLEAR'}" for d in top_data],
        y=[d['delay_rate'] for d in top_data],
        marker=dict(
            color=[d['delay_rate'] for d in top_data],
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title="Taux<br>retard (%)")
        ),
        text=[f"{d['delay_rate']:.1f}%" for d in top_data],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Taux retard: %{y:.1f}%<br>Vols totaux: %{customdata[0]:,}<br>Vols retardes: %{customdata[1]:,}<br>Retard moyen: %{customdata[2]:.1f} min<extra></extra>',
        customdata=[[d['total_flights'], d['delayed_flights'], d['avg_delay_min']] for d in top_data]
    ))
    fig.update_layout(
        title="Top 20 Conditions Meteo avec Taux Retard Eleve",
        xaxis_title="Categorie - Condition",
        yaxis_title="Taux retard (%)",
        template='plotly_white',
        height=500,
        xaxis_tickangle=-45
    )
    return fig
