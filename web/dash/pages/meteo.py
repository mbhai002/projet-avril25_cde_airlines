"""
Page Meteo - Observations et Previsions
Analyse meteorologique detaillee avec donnees METAR/TAF par aeroport
"""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime, timedelta
import os
import csv

dash.register_page(__name__, path='/meteo', name='Meteo')

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')
DELAY_THRESHOLD = 10

# =============================================================================
# CHARGEMENT REFERENCE AEROPORTS (ICAO -> Nom / Ville)
# =============================================================================

def _load_airport_names():
    """Charge le fichier airports_ref.csv pour mapper les codes ICAO aux noms."""
    icao_map = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Chemin 1: a cote du script (pages/ monte dans Docker)
    csv_path = os.path.join(base_dir, 'airports_ref.csv')
    if not os.path.exists(csv_path):
        # Chemin 2: dans flight-collector (hors Docker)
        csv_path = os.path.join(base_dir, '..', '..', '..', 'flight-collector', 'utils', 'airports_ref.csv')
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                icao = row.get('icao_code', '').strip()
                name = row.get('name', '').strip()
                iata = row.get('code_iata', '').strip()
                if icao and name:
                    # Extraire la ville du nom (avant "International", "Airport", etc.)
                    short = name.replace(' International Airport', '').replace(' Airport', '')
                    short = short.replace(' Intl', '').strip()
                    icao_map[icao] = {'name': name, 'short': short, 'iata': iata}
    except Exception:
        pass
    return icao_map

AIRPORT_NAMES = _load_airport_names()


def get_airport_label(icao):
    """Retourne un label lisible pour un code ICAO."""
    info = AIRPORT_NAMES.get(icao)
    if info:
        iata_str = f"/{info['iata']}" if info.get('iata') else ''
        return f"{info['short']} ({icao}{iata_str})"
    return icao


def get_airport_short(icao):
    """Retourne un nom court pour un code ICAO (pour les axes de graphes)."""
    info = AIRPORT_NAMES.get(icao)
    if info:
        short = info['short']
        # Tronquer si trop long
        if len(short) > 20:
            short = short[:18] + '..'
        return short
    return icao

# =============================================================================
# DICTIONNAIRES D'ABREVIATIONS METEOROLOGIQUES
# =============================================================================

# Abreviations wx_string (phenomenes meteo METAR)
WX_ABBREVIATIONS = {
    # Descripteurs
    'MI': 'Mince (shallow)',
    'BC': 'Bancs (patches)',
    'PR': 'Partiel (partial)',
    'DR': 'Chasse basse (low drifting)',
    'BL': 'Chasse elevee (blowing)',
    'SH': 'Averses (showers)',
    'TS': 'Orage (thunderstorm)',
    'FZ': 'Givrant (freezing)',
    'RE': 'Recent',
    'VC': 'Au voisinage (vicinity)',
    # Precipitations
    'RA': 'Pluie (rain)',
    'DZ': 'Bruine (drizzle)',
    'SN': 'Neige (snow)',
    'SG': 'Neige en grains (snow grains)',
    'IC': 'Cristaux de glace (ice crystals)',
    'PL': 'Granules de glace (ice pellets)',
    'GR': 'Grele (hail >= 5mm)',
    'GS': 'Gresil (small hail < 5mm)',
    'UP': 'Precipitation inconnue (unknown)',
    # Obscurcissements
    'FG': 'Brouillard (fog, vis < 1 km)',
    'BR': 'Brume (mist, 1-5 km vis)',
    'HZ': 'Brume seche (haze)',
    'FU': 'Fumee (smoke)',
    'VA': 'Cendres volcaniques (volcanic ash)',
    'DU': 'Poussiere etendue (dust)',
    'SA': 'Sable (sand)',
    'PY': 'Embruns (spray)',
    # Autres
    'SQ': 'Grain (squall)',
    'PO': 'Tourbillons de sable/poussiere',
    'DS': 'Tempete de sable (dust storm)',
    'SS': 'Tempete de sable (sandstorm)',
    'FC': 'Trombe/tornade (funnel cloud)',
    # Intensite
    '+': 'Fort (heavy)',
    '-': 'Faible (light)',
}

# Categories de vol
FLIGHT_CATEGORY_INFO = {
    'VFR': {
        'name': 'Vol a Vue (Visual Flight Rules)',
        'color': '#27ae60',
        'criteria': 'Visibilite >= 5 mi ET plafond >= 3000 ft',
        'description': 'Conditions optimales pour le vol a vue. Le pilote navigue visuellement.',
        'icon': 'fa-sun'
    },
    'MVFR': {
        'name': 'VFR Marginal',
        'color': '#f39c12',
        'criteria': 'Visibilite 3-5 mi OU plafond 1000-3000 ft',
        'description': 'Conditions difficiles mais vol a vue encore possible avec prudence.',
        'icon': 'fa-cloud-sun'
    },
    'IFR': {
        'name': 'Vol aux Instruments (Instrument Flight Rules)',
        'color': '#e74c3c',
        'criteria': 'Visibilite 1-3 mi OU plafond 500-1000 ft',
        'description': 'Vol uniquement avec instruments. Qualification IFR requise.',
        'icon': 'fa-cloud'
    },
    'LIFR': {
        'name': 'IFR Limite (Low IFR)',
        'color': '#8e44ad',
        'criteria': 'Visibilite < 1 mi OU plafond < 500 ft',
        'description': 'Conditions tres dangereuses. Equipement avance requis.',
        'icon': 'fa-smog'
    },
    'UNKNOWN': {
        'name': 'Inconnu',
        'color': '#95a5a6',
        'criteria': 'Donnees insuffisantes',
        'description': 'Categorie non determinee.',
        'icon': 'fa-question-circle'
    }
}

