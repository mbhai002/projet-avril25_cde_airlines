"""
Page Vols - Dashboard Principal
Analyse des vols et predictions ML
"""

import dash
from dash import html, dcc, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

dash.register_page(__name__, path='/', name='Vols')

API_URL = "http://127.0.0.1:8000"
DEFAULT_DELAY_THRESHOLD = 10

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
    dcc.Interval(id='interval-vols', interval=60000, n_intervals=0),
    
    dbc.Row([
        dbc.Col([
            html.H2("Analyse des Vols et Predictions ML", className="text-center mb-4")
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.I(className="fas fa-search me-2"),
                        html.H5("Recherche et Filtrage des Vols", className="d-inline mb-0")
                    ])
                ], style={'backgroundColor': '#f8f9fa'}),
                dbc.CardBody([
                    dbc.Tabs([
                        dbc.Tab([
                            html.Div([
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.Label([
                                                html.I(className="fas fa-plane me-2"),
                                                "Numero de vol"
                                            ], className="fw-bold mb-2"),
                                            dbc.InputGroup([
                                                dbc.InputGroupText(html.I(className="fas fa-hashtag")),
                                                dbc.Input(
                                                    id='input-flight-number',
                                                    type='text',
                                                    placeholder='Ex: AM 209, AA 1444',
                                                    style={'fontSize': '16px'}
                                                )
                                            ])
                                        ])
                                    ], width=12, lg=5),
                                    dbc.Col([
                                        html.Div([
                                            html.Label([
                                                html.I(className="fas fa-calendar-alt me-2"),
                                                "Date de depart"
                                            ], className="fw-bold mb-2"),
                                            dbc.InputGroup([
                                                dbc.InputGroupText(html.I(className="fas fa-calendar")),
                                                dcc.DatePickerSingle(
                                                    id='input-departure-date',
                                                    placeholder='JJ/MM/AAAA',
                                                    display_format='DD/MM/YYYY',
                                                    first_day_of_week=1,
                                                    style={'width': '100%', 'fontSize': '16px'}
                                                )
                                            ])
                                        ])
                                    ], width=12, lg=4),
                                    dbc.Col([
                                        html.Div([
                                            html.Label(html.Br(), className="d-none d-lg-block"),
                                            dbc.Button([
                                                html.I(className="fas fa-search me-2"),
                                                "Rechercher"
                                            ], id='btn-search-flight', color='success', size='lg', className='w-100')
                                        ])
                                    ], width=12, lg=3),
                                ], className="g-3 align-items-end"),
                                html.Div(id='search-result-container', className='mt-4')
                            ], className="p-3")
                        ], label="Recherche rapide", tab_id="tab-search", label_style={'fontSize': '16px'}),
                        
                        dbc.Tab([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-info-circle me-2 text-info"),
                                    html.Span("Selectionnez une periode - chargement automatique ou manuel", 
                                             className="text-muted")
                                ], className="mb-3 p-2 bg-light rounded"),
                                
                                dbc.Row([
                                    dbc.Col([
                                        html.Label([
                                            html.I(className="fas fa-calendar-day me-2"),
                                            "Date de debut"
                                        ], className="fw-bold mb-2"),
                                        dcc.DatePickerSingle(
                                            id='date-start-overview',
                                            placeholder='JJ/MM/AAAA',
                                            display_format='DD/MM/YYYY',
                                            date=datetime.now().strftime('%Y-%m-%d'),
                                            first_day_of_week=1,
                                            style={'width': '100%'}
                                        )
                                    ], width=12, md=4),
                                    dbc.Col([
                                        html.Label([
                                            html.I(className="fas fa-calendar-check me-2"),
                                            "Date de fin (optionnel)"
                                        ], className="fw-bold mb-2"),
                                        dcc.DatePickerSingle(
                                            id='date-end-overview',
                                            placeholder='Meme jour si vide',
                                            display_format='DD/MM/YYYY',
                                            first_day_of_week=1,
                                            style={'width': '100%'}
                                        )
                                    ], width=12, md=4),
                                    dbc.Col([
                                        html.Label(html.Br(), className="d-none d-md-block"),
                                        dbc.Button([
                                            html.I(className="fas fa-sync-alt me-2"),
                                            "Charger les vols"
                                        ], id='btn-load-flights', color='primary', size='lg', className='w-100')
                                    ], width=12, md=4),
                                ], className="g-3 mb-3"),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Button([
                                            html.I(className="fas fa-calendar-day me-2"),
                                            "Aujourd'hui"
                                        ], id='btn-today', color='info', outline=True, size='sm', className='me-2')
                                    ], width="auto"),
                                    dbc.Col([
                                        dbc.Button([
                                            html.I(className="fas fa-calendar-week me-2"),
                                            "Cette semaine"
                                        ], id='btn-this-week', color='info', outline=True, size='sm', className='me-2')
                                    ], width="auto"),
                                    dbc.Col([
                                        dbc.Button([
                                            html.I(className="fas fa-calendar-alt me-2"),
                                            "Ce mois"
                                        ], id='btn-this-month', color='info', outline=True, size='sm', className='me-2')
                                    ], width="auto"),
                                    dbc.Col([
                                        dbc.Button([
                                            html.I(className="fas fa-history me-2"),
                                            "Periode complete"
                                        ], id='btn-full-period', color='info', outline=True, size='sm')
                                    ], width="auto"),
                                ], className="mb-4"),
                                
                                html.Div(id='flights-table-container')
                            ], className="p-3")
                        ], label="Vue d'ensemble", tab_id="tab-overview", label_style={'fontSize': '16px'}),
                    ], id="tabs", active_tab="tab-search")
                ])
            ], className="shadow")
        ])
    ], className="mb-4"),
    
    dbc.Row(id='vols-kpi-cards', className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='vols-daily-chart', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Parametrage", className="mb-3"),
                    html.Div(id='delay-threshold-display', className="text-primary fw-bold text-center mb-2"),
                    dcc.Slider(
                        id='delay-threshold-slider',
                        min=5,
                        max=60,
                        step=5,
                        value=DEFAULT_DELAY_THRESHOLD,
                        marks={5: '5', 10: '10', 15: '15', 20: '20', 30: '30', 45: '45', 60: '60'},
                        tooltip={"placement": "bottom", "always_visible": False}
                    ),
                    html.Small("Ajustez le seuil de retard analyse pour aligner les KPI avec vos objectifs", className="d-block text-muted mt-2"),
                    html.Hr(className="my-3"),
                    html.H5("Definitions", className="mb-3"),
                    html.Ul([
                        html.Li([html.Strong("Retard:"), " >= seuil choisi"]),
                        html.Li([html.Strong("Prediction ML:"), " Probabilite > 50%"]),
                        html.Li([html.Strong("Risque:"), " LOW / MEDIUM / HIGH"]),
                        html.Li([html.Strong("Precision:"), " (TP + TN) / Total"])
                    ], style={'fontSize': '0.9rem'}),
                    html.Hr(),
                    html.H5("Donnees", className="mb-2"),
                    html.P(id='vols-data-info', style={'fontSize': '0.85rem'})
                ])
            ], className="shadow-sm h-100")
        ], width=4),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='vols-hourly-chart', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='vols-airlines-chart', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Insights Actionnables", className="mb-0")),
                dbc.CardBody(id='vols-insights')
            ], className="shadow-sm")
        ])
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Performance Modele ML", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='vols-ml-confusion', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Distribution Risque", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='vols-ml-risk', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ]),
])

