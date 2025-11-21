"""
Page Vols - Dashboard Principal
Analyse des vols et predictions ML
"""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests

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
