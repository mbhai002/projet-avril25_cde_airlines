"""
Page Analyses - Analyses Detaillees
Statistiques avancees et exploration des donnees
"""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import os

dash.register_page(__name__, path='/analyses', name='Analyses')

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
DELAY_THRESHOLD = 10

def fetch_api(endpoint):
    try:
        response = requests.get(f"{API_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except:
        return None

layout = html.Div([
    dcc.Interval(id='interval-analyses', interval=120000, n_intervals=0),
    
    dbc.Row([
        dbc.Col([
            html.H2("Analyses Detaillees", className="text-center mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Base de Donnees", className="mb-3"),
                    html.Table([
                        html.Thead(html.Tr([
                            html.Th("Table"),
                            html.Th("Description"),
                            html.Th("Lignes", className="text-end")
                        ])),
                        html.Tbody([
                            html.Tr([
                                html.Td(html.Code("flight")),
                                html.Td("Vols avec predictions ML"),
                                html.Td("841,745", className="text-end")
                            ]),
                            html.Tr([
                                html.Td(html.Code("metar")),
                                html.Td("Observations meteorologiques"),
                                html.Td("82,732", className="text-end")
                            ]),
                            html.Tr([
                                html.Td(html.Code("taf")),
                                html.Td("Previsions meteorologiques"),
                                html.Td("102,899", className="text-end")
                            ]),
                            html.Tr([
                                html.Td(html.Code("sky_condition")),
                                html.Td("Conditions du ciel"),
                                html.Td("243,541", className="text-end")
                            ]),
                            html.Tr([
                                html.Td(html.Code("sky_cover_reference")),
                                html.Td("Reference couverture nuageuse"),
                                html.Td("9", className="text-end")
                            ])
                        ])
                    ], className="table table-striped table-sm"),
                    html.Hr(),
                    html.H5("Architecture", className="mb-2"),
                    html.Ul([
                        html.Li([html.Strong("Backend:"), " FastAPI (Python) sur port 8000"]),
                        html.Li([html.Strong("Frontend:"), " Dash multi-pages sur port 8050"]),
                        html.Li([html.Strong("Base de donnees:"), " PostgreSQL 17.4 (Docker)"]),
                        html.Li([html.Strong("Visualisation:"), " Plotly + Bootstrap"]),
                        html.Li([html.Strong("ML:"), " Predictions de retards avec probabilites"])
                    ], style={'fontSize': '0.9rem'})
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Statistiques Vols", className="mb-0")),
                dbc.CardBody(id='analyses-flight-stats')
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Statistiques Meteo", className="mb-0")),
                dbc.CardBody(id='analyses-meteo-stats')
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Performance Machine Learning", className="mb-0")),
                dbc.CardBody(id='analyses-ml-performance')
            ], className="shadow-sm")
        ])
    ])
])

@callback(
    Output('analyses-flight-stats', 'children'),
    Input('interval-analyses', 'n_intervals')
)
def update_flight_stats(n):
    stats = fetch_api(f"/stats?delay_threshold={DELAY_THRESHOLD}")
    if not stats:
        return "Erreur chargement donnees"
    
    return html.Div([
        html.P([html.Strong("Periode:"), f" {stats['date_min']} au {stats['date_max']}"]),
        html.P([html.Strong("Total vols:"), f" {stats['total_flights']:,}"]),
        html.P([html.Strong("Vols retardes:"), f" {stats['delayed_flights']:,} ({stats['delay_rate']:.2f}%)"]),
        html.P([html.Strong("Vols a l'heure:"), f" {stats['total_flights'] - stats['delayed_flights']:,} ({100 - stats['delay_rate']:.2f}%)"]),
        html.P([html.Strong("Retard moyen:"), f" {stats['avg_delay']:.1f} minutes"]),
        html.P([html.Strong("Seuil retard:"), f" >= {DELAY_THRESHOLD} minutes"]),
    ])

@callback(
    Output('analyses-meteo-stats', 'children'),
    Input('interval-analyses', 'n_intervals')
)
def update_meteo_stats(n):
    stats = fetch_api("/meteo/stats")
    if not stats:
        return "Erreur chargement donnees"
    
    return html.Div([
        html.P([html.Strong("Observations METAR:"), f" {stats['total_metar']:,}"]),
        html.P([html.Strong("Aeroports METAR:"), f" {stats['airports_metar']}"]),
        html.P([html.Strong("Periode METAR:"), f" {stats['date_min_metar']} au {stats['date_max_metar']}"]),
        html.Hr(),
        html.P([html.Strong("Previsions TAF:"), f" {stats['total_taf']:,}"]),
        html.P([html.Strong("Aeroports TAF:"), f" {stats['airports_taf']}"]),
        html.P([html.Strong("Periode TAF:"), f" {stats['date_min_taf']} au {stats['date_max_taf']}"]),
        html.Hr(),
        html.P([html.Strong("Conditions ciel:"), f" {stats['total_sky_conditions']:,}"]),
    ])

@callback(
    Output('analyses-ml-performance', 'children'),
    Input('interval-analyses', 'n_intervals')
)
def update_ml_performance(n):
    stats = fetch_api(f"/stats?delay_threshold={DELAY_THRESHOLD}")
    confusion = fetch_api(f"/ml/confusion?delay_threshold={DELAY_THRESHOLD}")
    
    if not stats or not confusion:
        return "Erreur chargement donnees"
    
    total_ml = confusion['tp'] + confusion['tn'] + confusion['fp'] + confusion['fn']
    sensitivity = confusion['tp'] / (confusion['tp'] + confusion['fn']) * 100 if (confusion['tp'] + confusion['fn']) > 0 else 0
    specificity = confusion['tn'] / (confusion['tn'] + confusion['fp']) * 100 if (confusion['tn'] + confusion['fp']) > 0 else 0
    ppv = confusion['tp'] / (confusion['tp'] + confusion['fp']) * 100 if (confusion['tp'] + confusion['fp']) > 0 else 0
    npv = confusion['tn'] / (confusion['tn'] + confusion['fn']) * 100 if (confusion['tn'] + confusion['fn']) > 0 else 0
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("Metriques Globales"),
                html.P([html.Strong("Precision:"), f" {confusion['accuracy']:.2f}%"]),
                html.P([html.Strong("Vols analyses:"), f" {total_ml:,} / {stats['total_flights']:,}"]),
                html.P([html.Strong("Couverture:"), f" {total_ml / stats['total_flights'] * 100:.1f}%"]),
            ], width=4),
            dbc.Col([
                html.H6("Performance Predictions"),
                html.P([html.Strong("Sensibilite (Rappel):"), f" {sensitivity:.2f}%"]),
                html.P([html.Strong("Specificite:"), f" {specificity:.2f}%"]),
                html.P([html.Strong("VPP (Precision):"), f" {ppv:.2f}%"]),
                html.P([html.Strong("VPN:"), f" {npv:.2f}%"]),
            ], width=4),
            dbc.Col([
                html.H6("Matrice Confusion"),
                html.P([html.Strong("Vrais Positifs (VP):"), f" {confusion['tp']:,}"]),
                html.P([html.Strong("Vrais Negatifs (VN):"), f" {confusion['tn']:,}"]),
                html.P([html.Strong("Faux Positifs (FP):"), f" {confusion['fp']:,}"]),
                html.P([html.Strong("Faux Negatifs (FN):"), f" {confusion['fn']:,}"]),
            ], width=4),
        ])
    ])