@callback(
    Output('vols-kpi-cards', 'children'),
    Output('vols-data-info', 'children'),
    Input('interval-vols', 'n_intervals'),
    Input('delay-threshold-slider', 'value')
)
def update_kpis(n, delay_threshold):
    stats = fetch_api(f"/stats?delay_threshold={delay_threshold}")
    if not stats:
        return [], "Erreur connexion API"
    
    cards = [
        dbc.Col(create_metric_card(
            "Total Vols", f"{stats['total_flights']:,}", 
            f"{stats['date_min']} - {stats['date_max']}",
            "fa-plane", "#3498db"
        ), width=3),
        dbc.Col(create_metric_card(
            "Vols Retardes", f"{stats['delayed_flights']:,}", 
            f"{stats['delay_rate']:.1f}% (>={delay_threshold}min)",
            "fa-clock", "#e74c3c"
        ), width=3),
        dbc.Col(create_metric_card(
            "Retard Moyen", f"{stats['avg_delay']:.0f} min", 
            "Quand retard constate",
            "fa-hourglass-half", "#f39c12"
        ), width=3),
        dbc.Col(create_metric_card(
            "Precision ML", f"{stats['ml_accuracy']:.1f}%", 
            f"{stats['flights_with_ml']:,} predictions",
            "fa-brain", "#27ae60"
        ), width=3),
    ]
    
    info = [
        html.Strong(f"Periode: "), f"{stats['date_min']} au {stats['date_max']}", html.Br(),
        html.Strong(f"Vols: "), f"{stats['total_flights']:,} totaux, {stats['flights_with_ml']:,} avec ML", html.Br(),
        html.Strong(f"Retards: "), f"{stats['delayed_flights']:,} ({stats['delay_rate']:.1f}% >= {delay_threshold} min)"
    ]
    
    return cards, info