# Codes de couverture nuageuse (sky_cover)
SKY_COVER_CODES = {
    'FEW': {'fr': 'Peu de nuages', 'en': 'Few clouds', 'coverage': '1/8 - 2/8 (12-25%)'},
    'SCT': {'fr': 'Nuages epars', 'en': 'Scattered', 'coverage': '3/8 - 4/8 (37-50%)'},
    'BKN': {'fr': 'Ciel fragmente', 'en': 'Broken', 'coverage': '5/8 - 7/8 (62-87%)'},
    'OVC': {'fr': 'Ciel couvert', 'en': 'Overcast', 'coverage': '8/8 (100%)'},
    'NSC': {'fr': 'Pas de nuages significatifs', 'en': 'No Significant Cloud', 'coverage': '-'},
    'SKC': {'fr': 'Ciel degage', 'en': 'Sky Clear', 'coverage': '0%'},
    'NCD': {'fr': 'Nuages non detectes', 'en': 'No Clouds Detected', 'coverage': '-'},
    'CLR': {'fr': 'Ciel degage (auto)', 'en': 'Clear (automated)', 'coverage': '0% (< 12000 ft)'},
    'VV': {'fr': 'Visibilite verticale', 'en': 'Vertical Visibility', 'coverage': 'Obscurci'},
}

# Unites meteorologiques
METEO_UNITS = {
    'kt': 'Noeuds (knots) - 1 kt = 1.852 km/h',
    'mi': 'Miles terrestres (statute miles) - 1 mi = 1.609 km',
    'ft': 'Pieds (feet) - 1 ft = 0.3048 m',
    'hPa': 'Hectopascals (pression atmospherique)',
    'inHg': 'Pouces de mercure (inches of mercury) - 1 inHg = 33.86 hPa',
    'C': 'Degres Celsius',
    'AGL': 'Au-dessus du sol (Above Ground Level)',
}


def decode_wx_string(wx):
    """Decode une chaine wx_string METAR en description lisible."""
    if not wx or wx == 'CLEAR':
        return 'Ciel degage / Pas de phenomene'

    parts = []
    intensity = ''

    # Gerer l'intensite
    clean_wx = wx.strip()
    if clean_wx.startswith('+'):
        intensity = 'Fort '
        clean_wx = clean_wx[1:]
    elif clean_wx.startswith('-'):
        intensity = 'Faible '
        clean_wx = clean_wx[1:]

    # Decouper en codes de 2 caracteres
    remaining = clean_wx
    while remaining:
        found = False
        for length in [2]:
            code = remaining[:length]
            if code in WX_ABBREVIATIONS:
                parts.append(WX_ABBREVIATIONS[code])
                remaining = remaining[length:]
                found = True
                break
        if not found:
            remaining = remaining[1:]

    if parts:
        return f"{intensity}{' + '.join(parts)}"
    return wx


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


def build_date_params(date_start, date_end, station=None):
    """Construit les parametres de date et station pour les endpoints API."""
    parts = []
    if date_start:
        parts.append(f"date_start={date_start}")
    if date_end:
        parts.append(f"date_end={date_end}")
    if station:
        parts.append(f"station={station}")
    return ('?' + '&'.join(parts)) if parts else ""


# =============================================================================
# SECTION GLOSSAIRE / REFERENCE
# =============================================================================

