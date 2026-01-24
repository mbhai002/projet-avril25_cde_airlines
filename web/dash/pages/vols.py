"""
Page Vols - Dashboard de Synthèse
"""

import dash
from dash import html, dcc, Input, Output, callback, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import os

dash.register_page(__name__, path='/', name='Synthèse')

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
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
    ], className="shadow-sm h-100 border-0")

layout = html.Div([
    dcc.Interval(id='interval-vols', interval=120000, n_intervals=0),
    
    dbc.Row([
        dbc.Col([
            html.H2("Analyse des Vols et Synthèse Opérationnelle", className="text-center mb-4")
        ])
    ]),

    # Bloc de Paramétrage
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # Période
                dbc.Col([
                    html.Label([html.I(className="fas fa-calendar-alt me-2"), html.Strong("Période d'analyse")], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            html.Small("Du", className="text-muted d-block"),
                            dcc.DatePickerSingle(
                                id='stats-date-start',
                                date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d'),
                                display_format='DD/MM/YYYY',
                                first_day_of_week=1,
                                style={'width': '100%'}
                            )
                        ], width=6),
                        dbc.Col([
                            html.Small("Au", className="text-muted d-block"),
                            dcc.DatePickerSingle(
                                id='stats-date-end',
                                date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                                display_format='DD/MM/YYYY',
                                first_day_of_week=1,
                                style={'width': '100%'}
                            )
                        ], width=6),
                    ], className="g-2"),
                ], width=12, lg=4),
                
                # Slider Seuil
                dbc.Col([
                    html.Div(id='delay-threshold-display', className="text-primary fw-bold mb-2"),
                    dcc.Slider(
                        id='delay-threshold-slider',
                        min=5, max=60, step=5, value=DEFAULT_DELAY_THRESHOLD,
                        marks={5: '5', 15: '15', 30: '30', 45: '45', 60: '60'},
                        tooltip={"placement": "bottom", "always_visible": False}
                    ),
                    html.Small("Ajustez le seuil de retard pour les calculs.", className="text-muted d-block mt-3"),
                ], width=12, lg=4),

                # Informations
                dbc.Col([
                    html.H6("Informations", className="fw-bold mb-2"),
                    html.Ul([
                        html.Li([html.Strong("Retard:"), " >= seuil"], className="small"),
                        html.Li([html.Strong("Précision:"), " Performance ML"], className="small")
                    ], className="mb-1 ps-3"),
                ], width=12, lg=4),
            ]),
            
            # Bouton de rafraîchissement au centre
            html.Hr(className="my-3"),
            html.Div([
                dbc.Button([
                    html.I(className="fas fa-sync-alt me-2"),
                    "Actualiser les graphiques"
                ], id='btn-stats-refresh', color='primary', className='px-5'),
                dcc.Loading(
                    id="loading-stats-btn",
                    type="circle",
                    children=html.Div(id="loading-output-stats"),
                    className="mt-3"
                ),
                html.Div(id='vols-data-info', style={'fontSize': '0.75rem'}, className="text-muted mt-2")
            ], className="text-center d-flex flex-column align-items-center")
        ])
    ], className="shadow-sm border-0 mb-4 bg-light"),
    
    # Zone de résultats
    html.Div([
        dbc.Row(id='vols-kpi-cards', className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(id='vols-daily-chart', config={'displayModeBar': False}),
                        html.Hr(className="my-2"),
                        html.Small([
                            html.I(className="fas fa-calculator me-2 text-muted"),
                            html.Strong("Calcul : "),
                            "Taux retard = (Nombre vols retardés / Total vols) × 100"
                        ], className="text-muted d-block text-center")
                    ])
                ], className="shadow-sm border-0")
            ], width=12),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([dbc.CardBody([dcc.Graph(id='vols-hourly-chart', config={'displayModeBar': False})])], className="shadow-sm border-0")
            ], width=6),
            dbc.Col([
                dbc.Card([dbc.CardBody([dcc.Graph(id='vols-airlines-chart', config={'displayModeBar': False})])], className="shadow-sm border-0")
            ], width=6),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Insights Actionnables", className="mb-0")),
                    dbc.CardBody(id='vols-insights')
                ], className="shadow-sm border-0")
            ])
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Performance Modèle ML", className="mb-0")),
                    dbc.CardBody([dcc.Graph(id='vols-ml-confusion', config={'displayModeBar': False})])
                ], className="shadow-sm border-0")
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Distribution Risque", className="mb-0")),
                    dbc.CardBody([dcc.Graph(id='vols-ml-risk', config={'displayModeBar': False})])
                ], className="shadow-sm border-0")
            ], width=6),
        ]),
    ], id="vols-content-trigger")
])

