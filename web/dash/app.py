"""
Dashboard DST Airlines
Pages: Vols, Meteo
"""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    use_pages=True,
    suppress_callback_exceptions=True
)

app.title = "DST Airlines - Analytics"

navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-plane-departure me-2", style={'fontSize': '1.5rem'}),
                    dbc.NavbarBrand("DST Airlines", className="ms-2", style={'fontSize': '1.5rem', 'fontWeight': 'bold'})
                ], className="d-flex align-items-center")
            ], width="auto"),
        ], align="center", className="g-0"),
        dbc.Row([
            dbc.Col([
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Vols", href="/", active="exact")),
                    dbc.NavItem(dbc.NavLink("Meteo", href="/meteo", active="exact")),
                ], navbar=True)
            ])
        ], className="g-0 ms-auto flex-nowrap mt-3 mt-md-0", align="center"),
    ], fluid=True),
    color="dark",
    dark=True,
    className="mb-4"
)

app.layout = html.Div([
    navbar,
    dbc.Container(dash.page_container, fluid=True)
], style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

if __name__ == '__main__':
    print("\n" + "="*70)
    print("DASHBOARD DST AIRLINES DEMARRE")
    print("="*70)
    print("URL: http://0.0.0.0:8050/")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=8050)