def build_glossary_section():
    """Construit la section glossaire detaillee."""

    # Categories de vol
    flight_cat_rows = []
    for code, info in FLIGHT_CATEGORY_INFO.items():
        if code == 'UNKNOWN':
            continue
        flight_cat_rows.append(
            html.Tr([
                html.Td(
                    html.Span(code, style={
                        'backgroundColor': info['color'], 'color': 'white',
                        'padding': '3px 10px', 'borderRadius': '4px', 'fontWeight': 'bold'
                    })
                ),
                html.Td(info['name']),
                html.Td(info['criteria']),
                html.Td(info['description'], style={'fontSize': '0.85rem'}),
            ])
        )

    # Phenomenes meteo wx_string
    wx_categories = {
        'Precipitations': ['RA', 'DZ', 'SN', 'SG', 'IC', 'PL', 'GR', 'GS'],
        'Obscurcissements': ['FG', 'BR', 'HZ', 'FU', 'DU', 'SA'],
        'Descripteurs': ['MI', 'BC', 'SH', 'TS', 'FZ', 'BL', 'DR', 'VC'],
        'Autres': ['SQ', 'PO', 'DS', 'SS', 'FC'],
        'Intensite': ['+', '-'],
    }

    wx_rows = []
    for category, codes in wx_categories.items():
        wx_rows.append(html.Tr([
            html.Td(html.Strong(category), colSpan=3,
                     style={'backgroundColor': '#f8f9fa', 'paddingTop': '8px'})
        ]))
        for code in codes:
            if code in WX_ABBREVIATIONS:
                wx_rows.append(html.Tr([
                    html.Td(html.Code(code, style={'fontSize': '0.95rem', 'fontWeight': 'bold'})),
                    html.Td(WX_ABBREVIATIONS[code]),
                ]))

    # Couverture nuageuse
    sky_rows = []
    for code, info in SKY_COVER_CODES.items():
        sky_rows.append(html.Tr([
            html.Td(html.Code(code, style={'fontWeight': 'bold'})),
            html.Td(info['fr']),
            html.Td(info['en'], style={'fontStyle': 'italic', 'color': '#666'}),
            html.Td(info['coverage']),
        ]))

    # Unites
    unit_rows = []
    for unit, desc in METEO_UNITS.items():
        unit_rows.append(html.Tr([
            html.Td(html.Code(unit, style={'fontWeight': 'bold'})),
            html.Td(desc),
        ]))

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-book me-2"),
                        "Glossaire Meteorologique Aeronautique"
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Accordion([
                        # Categories de vol
                        dbc.AccordionItem([
                            dbc.Table([
                                html.Thead(html.Tr([
                                    html.Th("Code", style={'width': '80px'}),
                                    html.Th("Nom complet"),
                                    html.Th("Criteres"),
                                    html.Th("Description"),
                                ])),
                                html.Tbody(flight_cat_rows)
                            ], striped=True, bordered=True, hover=True, size='sm',
                               className="mb-0")
                        ], title="Categories de Vol (VFR / MVFR / IFR / LIFR)", item_id="cat-vol"),

                        # Phenomenes meteo
                        dbc.AccordionItem([
                            html.P([
                                "Les codes meteo METAR se composent d'un ",
                                html.Strong("prefixe d'intensite"),
                                " (- = faible, + = fort), de ",
                                html.Strong("descripteurs"),
                                " (SH, TS, FZ...) et de ",
                                html.Strong("phenomenes"),
                                " (RA, SN, FG...). ",
                                "Exemple : ", html.Code("-SHRA"), " = Averses de pluie faibles ; ",
                                html.Code("+TSRA"), " = Orage avec forte pluie ; ",
                                html.Code("FZFG"), " = Brouillard givrant."
                            ], className="text-muted mb-3", style={'fontSize': '0.9rem'}),
                            dbc.Table([
                                html.Thead(html.Tr([
                                    html.Th("Code", style={'width': '60px'}),
                                    html.Th("Signification"),
                                ])),
                                html.Tbody(wx_rows)
                            ], striped=True, bordered=True, hover=True, size='sm',
                               className="mb-0")
                        ], title="Codes Phenomenes Meteo (wx_string)", item_id="wx-codes"),

                        # Couverture nuageuse
                        dbc.AccordionItem([
                            html.P([
                                "La couverture nuageuse est mesuree en ", html.Strong("octas"),
                                " (huitiemes de ciel). La base nuageuse est en ",
                                html.Strong("pieds AGL"), " (au-dessus du sol)."
                            ], className="text-muted mb-3", style={'fontSize': '0.9rem'}),
                            dbc.Table([
                                html.Thead(html.Tr([
                                    html.Th("Code", style={'width': '60px'}),
                                    html.Th("Francais"),
                                    html.Th("Anglais"),
                                    html.Th("Couverture"),
                                ])),
                                html.Tbody(sky_rows)
                            ], striped=True, bordered=True, hover=True, size='sm',
                               className="mb-0")
                        ], title="Codes Couverture Nuageuse (Sky Cover)", item_id="sky-cover"),

                        # Unites
                        dbc.AccordionItem([
                            dbc.Table([
                                html.Thead(html.Tr([
                                    html.Th("Unite", style={'width': '80px'}),
                                    html.Th("Signification"),
                                ])),
                                html.Tbody(unit_rows)
                            ], striped=True, bordered=True, hover=True, size='sm',
                               className="mb-0"),
                            html.Hr(),
                            html.H6("Ressources METAR / TAF", className="mt-3"),
                            html.Ul([
                                html.Li([html.Strong("METAR"), " (METeorological Aerodrome Report) : observation meteorologique reelle prise a un aeroport, mise a jour toutes les 30 a 60 min."]),
                                html.Li([html.Strong("TAF"), " (Terminal Aerodrome Forecast) : prevision meteorologique pour un aeroport, couvrant 24-30h."]),
                                html.Li([html.Strong("Station ID"), " : code OACI de 4 lettres identifiant l'aeroport (ex: LFPG = Paris CDG, KJFK = New York JFK)."]),
                            ], style={'fontSize': '0.9rem'})
                        ], title="Unites de Mesure & Ressources", item_id="units"),

                    ], start_collapsed=True, always_open=True),
                ])
            ], className="shadow-sm")
        ])
    ], className="mb-4")


# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