@callback(
    Output('vols-daily-chart', 'figure'),
    Input('interval-vols', 'n_intervals'),
    Input('delay-threshold-slider', 'value')
)
def update_daily(n, delay_threshold):
    data = fetch_api(f"/stats/daily?delay_threshold={delay_threshold}")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['delay_rate'] for d in data],
        mode='lines+markers',
        name='Taux retard',
        line=dict(color='#e74c3c', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(231, 76, 60, 0.1)'
    ))
    fig.update_layout(
        title=f"Evolution Taux Retard (>={delay_threshold}min)",
        xaxis_title="Date",
        yaxis_title="Taux retard (%)",
        template='plotly_white',
        height=350
    )
    return fig

@callback(
    Output('vols-hourly-chart', 'figure'),
    Input('interval-vols', 'n_intervals'),
    Input('delay-threshold-slider', 'value')
)
def update_hourly(n, delay_threshold):
    data = fetch_api(f"/stats/hourly?delay_threshold={delay_threshold}")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['hour'] for d in data],
        y=[d['delay_rate'] for d in data],
        marker_color=[
            '#e74c3c' if d['delay_rate'] >= 20 else '#f39c12' if d['delay_rate'] >= 12 else '#27ae60'
            for d in data
        ],
        text=[f"{d['delay_rate']:.1f}%" for d in data],
        textposition='outside'
    ))
    fig.update_layout(
        title="Risque Retard par Heure Depart",
        xaxis_title="Heure (0-23h)",
        yaxis_title="Taux retard (%)",
        template='plotly_white',
        height=350,
        showlegend=False
    )
    return fig

@callback(
    Output('vols-airlines-chart', 'figure'),
    Input('interval-vols', 'n_intervals'),
    Input('delay-threshold-slider', 'value')
)
def update_airlines(n, delay_threshold):
    data = fetch_api(f"/stats/airlines?delay_threshold={delay_threshold}&top=15")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[d['airline'] for d in data],
        x=[d['delay_rate'] for d in data],
        orientation='h',
        marker=dict(
            color=[d['delay_rate'] for d in data],
            colorscale='RdYlGn_r',
            showscale=False
        ),
        text=[f"{d['delay_rate']:.1f}%" for d in data],
        textposition='auto'
    ))
    fig.update_layout(
        title="Top 15 Compagnies - Taux Retard",
        xaxis_title="Taux retard (%)",
        template='plotly_white',
        height=400
    )
    return fig

