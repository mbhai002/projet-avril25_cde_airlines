"""
Page Suivi de Vol - Recherche Specifique et ML
"""

import dash
from dash import html, dcc, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import requests
from datetime import datetime
import os

dash.register_page(__name__, path='/suivi', name='Suivi Vol')

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')

def fetch_api(endpoint):
    try:
        response = requests.get(f"{API_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except:
        return None

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="fas fa-plane-arrival me-3"), "Suivi Specifique & ML"], className="mb-4")
        ])
    ]),
    
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-search me-2"),
            "Rechercher un vol par son numero"
        ], style={'backgroundColor': '#f8f9fa'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Numero de vol", className="fw-bold mb-2"),
                    dbc.InputGroup([
                        dbc.InputGroupText(html.I(className="fas fa-hashtag")),
                        dbc.Input(
                            id='input-flight-number-suivi',
                            type='text',
                            placeholder='Ex: AM 209, AA 1444'
                        )
                    ])
                ], width=12, lg=5),
                dbc.Col([
                    html.Label("Date de depart", className="fw-bold mb-2"),
                    dbc.InputGroup([
                        dbc.InputGroupText(html.I(className="fas fa-calendar")),
                        dcc.DatePickerSingle(
                            id='input-departure-date-suivi',
                            placeholder='JJ/MM/AAAA',
                            display_format='DD/MM/YYYY',
                            first_day_of_week=1,
                            style={'width': '100%'}
                        )
                    ])
                ], width=12, lg=4),
                dbc.Col([
                    html.Label(html.Br(), className="d-none d-lg-block"),
                    dbc.Button([
                        html.I(className="fas fa-magic me-2"),
                        "Analyser le Vol"
                    ], id='btn-search-flight-suivi', color='primary', className='w-100')
                ], width=12, lg=3),
            ], className="g-3 align-items-end")
        ])
    ], className="shadow-sm mb-4"),
    
    dcc.Loading(
        id="loading-suivi",
        type="default",
        children=html.Div(id='search-result-container-suivi')
    )
], className="py-4")

@callback(
    Output('search-result-container-suivi', 'children'),
    Input('btn-search-flight-suivi', 'n_clicks'),
    Input('input-flight-number-suivi', 'value'),
    Input('input-departure-date-suivi', 'date')
)
def search_specific_flight(n_clicks, flight_number, departure_date):
    if not n_clicks:
        return None
    
    if not flight_number:
        return dbc.Alert("Veuillez saisir un numero de vol", color="warning", className="mt-3")
    
    endpoint = f"/search-flights?flight_number={flight_number.strip()}"
    if departure_date:
        endpoint += f"&departure_date={departure_date}"
    
    flights = fetch_api(endpoint)
    
    if not flights:
        return dbc.Alert(f"Aucun vol trouve pour {flight_number}", color="danger", className="mt-3")
    
    for flight in flights:
        delay = flight.get('delay_min')
        flight['delay_min_disp'] = int(round(delay)) if delay is not None else 'N/A'
        flight['delay_prob_pct'] = f"{flight.get('delay_prob', 0)*100:.1f}%" if flight.get('delay_prob') else 'N/A'
        flight['risk'] = (flight.get('delay_risk_level') or 'N/A').upper()
        
        flight['from_label'] = f"{flight.get('from_city') or 'N/A'} ({flight.get('from_airport')})"
        flight['to_label'] = f"{flight.get('to_city') or 'N/A'} ({flight.get('to_airport')})"
        flight['airline_label'] = flight.get('airline_name') or flight.get('airline_code')

    columns = [
        {"name": "Vol", "id": "flight_number"},
        {"name": "De", "id": "from_label"},
        {"name": "Vers", "id": "to_label"},
        {"name": "Compagnie", "id": "airline_label"},
        {"name": "Depart", "id": "departure_scheduled_utc"},
        {"name": "Probabilite Retard", "id": "delay_prob_pct"},
        {"name": "Risque", "id": "risk"},
    ]

    tooltip_data = [
        {
            'from_label': {'value': str(row.get('from_airport_name') or 'N/A'), 'type': 'markdown'},
            'to_label': {'value': str(row.get('to_airport_name') or 'N/A'), 'type': 'markdown'},
            'airline_label': {'value': str(row.get('airline_name') or 'N/A'), 'type': 'markdown'}
        } for row in flights
    ]

    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Resultats de l'analyse", className="bg-primary text-white"),
                    dbc.CardBody([
                        dash_table.DataTable(
                            columns=columns,
                            data=flights,
                            tooltip_data=tooltip_data,
                            tooltip_delay=0,
                            tooltip_duration=None,
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '12px'},
                            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                            style_data_conditional=[
                                {'if': {'filter_query': '{risk} = "LOW"'}, 'backgroundColor': '#d4edda', 'color': '#155724'},
                                {'if': {'filter_query': '{risk} = "MEDIUM"'}, 'backgroundColor': '#fff3cd', 'color': '#856404'},
                                {'if': {'filter_query': '{risk} = "HIGH"'}, 'backgroundColor': '#f8d7da', 'color': '#721c24'},
                            ]
                        )
                    ])
                ], className="shadow-sm border-0")
            ])
        ])
    ], className="mt-4")