layout = html.Div([
    dcc.Interval(id='interval-meteo', interval=120000, n_intervals=0),

    # Titre
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-cloud-sun-rain me-3"),
                "Analyse Meteorologique Aeronautique"
            ], className="text-center mb-2"),
            html.P("Donnees METAR (observations) et TAF (previsions) par aeroport",
                   className="text-center text-muted mb-4", style={'fontSize': '0.95rem'})
        ])
    ]),

    # Filtres : Periode + Aeroport
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Date filters
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-calendar-alt me-2"),
                                html.Strong("Periode d'analyse")
                            ], className="mb-2"),
                            dbc.Row([
                                dbc.Col([
                                    dcc.DatePickerSingle(
                                        id='meteo-date-start',
                                        date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d'),
                                        display_format='DD/MM/YYYY',
                                        placeholder='Date debut',
                                        first_day_of_week=1,
                                        style={'width': '100%'}
                                    )
                                ], width=6),
                                dbc.Col([
                                    dcc.DatePickerSingle(
                                        id='meteo-date-end',
                                        date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                                        display_format='DD/MM/YYYY',
                                        placeholder='Date fin',
                                        first_day_of_week=1,
                                        style={'width': '100%'}
                                    )
                                ], width=6),
                            ], className="g-2"),
                            html.Small("Par defaut : 20 derniers jours",
                                      className="text-muted d-block mt-1")
                        ], md=5),

                        # Airport filter
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-plane me-2"),
                                html.Strong("Filtrer par aeroport (station OACI)")
                            ], className="mb-2"),
                            dcc.Dropdown(
                                id='meteo-airport-filter',
                                placeholder='Tous les aeroports (global)',
                                clearable=True,
                                searchable=True,
                                style={'fontSize': '0.95rem'}
                            ),
                            html.Small("Ex : LFPG (Paris CDG), KJFK (New York), EGLL (Londres Heathrow)",
                                      className="text-muted d-block mt-1")
                        ], md=5),

                        # Refresh
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-sync-alt fa-2x text-muted mb-2"),
                                html.Br(),
                                html.Small("Actualisation auto 2 min", className="text-muted")
                            ], className="text-center mt-3")
                        ], md=2),
                    ])
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # KPI Cards
    dbc.Row(id='meteo-kpi-cards', className="mb-4"),

    # Section 1: Categories de vol + Conditions meteo
    dbc.Row([
        dbc.Col([
            html.H4([
                html.I(className="fas fa-plane-departure me-2", style={'color': '#3498db'}),
                "Conditions de Vol"
            ], className="mb-3 mt-2")
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Categories de Vol (METAR)", className="mb-0 d-inline"),
                    dbc.Badge("VFR / MVFR / IFR / LIFR", color="info", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Graph(id='meteo-flight-categories', config={'displayModeBar': False}),
                    html.Hr(),
                    html.Div(id='meteo-flight-cat-legend', className="mt-2")
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Phenomenes Meteorologiques", className="mb-0 d-inline"),
                    dbc.Badge("Codes METAR wx_string", color="info", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Graph(id='meteo-weather-conditions', config={'displayModeBar': False}),
                    html.Hr(),
                    html.Div(id='meteo-wx-legend', className="mt-2")
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),

    # Section 2: Analyse par Aeroport
    dbc.Row([
        dbc.Col([
            html.H4([
                html.I(className="fas fa-map-marker-alt me-2", style={'color': '#e67e22'}),
                "Analyse par Aeroport"
            ], className="mb-3 mt-4")
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Top Aeroports - Observations METAR", className="mb-0 d-inline"),
                    dbc.Badge("Temp / Vent / Visibilite", color="warning", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Graph(id='meteo-top-airports', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=12),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Detail Aeroports - Tableau Comparatif", className="mb-0")),
                dbc.CardBody(id='meteo-airports-table')
            ], className="shadow-sm")
        ], width=12),
    ], className="mb-4"),

    # Section 3: Visibilite
    dbc.Row([
        dbc.Col([
            html.H4([
                html.I(className="fas fa-eye me-2", style={'color': '#1abc9c'}),
                "Analyse Visibilite"
            ], className="mb-3 mt-4"),
            html.P("La visibilite est mesuree en miles terrestres (statute miles). "
                   "Une visibilite < 3 mi impose le vol aux instruments (IFR).",
                   className="text-muted mb-3", style={'fontSize': '0.9rem'})
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

    # Section 4: Temperature & Vent
    dbc.Row([
        dbc.Col([
            html.H4([
                html.I(className="fas fa-temperature-high me-2", style={'color': '#e74c3c'}),
                "Temperature & Vent"
            ], className="mb-3 mt-4"),
            html.P([
                "Le ", html.Strong("point de rosee"),
                " indique la temperature a laquelle la vapeur d'eau se condense. "
                "Quand la temperature se rapproche du point de rosee, le risque de ",
                html.Strong("brouillard"), " ou de ", html.Strong("givrage"), " augmente."
            ], className="text-muted mb-3", style={'fontSize': '0.9rem'})
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Temperature et Point de Rosee", className="mb-0 d-inline"),
                    dbc.Badge("Celsius", color="danger", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Graph(id='meteo-temperature-dewpoint', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Distribution Vitesse du Vent", className="mb-0 d-inline"),
                    dbc.Badge("kt (noeuds)", color="secondary", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Graph(id='meteo-wind-speed', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=6),
    ], className="mb-4"),

    # Section 5: Volume d'observations
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("Volume d'Observations METAR par Jour", className="mb-0 d-inline"),
                    dbc.Badge("Couverture temporelle", color="success", className="ms-2")
                ]),
                dbc.CardBody([
                    dcc.Graph(id='meteo-observations-timeline', config={'displayModeBar': False})
                ])
            ], className="shadow-sm")
        ], width=12),
    ], className="mb-4"),

    # Section 6: Glossaire
    dbc.Row([
        dbc.Col([
            html.H4([
                html.I(className="fas fa-book-open me-2", style={'color': '#9b59b6'}),
                "Reference & Glossaire"
            ], className="mb-3 mt-4")
        ])
    ]),
    build_glossary_section(),
])


# =============================================================================
# CALLBACKS
# =============================================================================

# --- Callback: Populate airport dropdown ---
@callback(
    Output('meteo-airport-filter', 'options'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_airport_dropdown(n, date_start, date_end):
    params = build_date_params(date_start, date_end)
    sep = '&' if params else '?'
    data = fetch_api(f"/meteo/top-airports{params}{sep}limit=200")
    if not data:
        return []
    options = []
    for d in data:
        icao = d['airport']
        label = get_airport_label(icao)
        options.append({
            'label': f"{label}  -  {d['observations']:,} obs, {d['avg_temp']}°C moy",
            'value': icao
        })
    return options


# --- Callback: KPI Cards ---
@callback(
    Output('meteo-kpi-cards', 'children'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_kpis(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    stats = fetch_api(f"/meteo/stats{params}")
    if not stats:
        return []

    return [
        dbc.Col(create_metric_card(
            "Observations METAR", f"{stats['total_metar']:,}",
            f"{stats['airports_metar']} stations OACI",
            "fa-cloud", "#3498db"
        ), width=3),
        dbc.Col(create_metric_card(
            "Previsions TAF", f"{stats['total_taf']:,}",
            f"{stats['airports_taf']} stations OACI",
            "fa-cloud-sun", "#9b59b6"
        ), width=3),
        dbc.Col(create_metric_card(
            "Conditions Ciel", f"{stats['total_sky_conditions']:,}",
            "Couches nuageuses enregistrees",
            "fa-cloud-meatball", "#1abc9c"
        ), width=3),
        dbc.Col(create_metric_card(
            "Periode METAR",
            f"{stats['date_min_metar']}",
            f"au {stats['date_max_metar']}",
            "fa-calendar", "#e67e22"
        ), width=3),
    ]


# --- Callback: Flight Categories Pie ---
@callback(
    Output('meteo-flight-categories', 'figure'),
    Output('meteo-flight-cat-legend', 'children'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_flight_categories(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/flight-categories{params}")
    if not data:
        return go.Figure(), []

    colors_map = {k: v['color'] for k, v in FLIGHT_CATEGORY_INFO.items()}

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=[d['condition'] for d in data],
        values=[d['count'] for d in data],
        marker=dict(colors=[colors_map.get(d['condition'], '#95a5a6') for d in data]),
        textinfo='label+percent',
        textposition='inside',
        hovertemplate=(
            '<b>%{label}</b><br>'
            'Observations: %{value:,}<br>'
            'Pourcentage: %{percent}<br>'
            '<extra></extra>'
        )
    ))
    fig.update_layout(
        title="Distribution des Categories de Vol",
        template='plotly_white',
        height=400,
        showlegend=True,
        margin=dict(t=40, b=10)
    )

    # Legend with explanations
    legend_items = []
    for d in data:
        cat = d['condition']
        info = FLIGHT_CATEGORY_INFO.get(cat, FLIGHT_CATEGORY_INFO['UNKNOWN'])
        legend_items.append(
            html.Div([
                html.Span("● ", style={'color': info['color'], 'fontSize': '1.2rem', 'fontWeight': 'bold'}),
                html.Strong(f"{cat} : "),
                html.Span(f"{info['criteria']} ", style={'fontSize': '0.82rem'}),
                html.Span(f"({d['count']:,} obs, {d['percentage']}%)",
                         style={'fontSize': '0.8rem', 'color': '#888'}),
            ], className="mb-1")
        )

    return fig, legend_items


# --- Callback: Weather Conditions ---
@callback(
    Output('meteo-weather-conditions', 'figure'),
    Output('meteo-wx-legend', 'children'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_weather_conditions(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/weather-conditions{params}")
    if not data:
        return go.Figure(), []

    top_data = data[:15]

    # Decode wx abbreviations for display
    labels = []
    decoded = []
    for d in top_data:
        raw = d['condition'] if d['condition'] else 'CLEAR'
        labels.append(raw)
        decoded.append(decode_wx_string(raw))

    # Color by severity
    def wx_color(wx):
        if not wx or wx == 'CLEAR':
            return '#27ae60'
        if any(c in wx for c in ['TS', '+', 'FZ']):
            return '#e74c3c'
        if any(c in wx for c in ['SN', 'GR', 'PL', 'IC']):
            return '#8e44ad'
        if any(c in wx for c in ['RA', 'DZ', 'SH']):
            return '#3498db'
        if any(c in wx for c in ['FG', 'BR', 'HZ', 'FU']):
            return '#f39c12'
        return '#95a5a6'

    colors = [wx_color(d['condition']) for d in top_data]

    # Labels avec decodage sur l'axe Y pour lisibilite
    y_labels = [f"{labels[i]}  ({decoded[i][:30]})" if decoded[i] != labels[i] else labels[i]
                for i in range(len(labels))]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=y_labels,
        x=[d['count'] for d in top_data],
        orientation='h',
        marker_color=colors,
        text=[f"{d['percentage']:.1f}%" for d in top_data],
        textposition='auto',
        hovertemplate=[
            f'<b>Code : {labels[i]}</b><br>'
            f'Signification : {decoded[i]}<br>'
            f'Observations : {top_data[i]["count"]:,}<br>'
            f'Pourcentage : {top_data[i]["percentage"]:.1f}%'
            f'<extra></extra>'
            for i in range(len(top_data))
        ]
    ))
    fig.update_layout(
        title="Top 15 Phenomenes Meteo (codes METAR)",
        xaxis_title="Nombre d'observations",
        template='plotly_white',
        height=500,
        margin=dict(l=250)
    )

    # Decoded legend
    legend_items = [
        html.Small("Decodage des codes affiches :", className="text-muted d-block mb-1 fw-bold")
    ]
    for i, d in enumerate(top_data[:8]):
        raw = d['condition'] if d['condition'] else 'CLEAR'
        desc = decode_wx_string(raw)
        legend_items.append(
            html.Div([
                html.Code(raw, style={'fontSize': '0.8rem', 'marginRight': '6px'}),
                html.Span(f"= {desc}", style={'fontSize': '0.8rem', 'color': '#555'})
            ])
        )
    if len(top_data) > 8:
        legend_items.append(html.Small("... voir glossaire pour tous les codes", className="text-muted"))

    return fig, legend_items


# --- Callback: Top Airports Chart ---
@callback(
    Output('meteo-top-airports', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_top_airports(n, date_start, date_end):
    params = build_date_params(date_start, date_end)
    sep = '&' if params else '?'
    data = fetch_api(f"/meteo/top-airports{params}{sep}limit=20")
    if not data:
        return go.Figure()

    # Build labels with city names
    airport_labels = [get_airport_label(d['airport']) for d in data]
    airport_hovers = []
    for d in data:
        icao = d['airport']
        info = AIRPORT_NAMES.get(icao, {})
        full_name = info.get('name', icao)
        airport_hovers.append(f"{full_name} ({icao})")

    fig = go.Figure()

    # Bar: nombre d'observations
    fig.add_trace(go.Bar(
        x=airport_labels,
        y=[d['observations'] for d in data],
        name='Observations',
        marker_color='rgba(52, 152, 219, 0.7)',
        yaxis='y',
        hovertemplate=['<b>' + airport_hovers[i] + '</b><br>Observations: ' + f'{data[i]["observations"]:,}' + '<extra></extra>' for i in range(len(data))]
    ))

    # Line: temperature moyenne
    fig.add_trace(go.Scatter(
        x=airport_labels,
        y=[d['avg_temp'] for d in data],
        name='Temp moy (°C)',
        mode='lines+markers',
        marker=dict(size=8, color='#e74c3c', symbol='circle'),
        line=dict(width=2, color='#e74c3c'),
        yaxis='y2',
        hovertemplate=['<b>' + airport_hovers[i] + '</b><br>Temp moy: ' + f'{data[i]["avg_temp"]:.1f}°C' + '<extra></extra>' for i in range(len(data))]
    ))

    # Line: vitesse vent moyenne
    fig.add_trace(go.Scatter(
        x=airport_labels,
        y=[d['avg_wind_speed'] for d in data],
        name='Vent moy (kt)',
        mode='lines+markers',
        marker=dict(size=8, color='#9b59b6', symbol='diamond'),
        line=dict(width=2, color='#9b59b6', dash='dot'),
        yaxis='y2',
        hovertemplate=['<b>' + airport_hovers[i] + '</b><br>Vent moy: ' + f'{data[i]["avg_wind_speed"]:.1f} kt ({data[i]["avg_wind_speed"]*1.852:.0f} km/h)' + '<extra></extra>' for i in range(len(data))]
    ))

    # Line: visibilite moyenne
    fig.add_trace(go.Scatter(
        x=airport_labels,
        y=[d['avg_visibility'] for d in data],
        name='Visibilite moy (mi)',
        mode='lines+markers',
        marker=dict(size=8, color='#1abc9c', symbol='square'),
        line=dict(width=2, color='#1abc9c', dash='dash'),
        yaxis='y2',
        hovertemplate=['<b>' + airport_hovers[i] + '</b><br>Visibilite moy: ' + f'{data[i]["avg_visibility"]:.1f} mi ({data[i]["avg_visibility"]*1.609:.1f} km)' + '<extra></extra>' for i in range(len(data))]
    ))

    fig.update_layout(
        title="Top 20 Aeroports METAR : Observations, Temperature, Vent et Visibilite",
        xaxis_title="Aeroport",
        yaxis=dict(title="Nombre d'observations", side='left'),
        yaxis2=dict(title="Valeurs (°C / kt / mi)", side='right', overlaying='y'),
        template='plotly_white',
        height=480,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hovermode='x unified',
        margin=dict(b=130),
        xaxis=dict(tickangle=-35, tickfont=dict(size=10))
    )

    return fig


# --- Callback: Airport detail table ---
@callback(
    Output('meteo-airports-table', 'children'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    prevent_initial_call=False
)
def update_airports_table(n, date_start, date_end):
    params = build_date_params(date_start, date_end)
    sep = '&' if params else '?'
    data = fetch_api(f"/meteo/top-airports{params}{sep}limit=15")
    if not data:
        return html.P("Aucune donnee disponible", className="text-muted text-center")

    # Color coding for wind
    def wind_badge(speed):
        if speed is None:
            return dbc.Badge("N/A", color="secondary")
        if speed < 5:
            return dbc.Badge(f"{speed:.1f} kt", color="success")
        elif speed < 15:
            return dbc.Badge(f"{speed:.1f} kt", color="warning")
        else:
            return dbc.Badge(f"{speed:.1f} kt", color="danger")

    # Color coding for visibility
    def vis_badge(vis):
        if vis is None:
            return dbc.Badge("N/A", color="secondary")
        if vis >= 5:
            return dbc.Badge(f"{vis:.1f} mi", color="success")
        elif vis >= 3:
            return dbc.Badge(f"{vis:.1f} mi", color="warning")
        else:
            return dbc.Badge(f"{vis:.1f} mi", color="danger")

    # Color for temp
    def temp_badge(temp):
        if temp is None:
            return dbc.Badge("N/A", color="secondary")
        if temp < 0:
            return dbc.Badge(f"{temp:.1f}C", color="primary")
        elif temp < 15:
            return dbc.Badge(f"{temp:.1f}C", color="info")
        elif temp < 30:
            return dbc.Badge(f"{temp:.1f}C", color="warning")
        else:
            return dbc.Badge(f"{temp:.1f}C", color="danger")

    rows = []
    for i, d in enumerate(data):
        icao = d['airport']
        info = AIRPORT_NAMES.get(icao, {})
        full_name = info.get('name', '')
        iata = info.get('iata', '')
        iata_str = f" ({iata})" if iata else ''
        rows.append(html.Tr([
            html.Td(html.Strong(str(i + 1))),
            html.Td([
                html.Div([
                    html.I(className="fas fa-plane-departure me-1", style={'color': '#3498db'}),
                    html.Strong(f"{icao}{iata_str}")
                ]),
                html.Small(full_name, className="text-muted") if full_name else None
            ]),
            html.Td(f"{d['observations']:,}"),
            html.Td(temp_badge(d.get('avg_temp'))),
            html.Td(wind_badge(d.get('avg_wind_speed'))),
            html.Td(vis_badge(d.get('avg_visibility'))),
        ]))

    return [
        dbc.Table([
            html.Thead(html.Tr([
                html.Th("#", style={'width': '40px'}),
                html.Th([html.I(className="fas fa-map-pin me-1"), "Aeroport"]),
                html.Th([html.I(className="fas fa-chart-bar me-1"), "Observations"]),
                html.Th([html.I(className="fas fa-thermometer-half me-1"), "Temp Moy"]),
                html.Th([html.I(className="fas fa-wind me-1"), "Vent Moy"]),
                html.Th([html.I(className="fas fa-eye me-1"), "Visibilite Moy"]),
            ]), className="table-dark"),
            html.Tbody(rows)
        ], striped=True, bordered=True, hover=True, responsive=True, size='sm'),
        html.Div([
            html.Small([
                html.Span("Legende : ", style={'fontWeight': 'bold'}),
                html.Span("● ", style={'color': '#28a745'}), "Bon  ",
                html.Span("● ", style={'color': '#ffc107'}), "Modere  ",
                html.Span("● ", style={'color': '#dc3545'}), "Critique"
            ], className="text-muted")
        ], className="text-end")
    ]


# --- Callback: Visibility Distribution ---
@callback(
    Output('meteo-visibility-distribution', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_visibility_distribution(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/visibility-distribution{params}")
    if not data:
        return go.Figure()

    # Color by IFR impact
    range_colors = {
        '< 1 mi': '#e74c3c',     # LIFR
        '1-3 mi': '#f39c12',     # IFR
        '3-5 mi': '#f1c40f',     # MVFR
        '5-10 mi': '#3498db',    # VFR marginal
        '>= 10 mi': '#27ae60',   # VFR
    }

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['visibility_range'] for d in data],
        y=[d['count'] for d in data],
        marker_color=[range_colors.get(d['visibility_range'], '#3498db') for d in data],
        text=[f"{d['count']:,}" for d in data],
        textposition='outside',
        hovertemplate=[
            f'<b>{d["visibility_range"]}</b><br>'
            f'Observations: {d["count"]:,}<br>'
            f'{"LIFR - Tres dangereux" if "< 1" in d["visibility_range"] else ""}'
            f'{"IFR - Vol aux instruments" if "1-3" in d["visibility_range"] else ""}'
            f'{"MVFR - VFR marginal" if "3-5" in d["visibility_range"] else ""}'
            f'{"VFR - Bonnes conditions" if "5-10" in d["visibility_range"] or ">= 10" in d["visibility_range"] else ""}'
            f'<extra></extra>'
            for d in data
        ]
    ))
    fig.update_layout(
        title="Repartition par Plage de Visibilite",
        xaxis_title="Visibilite (statute miles, 1 mi = 1.6 km)",
        yaxis_title="Nombre d'observations",
        template='plotly_white',
        height=350,
        annotations=[
            dict(x=0, y=1.08, xref='paper', yref='paper',
                 text="<span style='color:#e74c3c'>■</span> LIFR  "
                      "<span style='color:#f39c12'>■</span> IFR  "
                      "<span style='color:#f1c40f'>■</span> MVFR  "
                      "<span style='color:#3498db'>■</span><span style='color:#27ae60'>■</span> VFR",
                 showarrow=False, font=dict(size=11))
        ]
    )
    return fig


# --- Callback: Visibility Timeline ---
@callback(
    Output('meteo-visibility-timeline', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_visibility_timeline(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/visibility-timeline{params}")
    if not data:
        return go.Figure()

    fig = go.Figure()

    # Zones IFR/VFR en arriere-plan
    fig.add_hrect(y0=0, y1=1, fillcolor="rgba(231,76,60,0.1)", line_width=0,
                  annotation_text="LIFR", annotation_position="top left",
                  annotation_font_size=10, annotation_font_color="#e74c3c")
    fig.add_hrect(y0=1, y1=3, fillcolor="rgba(243,156,18,0.1)", line_width=0,
                  annotation_text="IFR", annotation_position="top left",
                  annotation_font_size=10, annotation_font_color="#f39c12")
    fig.add_hrect(y0=3, y1=5, fillcolor="rgba(241,196,15,0.1)", line_width=0,
                  annotation_text="MVFR", annotation_position="top left",
                  annotation_font_size=10, annotation_font_color="#f1c40f")

    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['avg_visibility'] for d in data],
        mode='lines+markers',
        marker=dict(size=8, color='#3498db'),
        line=dict(width=2, color='#3498db'),
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.15)',
        hovertemplate='<b>%{x}</b><br>Visibilite moy: %{y:.2f} mi<extra></extra>'
    ))

    fig.update_layout(
        title="Evolution Visibilite Moyenne Journaliere (avec zones VFR/IFR)",
        xaxis_title="Date",
        yaxis_title="Visibilite moyenne (statute miles)",
        template='plotly_white',
        height=350
    )
    return fig


# --- Callback: Temperature & Dewpoint ---
@callback(
    Output('meteo-temperature-dewpoint', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_temperature_dewpoint(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/temperature-stats{params}")
    if not data:
        return go.Figure()

    fig = go.Figure()

    # Calculer min pour la zone givrage
    all_temps = [d['avg_temp'] for d in data if d.get('avg_temp') is not None]
    all_dew = [d['avg_dewpoint'] for d in data if d.get('avg_dewpoint') is not None]
    y_min = min(min(all_temps, default=0), min(all_dew, default=0)) - 3

    # Zone givrage potentiel (temp <= 0) - limiter le rectangle aux donnees
    if y_min < 0:
        fig.add_hrect(y0=y_min, y1=0, fillcolor="rgba(52,152,219,0.08)", line_width=0,
                      annotation_text="Zone givrage (< 0°C)", annotation_position="bottom left",
                      annotation_font_size=10, annotation_font_color="#3498db")

    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['avg_temp'] for d in data],
        mode='lines+markers',
        name='Temperature (C)',
        marker=dict(size=6, color='#e74c3c'),
        line=dict(width=2),
        hovertemplate='%{x}<br>Temp moy: %{y:.1f}C<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d['avg_dewpoint'] for d in data],
        mode='lines+markers',
        name='Point de rosee (C)',
        marker=dict(size=6, color='#3498db'),
        line=dict(width=2),
        hovertemplate='%{x}<br>Point de rosee: %{y:.1f}C<extra></extra>'
    ))

    # Spread line (difference temp - dewpoint) - risque brouillard
    valid_data = [d for d in data if d.get('avg_temp') is not None and d.get('avg_dewpoint') is not None]
    if valid_data:
        spread = [d['avg_temp'] - d['avg_dewpoint'] for d in valid_data]
        fig.add_trace(go.Scatter(
            x=[d['date'] for d in valid_data],
            y=spread,
            mode='lines',
            name='Ecart T-Td (brouillard si < 3C)',
            line=dict(width=1, color='#95a5a6', dash='dot'),
            hovertemplate='%{x}<br>Ecart T-Td: %{y:.1f}C<extra></extra>'
        ))

    fig.update_layout(
        title="Evolution Temperature, Point de Rosee et Ecart T-Td",
        xaxis_title="Date",
        yaxis_title="Temperature (\u00b0C)",
        template='plotly_white',
        height=380,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        yaxis=dict(range=[y_min, max(all_temps, default=20) + 3])
    )
    return fig


# --- Callback: Wind Speed ---
@callback(
    Output('meteo-wind-speed', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_wind_speed(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/wind-stats{params}")
    if not data:
        return go.Figure()

    # Wind color: calm -> severe
    wind_colors = {
        '< 5 kt': '#27ae60',
        '5-10 kt': '#2ecc71',
        '10-15 kt': '#f39c12',
        '15-20 kt': '#e67e22',
        '20-25 kt': '#e74c3c',
        '>= 25 kt': '#c0392b',
    }

    wind_desc = {
        '< 5 kt': 'Calme (< 9 km/h)',
        '5-10 kt': 'Legere brise (9-18 km/h)',
        '10-15 kt': 'Brise moderee (18-28 km/h)',
        '15-20 kt': 'Brise forte (28-37 km/h)',
        '20-25 kt': 'Vent fort (37-46 km/h)',
        '>= 25 kt': 'Vent violent (> 46 km/h)',
    }

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d['wind_range'] for d in data],
        y=[d['count'] for d in data],
        marker_color=[wind_colors.get(d['wind_range'], '#9b59b6') for d in data],
        text=[f"{d['count']:,}" for d in data],
        textposition='outside',
        hovertemplate=[
            f'<b>{d["wind_range"]}</b><br>'
            f'{wind_desc.get(d["wind_range"], "")}<br>'
            f'Observations: {d["count"]:,}'
            f'<extra></extra>'
            for d in data
        ]
    ))
    fig.update_layout(
        title="Distribution Vitesse du Vent",
        xaxis_title="Vitesse (kt = noeuds, 1 kt = 1.852 km/h)",
        yaxis_title="Nombre d'observations",
        template='plotly_white',
        height=350
    )
    return fig


# --- Callback: Observations Timeline ---
@callback(
    Output('meteo-observations-timeline', 'figure'),
    Input('interval-meteo', 'n_intervals'),
    Input('meteo-date-start', 'date'),
    Input('meteo-date-end', 'date'),
    Input('meteo-airport-filter', 'value'),
    prevent_initial_call=False
)
def update_observations_timeline(n, date_start, date_end, airport):
    params = build_date_params(date_start, date_end, airport)
    data = fetch_api(f"/meteo/temperature-stats{params}")
    if not data:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d['date'] for d in data],
        y=[d.get('observations', 0) for d in data],
        mode='lines+markers',
        name='Observations / jour',
        fill='tozeroy',
        fillcolor='rgba(26, 188, 156, 0.2)',
        marker=dict(size=6, color='#1abc9c'),
        line=dict(width=2, color='#1abc9c'),
        hovertemplate='<b>%{x}</b><br>Observations: %{y:,}<extra></extra>'
    ))

    fig.update_layout(
        title="Volume d'Observations METAR par Jour (couverture de la collecte)",
        xaxis_title="Date",
        yaxis_title="Nombre d'observations",
        template='plotly_white',
        height=300,
        margin=dict(t=40, b=40)
    )
    return fig