@callback(
    Output('vols-ml-confusion', 'figure'),
    Input('interval-vols', 'n_intervals'),
    Input('delay-threshold-slider', 'value')
)
def update_ml_confusion(n, delay_threshold):
    data = fetch_api(f"/ml/confusion?delay_threshold={delay_threshold}")
    if not data:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=[[data['tn'], data['fp']], [data['fn'], data['tp']]],
        x=['Predit: A temps', 'Predit: Retard'],
        y=['Reel: A temps', 'Reel: Retard'],
        text=[[f'VN<br>{data["tn"]:,}', f'FP<br>{data["fp"]:,}'], 
              [f'FN<br>{data["fn"]:,}', f'VP<br>{data["tp"]:,}']],
        texttemplate='%{text}',
        colorscale='RdYlGn_r',
        showscale=False
    ))
    fig.update_layout(
        title=f"Matrice Confusion - Precision: {data['accuracy']:.1f}%",
        template='plotly_white',
        height=350
    )
    return fig

@callback(
    Output('vols-ml-risk', 'figure'),
    Input('interval-vols', 'n_intervals')
)
def update_ml_risk(n):
    data = fetch_api("/ml/risk-distribution")
    if not data:
        return go.Figure()
    
    colors = {'LOW': '#27ae60', 'MEDIUM': '#f39c12', 'HIGH': '#e74c3c'}
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['delay_risk_level'] for d in data],
        y=[d['count'] for d in data],
        marker_color=[colors.get(d['delay_risk_level'], '#95a5a6') for d in data],
        text=[d['count'] for d in data],
        textposition='auto'
    ))
    fig.update_layout(
        title="Distribution Niveaux Risque ML",
        xaxis_title="Niveau risque",
        yaxis_title="Nombre vols",
        template='plotly_white',
        height=350,
        showlegend=False
    )
    return fig

@callback(
    Output('delay-threshold-display', 'children'),
    Input('delay-threshold-slider', 'value')
)
def update_threshold_display(value):
    return f"Seuil retard analyse: >= {value} minutes"

@callback(
    Output('vols-insights', 'children'),
    Input('interval-vols', 'n_intervals'),
    Input('delay-threshold-slider', 'value')
)
def update_insights(n, delay_threshold):
    stats = fetch_api(f"/stats?delay_threshold={delay_threshold}")
    hourly = fetch_api(f"/stats/hourly?delay_threshold={delay_threshold}")
    airlines = fetch_api(f"/stats/airlines?delay_threshold={delay_threshold}&top=15")
    daily = fetch_api(f"/stats/daily?delay_threshold={delay_threshold}")
    if not stats or not hourly or not airlines or not daily:
        return html.P("Insights indisponibles (API non joignable)", className="text-muted mb-0")
    
    worst_hour = max(hourly, key=lambda x: x['delay_rate']) if hourly else None
    best_hour = min(hourly, key=lambda x: x['delay_rate']) if hourly else None
    riskiest_airline = max(airlines, key=lambda x: x['delay_rate']) if airlines else None
    safest_airline = min(airlines, key=lambda x: x['delay_rate']) if airlines else None
    busiest_day = max(daily, key=lambda x: x['total']) if daily else None
    
    items = [
        html.Li(
            f"{stats['delay_rate']:.1f}% des {stats['total_flights']:,} vols depassent {delay_threshold} minutes",
            className="mb-1"
        )
    ]
    if worst_hour and best_hour:
        items.append(html.Li(
            f"Heure la plus risquee: {int(worst_hour['hour'])}h avec {worst_hour['delay_rate']:.1f}% de retards",
            className="mb-1"
        ))
        items.append(html.Li(
            f"Heure la plus fiable: {int(best_hour['hour'])}h avec {best_hour['delay_rate']:.1f}%",
            className="mb-1"
        ))
    if riskiest_airline and safest_airline:
        items.append(html.Li(
            f"Compagnie la plus exposee: {riskiest_airline['airline']} ({riskiest_airline['delay_rate']:.1f}% retards)",
            className="mb-1"
        ))
        items.append(html.Li(
            f"Compagnie la plus fiable: {safest_airline['airline']} ({safest_airline['delay_rate']:.1f}% retards)",
            className="mb-1"
        ))
    if busiest_day:
        items.append(html.Li(
            f"Jour le plus charge: {busiest_day['date']} avec {busiest_day['total']:,} vols",
            className="mb-0"
        ))
    return html.Ul(items, className="mb-0")