@callback(
    Output('vols-kpi-cards', 'children'),
    Output('vols-daily-chart', 'figure'),
    Output('vols-hourly-chart', 'figure'),
    Output('vols-airlines-chart', 'figure'),
    Output('vols-ml-confusion', 'figure'),
    Output('vols-ml-risk', 'figure'),
    Output('vols-insights', 'children'),
    Output('vols-data-info', 'children'),
    Output('loading-output-stats', 'children'),
    Input('btn-stats-refresh', 'n_clicks'),
    Input('interval-vols', 'n_intervals'),
    State('delay-threshold-slider', 'value'),
    State('stats-date-start', 'date'),
    State('stats-date-end', 'date'),
    prevent_initial_call=False
)
def update_all_stats(n_clicks, n_int, delay_threshold, date_start, date_end):
    # Construction robuste des paramètres d'URI
    params = f"?delay_threshold={delay_threshold}"
    if date_start: params += f"&date_start={date_start}"
    if date_end: params += f"&date_end={date_end}"
    
    # 1. KPIs
    stats = fetch_api(f"/stats{params}")
    kpi_children = []
    if stats:
        kpi_children = [
            dbc.Col(create_metric_card("Total Vols", f"{stats['total_flights']:,}", f"{stats['date_min']} - {stats['date_max']}", "fa-plane", "#3498db"), width=3),
            dbc.Col(create_metric_card("Vols Retardés", f"{stats['delayed_flights']:,}", f"{stats['delay_rate']:.1f}% (>={delay_threshold}min)", "fa-clock", "#e74c3c"), width=3),
            dbc.Col(create_metric_card("Retard Moyen", f"{stats['avg_delay']:.0f} min", "Quand retard constaté", "fa-hourglass-half", "#f39c12"), width=3),
            dbc.Col(create_metric_card("Précision ML", f"{stats['ml_accuracy']:.1f}%", f"{stats['flights_with_ml']:,} prédictions", "fa-brain", "#27ae60"), width=3),
        ]

    # 2. Daily Chart
    daily_data = fetch_api(f"/stats/daily{params}")
    fig_daily = go.Figure()
    if daily_data:
        fig_daily.add_trace(go.Scatter(x=[d['date'] for d in daily_data], y=[d['delay_rate'] for d in daily_data], mode='lines+markers', line=dict(color='#e74c3c', width=3), fill='tozeroy', fillcolor='rgba(231, 76, 60, 0.1)'))
    fig_daily.update_layout(title=f"Évolution Taux Retard (>={delay_threshold}min)", template='plotly_white', height=350, margin=dict(l=20, r=20, t=40, b=20))

    # 3. Hourly
    hourly_data = fetch_api(f"/stats/hourly{params}")
    fig_hourly = go.Figure()
    if hourly_data:
        fig_hourly.add_trace(go.Bar(x=[d['hour'] for d in hourly_data], y=[d['delay_rate'] for d in hourly_data], marker_color=['#e74c3c' if d['delay_rate'] >= 20 else '#f39c12' if d['delay_rate'] >= 12 else '#27ae60' for d in hourly_data]))
    fig_hourly.update_layout(title="Risque Retard par Heure", template='plotly_white', height=350, margin=dict(l=20, r=20, t=40, b=20))

    # 4. Airlines
    airlines_data = fetch_api(f"/stats/airlines{params}&top=15")
    fig_airlines = go.Figure()
    if airlines_data:
        fig_airlines.add_trace(go.Bar(y=[d.get('airline_name') or d['airline'] for d in airlines_data], x=[d['delay_rate'] for d in airlines_data], orientation='h', marker=dict(color=[d['delay_rate'] for d in airlines_data], colorscale='RdYlGn_r')))
    fig_airlines.update_layout(title="Top 15 Compagnies - Taux Retard", template='plotly_white', height=400, yaxis={'autorange': 'reversed'}, margin=dict(l=20, r=20, t=40, b=20))

    # 5. ML Confusion
    ml_conf = fetch_api(f"/ml/confusion{params}")
    fig_conf = go.Figure()
    if ml_conf:
        fig_conf.add_trace(go.Heatmap(z=[[ml_conf['tn'], ml_conf['fp']], [ml_conf['fn'], ml_conf['tp']]], x=['Stable', 'Retard'], y=['Stable', 'Retard'], colorscale='RdYlGn_r', showscale=False))
        fig_conf.update_layout(title=f"Matrice Confusion (Précision: {ml_conf['accuracy']:.1f}%)")
    fig_conf.update_layout(template='plotly_white', height=350, margin=dict(l=20, r=20, t=40, b=20))

    # 6. ML Risk
    # Suppression du premier '&' car pas de delay_threshold sur cet endpoint
    risk_params = params.replace('?delay_threshold=' + str(delay_threshold) + '&', '?', 1).replace('?delay_threshold=' + str(delay_threshold), '?', 1)
    risk_data = fetch_api(f"/ml/risk-distribution{risk_params}")
    fig_risk = go.Figure()
    if risk_data:
        colors = {'LOW': '#27ae60', 'MEDIUM': '#f39c12', 'HIGH': '#e74c3c'}
        fig_risk.add_trace(go.Bar(x=[d['delay_risk_level'] for d in risk_data], y=[d['count'] for d in risk_data], marker_color=[colors.get(d['delay_risk_level'], '#95a5a6') for d in risk_data]))
    fig_risk.update_layout(title="Distribution Risque ML", template='plotly_white', height=350, margin=dict(l=20, r=20, t=40, b=20))

    # 7. Insights
    insight_content = "Veuillez actualiser les données."
    if stats and hourly_data and airlines_data:
        worst_h = max(hourly_data, key=lambda x: x['delay_rate']) if hourly_data else None
        risk_a = max(airlines_data, key=lambda x: x['delay_rate']) if airlines_data else None
        insight_items = [html.Li(f"{stats['delay_rate']:.1f}% des vols dépassent le seuil de {delay_threshold} min")]
        if worst_h: insight_items.append(html.Li(f"Heure critique: {int(worst_h['hour'])}h ({worst_h['delay_rate']:.1f}% de retards)"))
        if risk_a: insight_items.append(html.Li(f"Compagnie à risque: {risk_a.get('airline_name') or risk_a['airline']}"))
        insight_content = html.Ul(insight_items)
    
    info = f"Mis à jour à {datetime.now().strftime('%H:%M:%S')}"
    return kpi_children, fig_daily, fig_hourly, fig_airlines, fig_conf, fig_risk, insight_content, info, ""

@callback(Output('delay-threshold-display', 'children'), Input('delay-threshold-slider', 'value'))
def update_threshold_display(value):
    return f"Seuil retard analyse: {value} min"
