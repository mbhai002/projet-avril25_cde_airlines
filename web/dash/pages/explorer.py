"""
Page Explorer - Consultation de la liste des vols avec filtres
"""

import dash
from dash import html, dcc, Input, Output, callback, dash_table, State
import dash_bootstrap_components as dbc
import requests
from datetime import datetime, timedelta
import os

dash.register_page(__name__, path='/explorer', name='Exploration')

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
            html.H2([html.I(className="fas fa-list me-3"), "Exploration des Vols"], className="mb-4")
        ])
    ]),

    # Barre de filtres
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Periode de depart", className="fw-bold mb-2"),
                    dcc.DatePickerRange(
                        id='explorer-date-range',
                        start_date=datetime.now().strftime('%Y-%m-%d'),
                        end_date=datetime.now().strftime('%Y-%m-%d'),
                        display_format='DD/MM/YYYY',
                        className="w-100"
                    )
                ], width=12, lg=4),
                dbc.Col([
                    html.Label("Filtres rapides", className="fw-bold mb-2"),
                    dbc.RadioItems(
                        id="explorer-quick-filter",
                        options=[
                            {"label": "Tous", "value": "all"},
                            {"label": "Retards", "value": "delayed"},
                            {"label": "Haut Risque", "value": "high_risk"},
                        ],
                        value="all",
                        inline=True,
                    )
                ], width=12, lg=4),
                dbc.Col([
                    html.Label(html.Br(), className="d-none d-lg-block"),
                    dbc.Button([
                        html.I(className="fas fa-sync-alt me-2"),
                        "Actualiser la liste"
                    ], id='btn-explorer-refresh', color='success', className='w-100')
                ], width=12, lg=4),
            ], className="g-3 align-items-end")
        ])
    ], className="shadow-sm mb-4 border-0 bg-light"),

    dcc.Loading(
        id="loading-explorer",
        type="circle",
        children=html.Div(id='explorer-table-container')
    )
], className="py-4")

@callback(
    Output('explorer-table-container', 'children'),
    Input('btn-explorer-refresh', 'n_clicks'),
    Input('explorer-date-range', 'start_date'),
    Input('explorer-date-range', 'end_date'),
    Input('explorer-quick-filter', 'value'),
    State('explorer-date-range', 'start_date'),
    State('explorer-date-range', 'end_date')
)
def update_explorer_table(n_clicks, start, end, q_filter, s_state, e_state):
    # Correction: On utilise les dates fournies
    date_start = start or datetime.now().strftime('%Y-%m-%d')
    date_end = end or datetime.now().strftime('%Y-%m-%d')
    
    params = [f"date_start={date_start}", f"date_end={date_end}"]
    
    if q_filter == 'delayed':
        params.append("min_delay=15")
    elif q_filter == 'high_risk':
        params.append("risk_level=high")
    
    flights = fetch_api(f"/search-flights?{'&'.join(params)}")
    
    if not flights:
        return dbc.Alert("Aucun vol trouvé pour cette période.", color="info", className="mt-4")

    # Data transformation for display
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
        {"name": "Depart (UTC)", "id": "departure_scheduled_utc"},
        {"name": "Retard (m)", "id": "delay_min_disp"},
        {"name": "Meteo", "id": "dep_flight_category"},
        {"name": "Risque Retard", "id": "risk"},
    ]

    tooltip_data = [
        {
            'from_label': {'value': str(row.get('from_airport_name') or 'N/A'), 'type': 'markdown'},
            'to_label': {'value': str(row.get('to_airport_name') or 'N/A'), 'type': 'markdown'},
            'airline_label': {'value': str(row.get('airline_name') or 'N/A'), 'type': 'markdown'}
        } for row in flights
    ]

    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-table me-2"),
            f"Resultats : {len(flights)} vols"
        ]),
        dbc.CardBody([
            dash_table.DataTable(
                id='explorer-table-dt',
                columns=columns,
                data=flights,
                tooltip_data=tooltip_data,
                tooltip_delay=0,
                tooltip_duration=None,
                filter_action="native",
                sort_action="native",
                page_size=20,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '12px', 'fontSize': '13px'},
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'filter_query': '{risk} = "LOW"'}, 'backgroundColor': '#d4edda', 'color': '#155724'},
                    {'if': {'filter_query': '{risk} = "MEDIUM"'}, 'backgroundColor': '#fff3cd', 'color': '#856404'},
                    {'if': {'filter_query': '{risk} = "HIGH"'}, 'backgroundColor': '#f8d7da', 'color': '#721c24'},
                ]
            )
        ])
    ], className="shadow-sm border-0")