@callback(
    Output('search-result-container', 'children'),
    Input('btn-search-flight', 'n_clicks'),
    Input('input-flight-number', 'value'),
    Input('input-departure-date', 'date')
)
def search_specific_flight(n_clicks, flight_number, departure_date):
    if n_clicks is None or n_clicks == 0:
        return None
    
    if not flight_number:
        return html.P("Veuillez saisir un numero de vol", className="text-warning")
    
    endpoint = f"/search-flights?flight_number={flight_number}"
    
    if departure_date:
        endpoint += f"&departure_date={departure_date}"
    
    flights = fetch_api(endpoint)
    
    if not flights or len(flights) == 0:
        return dbc.Alert(
            f"Aucun vol trouve pour {flight_number}" + (f" le {departure_date}" if departure_date else ""),
            color="warning"
        )
    
    for flight in flights:
        flight['delay_min'] = flight.get('delay_min') if flight.get('delay_min') is not None else 'N/A'
        flight['delay_prob_pct'] = f"{flight.get('delay_prob', 0)*100:.1f}%" if flight.get('delay_prob') else 'N/A'
        risk_level = flight.get('delay_risk_level')
        flight['risk'] = risk_level.upper() if risk_level else 'N/A'
        flight['prediction'] = flight.get('prediction_retard', 'N/A')
    
    columns = [
        {"name": "Vol", "id": "flight_number"},
        {"name": "De", "id": "from_airport"},
        {"name": "Vers", "id": "to_airport"},
        {"name": "Compagnie", "id": "airline_code"},
        {"name": "Depart", "id": "departure_scheduled_utc"},
        {"name": "Arrivee prevue", "id": "arrival_scheduled_utc"},
        {"name": "Arrivee reelle", "id": "arrival_actual_utc"},
        {"name": "Retard (min)", "id": "delay_min"},
        {"name": "Probabilite", "id": "delay_prob_pct"},
        {"name": "Risque", "id": "risk"},
        {"name": "Prediction", "id": "prediction"},
    ]
    
    style_data_conditional = [
        {
            'if': {'filter_query': '{risk} = "LOW"', 'column_id': 'risk'},
            'backgroundColor': '#d4edda',
            'color': '#155724'
        },
        {
            'if': {'filter_query': '{risk} = "MEDIUM"', 'column_id': 'risk'},
            'backgroundColor': '#fff3cd',
            'color': '#856404'
        },
        {
            'if': {'filter_query': '{risk} = "HIGH"', 'column_id': 'risk'},
            'backgroundColor': '#f8d7da',
            'color': '#721c24'
        },
        {
            'if': {'filter_query': '{prediction} = "OUI"', 'column_id': 'prediction'},
            'backgroundColor': '#dc3545',
            'color': 'white',
            'fontWeight': 'bold'
        },
        {
            'if': {'filter_query': '{prediction} = "NON"', 'column_id': 'prediction'},
            'backgroundColor': '#28a745',
            'color': 'white',
            'fontWeight': 'bold'
        },
    ]
    
    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            html.Strong(f"{len(flights)} vol(s) trouve(s)"),
            f" pour {flight_number}" + (f" le {departure_date}" if departure_date else "")
        ], color="success", className="d-flex align-items-center"),
        dbc.Card([
            dbc.CardBody([
                dash_table.DataTable(
                    columns=columns,
                    data=flights,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontSize': '14px',
                        'fontFamily': 'Arial, sans-serif'
                    },
                    style_header={
                        'backgroundColor': '#2c3e50',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'border': '1px solid #34495e',
                        'textAlign': 'center'
                    },
                    style_data={
                        'border': '1px solid #dee2e6'
                    },
                    style_data_conditional=style_data_conditional
                )
            ])
        ], className="shadow-sm")
    ])

@callback(
    Output('date-start-overview', 'date'),
    Output('date-end-overview', 'date'),
    Output('flights-table-container', 'children'),
    Input('btn-today', 'n_clicks'),
    Input('btn-this-week', 'n_clicks'),
    Input('btn-this-month', 'n_clicks'),
    Input('btn-full-period', 'n_clicks'),
    Input('btn-load-flights', 'n_clicks'),
    Input('date-start-overview', 'date'),
    Input('date-end-overview', 'date'),
    prevent_initial_call=False
)
def update_date_range_and_load_flights(btn_today, btn_week, btn_month, btn_full, btn_load, date_start, date_end):
    ctx = dash.callback_context
    
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return dash.no_update, dash.no_update, html.Div([
            dbc.Alert([
                html.I(className="fas fa-arrow-up me-2"),
                html.Strong("Utilisez les boutons rapides ci-dessus, selectionnez des dates ou cliquez sur 'Charger les vols'")
            ], color="info", className="text-center")
        ])
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    today = datetime.now()
    
    if button_id == 'btn-today':
        new_start = today.strftime('%Y-%m-%d')
        new_end = today.strftime('%Y-%m-%d')
        return new_start, new_end, load_flights_data(new_start, new_end)
    elif button_id == 'btn-this-week':
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)
        new_start = start_week.strftime('%Y-%m-%d')
        new_end = end_week.strftime('%Y-%m-%d')
        return new_start, new_end, load_flights_data(new_start, new_end)
    elif button_id == 'btn-this-month':
        start_month = today.replace(day=1)
        if today.month == 12:
            end_month = today.replace(day=31)
        else:
            end_month = (today.replace(month=today.month+1, day=1) - timedelta(days=1))
        new_start = start_month.strftime('%Y-%m-%d')
        new_end = end_month.strftime('%Y-%m-%d')
        return new_start, new_end, load_flights_data(new_start, new_end)
    elif button_id == 'btn-full-period':
        start_full = today - timedelta(weeks=2)
        end_full = today + timedelta(weeks=4)
        new_start = start_full.strftime('%Y-%m-%d')
        new_end = end_full.strftime('%Y-%m-%d')
        return new_start, new_end, load_flights_data(new_start, new_end)
    elif button_id == 'btn-load-flights':
        if not date_start:
            return dash.no_update, dash.no_update, dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                "Veuillez selectionner au moins une date de debut"
            ], color="warning")
        
        end_to_use = date_end if date_end else date_start
        return dash.no_update, dash.no_update, load_flights_data(date_start, end_to_use)
    elif button_id in ['date-start-overview', 'date-end-overview']:
        if date_start:
            end_to_use = date_end if date_end else date_start
            return dash.no_update, dash.no_update, load_flights_data(date_start, end_to_use)
    
    return dash.no_update, dash.no_update, dash.no_update

def load_flights_data(date_start, date_end):
    flights = fetch_api(f"/search-flights?date_start={date_start}&date_end={date_end}")
    
    if not flights or len(flights) == 0:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-circle me-2"),
            f"Aucun vol trouve pour la periode du {date_start} au {date_end}"
        ], color="info")
    
    for flight in flights:
        flight['delay_min'] = flight.get('delay_min') if flight.get('delay_min') is not None else 'N/A'
        flight['delay_prob_pct'] = f"{flight.get('delay_prob', 0)*100:.1f}%" if flight.get('delay_prob') else 'N/A'
        risk_level = flight.get('delay_risk_level')
        flight['risk'] = risk_level.upper() if risk_level else 'N/A'
        flight['prediction'] = flight.get('prediction_retard', 'N/A')
    
    columns = [
        {"name": "Vol", "id": "flight_number"},
        {"name": "De", "id": "from_airport"},
        {"name": "Vers", "id": "to_airport"},
        {"name": "Compagnie", "id": "airline_code"},
        {"name": "Depart", "id": "departure_scheduled_utc"},
        {"name": "Arrivee prevue", "id": "arrival_scheduled_utc"},
        {"name": "Arrivee reelle", "id": "arrival_actual_utc"},
        {"name": "Retard (min)", "id": "delay_min"},
        {"name": "Probabilite", "id": "delay_prob_pct"},
        {"name": "Risque", "id": "risk"},
        {"name": "Prediction", "id": "prediction"},
    ]
    
    style_data_conditional = [
        {
            'if': {'filter_query': '{risk} = "LOW"', 'column_id': 'risk'},
            'backgroundColor': '#d4edda',
            'color': '#155724'
        },
        {
            'if': {'filter_query': '{risk} = "MEDIUM"', 'column_id': 'risk'},
            'backgroundColor': '#fff3cd',
            'color': '#856404'
        },
        {
            'if': {'filter_query': '{risk} = "HIGH"', 'column_id': 'risk'},
            'backgroundColor': '#f8d7da',
            'color': '#721c24'
        },
        {
            'if': {'filter_query': '{prediction} = "OUI"', 'column_id': 'prediction'},
            'backgroundColor': '#dc3545',
            'color': 'white',
            'fontWeight': 'bold'
        },
        {
            'if': {'filter_query': '{prediction} = "NON"', 'column_id': 'prediction'},
            'backgroundColor': '#28a745',
            'color': 'white',
            'fontWeight': 'bold'
        },
    ]
    
    total_with_prediction = sum(1 for f in flights if f.get('prediction') not in ['N/A', None])
    total_delayed_predicted = sum(1 for f in flights if f.get('prediction') == 'OUI')
    
    total_in_db = fetch_api("/stats")
    total_db_count = total_in_db.get('total_flights', 0) if total_in_db else 0
    
    period_display = f"{date_start}" if date_start == date_end else f"{date_start} au {date_end}"
    
    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-calendar-check me-2"),
            html.Strong(f"Periode: {period_display}")
        ], color="info", className="d-flex align-items-center mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-database fa-2x text-primary mb-2"),
                            html.H4(f"{len(flights):,}", className="mb-1"),
                            html.Small("Vols affiches", className="text-muted")
                        ], className="text-center")
                    ])
                ], className="border-primary")
            ], width=6, lg=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-brain fa-2x text-info mb-2"),
                            html.H4(f"{total_with_prediction:,}", className="mb-1"),
                            html.Small("Avec prediction ML", className="text-muted")
                        ], className="text-center")
                    ])
                ], className="border-info")
            ], width=6, lg=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-exclamation-triangle fa-2x text-warning mb-2"),
                            html.H4(f"{total_delayed_predicted:,}", className="mb-1"),
                            html.Small("Retards predits", className="text-muted")
                        ], className="text-center")
                    ])
                ], className="border-warning")
            ], width=6, lg=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-chart-line fa-2x text-success mb-2"),
                            html.H4(f"{total_db_count:,}", className="mb-1"),
                            html.Small("Total en base", className="text-muted")
                        ], className="text-center")
                    ])
                ], className="border-success")
            ], width=6, lg=3),
        ], className="g-3 mb-3"),
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-table me-2"),
                html.Strong("Tableau des vols"),
                html.Span(" - Utilisez les filtres dans les colonnes pour rechercher", className="text-muted ms-2")
            ]),
            dbc.CardBody([
                dash_table.DataTable(
                    id='flights-table',
                    columns=columns,
                    data=flights,
                    filter_action="native",
                    sort_action="native",
                    sort_mode="multi",
                    page_action="native",
                    page_current=0,
                    page_size=50,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontSize': '14px',
                        'fontFamily': 'Arial, sans-serif',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    style_header={
                        'backgroundColor': '#2c3e50',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'border': '1px solid #34495e',
                        'textAlign': 'center',
                        'fontSize': '15px'
                    },
                    style_data={
                        'border': '1px solid #dee2e6'
                    },
                    style_filter={
                        'backgroundColor': '#ecf0f1',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=style_data_conditional
                )
            ])
        ], className="shadow")
    ])
