"""
Page Performance et Limites du Modèle ML
"""

import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import os
import requests

dash.register_page(__name__, path='/modele-ml', name='Modèle ML')

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000')

# Chemins des données (statiques pour cette présentation)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # /app dans le container
METRICS_PATH = os.path.join(BASE_DIR, 'machine_learning', 'model_output', 'model_metrics_20251107_094353.json')
FEAT_IMP_PATH = os.path.join(BASE_DIR, 'machine_learning', 'model_output', 'feature_importance_20251107_094353.csv')

def fetch_reliability():
    try:
        response = requests.get(f"{API_URL}/ml/reliability")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erreur API reliability: {e}")
        return None

def load_data():
    try:
        with open(METRICS_PATH, 'r') as f:
            metrics = json.load(f)
        feat_imp = pd.read_csv(FEAT_IMP_PATH).head(15)
        return metrics, feat_imp
    except Exception as e:
        print(f"Erreur chargement metrics: {e}")
        return None, None

def create_metric_card(title, value, description, color="primary"):
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="card-title text-muted"),
            html.H2(f"{value:.3f}" if isinstance(value, float) else value, className=f"text-{color}"),
            html.P(description, className="small text-muted mb-0")
        ])
    ], className="shadow-sm h-100")

def layout():
    metrics, feat_imp = load_data()
    reliability_data = fetch_reliability()
    risk_mapping = {'low': 'Faible', 'medium': 'Modéré', 'high': 'Élevé'}
    
    if not metrics or feat_imp is None:
        return html.Div([dbc.Alert("Données du modèle non disponibles ou mal formées.", color="danger")], className="p-4")

    # Graphique Importance des Features
    fig_imp = px.bar(
        feat_imp, 
        x='importance', 
        y='feature',
        orientation='h',
        title="Impact des variables sur la prédiction",
        labels={'importance': 'Importance', 'feature': 'Variable'},
        height=450
    )
    fig_imp.update_layout(
        yaxis={'categoryorder':'total ascending'}, 
        margin=dict(l=150, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Matrice de confusion
    cm = metrics.get('confusion_matrix', [[0,0],[0,0]])
    total_samples = sum(sum(cm, []))
    
    def get_pct(val):
        return f"{(val/total_samples)*100:.1f}%" if total_samples > 0 else "0%"

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H2([html.I(className="fas fa-brain me-3"), "Performance & Limites du Modèle ML"], className="mb-4")
            ])
        ]),

        # KPIs
        dbc.Row([
            dbc.Col([
                create_metric_card("ROC AUC", metrics['roc_auc'], "Capacité de discrimination (Test)", "primary"),
                dbc.Tooltip("Mesure la probabilité qu'un retard tiré au hasard soit mieux classé qu'un vol à l'heure au hasard. 0.5 = Aléatoire / 1.0 = Parfait.", target="_roc_auc", placement="bottom"),
            ], width=12, md=3, id="_roc_auc"),
            dbc.Col([
                create_metric_card("F1-Score", metrics['f1_score'], "Équilibre Précision/Rappel", "info"),
                dbc.Tooltip("Moyenne harmonique de la Précision et du Rappel. Crucial pour les données déséquilibrées.", target="_f1_score", placement="bottom"),
            ], width=12, md=3, id="_f1_score"),
            dbc.Col([
                create_metric_card("Précision", metrics['precision'], "Fiabilité des alertes retard", "success"),
                dbc.Tooltip("Parmi tous les retards prédits, combien étaient réellement des retards ? Évite les fausses alertes.", target="_precision", placement="bottom"),
            ], width=12, md=3, id="_precision"),
            dbc.Col([
                create_metric_card("Rappel (Recall)", metrics['recall'], "Taux de détection des retards", "warning"),
                dbc.Tooltip("Parmi tous les retards réels, combien le modèle a-t-il réussi à en détecter ? Évite les retards manqués.", target="_recall", placement="bottom"),
            ], width=12, md=3, id="_recall"),
        ], className="g-4 mb-4"),

        dbc.Row([
            # Importance des variables
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.I(className="fas fa-chart-bar me-2"), "Importance des Variables"]),
                    dbc.CardBody([
                        dcc.Graph(figure=fig_imp)
                    ])
                ], className="shadow-sm h-100")
            ], width=12, lg=7),

            # Matrice de Confusion Simpifiée
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.I(className="fas fa-th me-2"), "Matrice de Confusion"]),
                    dbc.CardBody([
                        html.Table([
                            html.Thead([
                                html.Tr([html.Th(""), html.Th("Prédit Normal"), html.Th("Prédit Retard")])
                            ]),
                            html.Tbody([
                                html.Tr([html.Th("Réel Normal"), html.Td(f"{cm[0][0]}", className="text-center p-3 bg-light"), html.Td(f"{cm[0][1]}", className="text-center p-3")]),
                                html.Tr([html.Th("Réel Retard"), html.Td(f"{cm[1][0]}", className="text-center p-3"), html.Td(f"{cm[1][1]}", className="text-center p-3 bg-info text-white")])
                            ])
                        ], className="table table-bordered mt-4"),
                        html.Div([
                            html.P([html.B(f"Vrais Négatifs - {get_pct(cm[0][0])}: "), "Le modèle a correctement prédit l'absence de retard."], className="small mb-1"),
                            html.P([html.B(f"Faux Positifs - {get_pct(cm[0][1])}: "), "Alertes inutiles (le vol était à l'heure alors qu'on prédisait un retard)."], className="small mb-1"),
                            html.P([html.B(f"Faux Négatifs - {get_pct(cm[1][0])}: "), "Retards non détectés (le cas le plus problématique pour l'exploitation)."], className="small mb-1"),
                            html.P([html.B(f"Vrais Positifs - {get_pct(cm[1][1])}: "), "Le modèle a anticipé avec succès le retard du vol."], className="small mb-0")
                        ], className="mt-3 p-2 bg-light border rounded")
                    ])
                ], className="shadow-sm h-100")
            ], width=12, lg=5),
        ], className="g-4 mb-4"),

        # Tableau de Fiabilité (Données Réelles API)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.I(className="fas fa-tasks me-2"), "Analyse de Fiabilité (Toute la base PostgreSQL)"]),
                    dbc.CardBody([
                        html.P("Ce tableau croise les niveaux de risque prédits avec les retards réellement constatés dans la base de données.", className="small text-muted"),
                        html.Table([
                            html.Thead([
                                html.Tr([
                                    html.Th("Niveau de Risque"), 
                                    html.Th("Total Vols", className="text-center"), 
                                    html.Th("Vrais Retards", className="text-center"), 
                                    html.Th("Vols à l'heure", className="text-center"),
                                    html.Th("Taux de retard réel", className="text-center")
                                ])
                            ]),
                            html.Tbody([
                                html.Tr([
                                    html.Td(risk_mapping.get(r['risk_level'], r['risk_level']), className="fw-bold"),
                                    html.Td(f"{r['total_vols']:,}", className="text-center"),
                                    html.Td(f"{r['vrais_retards']:,}", className="text-center text-danger"),
                                    html.Td(f"{r['vols_a_l_heure']:,}", className="text-center text-success"),
                                    html.Td(f"{r['taux_retard_reel']}%", className="text-center fw-bold bg-light")
                                ]) for r in (reliability_data or [])
                            ])
                        ], className="table table-hover table-sm") if reliability_data else dbc.Alert("Données de fiabilité API indisponibles", color="warning")
                    ])
                ], className="shadow-sm")
            ])
        ], className="mb-4"),

        # Limites et Overfitting
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([html.I(className="fas fa-exclamation-triangle me-2 text-danger"), "Analyse des Limites & Plafond de Performance"]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H5("Diagnostic : " + metrics['overfitting_analysis']['overfitting_status'], className="text-danger fw-bold"),
                                html.P([
                                    "Le modèle présente un ", html.B("surapprentissage (overfitting) significatif"), 
                                    " (Gap ROC AUC : ", 
                                    html.Span(f"{metrics['overfitting_analysis']['roc_auc_gap_percent']:.1f}%", className="badge bg-danger"),
                                    ")."
                                ]),
                                
                                html.H6([html.I(className="fas fa-info-circle me-2"), "Pourquoi est-il difficile de faire mieux ?"], className="mt-4"),
                                html.P([
                                    "Les retards d'avion sont un phénomène à ", html.B("fort bruit structurel"), ". Une grande partie des causes (contraintes ATC (air traffic control), logistique sol, incidents, propagation des retards) n'est pas observée dans le jeu de données actuel."
                                ]),
                                
                                dbc.Alert([
                                    "Un modèle ne peut pas apprendre ce qu'il n'a jamais vu. L'overfitting est ici le symptôme d'un manque d'information causale plutôt qu'un simple défaut technique."
                                ], color="info", className="small"),

                                html.H6("Facteurs limitants :"),
                                html.Ul([
                                    html.Li([html.B("Déséquilibre des classes : "), "Avec ~10% de retards, le modèle est naturellement poussé à prédire 'à l'heure' pour minimiser son erreur globale. Cela biaise l'apprentissage vers la majorité."]),
                                    html.Li("Effets chaotiques : propagation des retards d'un vol précédent non capturée."),
                                    html.Li("Variables cachées : grèves, pannes techniques, météo temps réel ultra-locale."),
                                    html.Li("Plafond naturel : Pour ce type de problème, un ROC-AUC entre 0.70 et 0.80 est souvent le maximum réaliste sans données d'exploitation internes.")
                                ], className="small")
                            ], lg=8),
                            dbc.Col([
                                html.Div([
                                    html.H6("Pistes d'amélioration :", className="text-muted text-uppercase small fw-bold"),
                                    html.Ul([
                                        html.Li("Régularisation plus forte (XGBoost alpha/lambda)"),
                                        html.Li("Ajout de proxys (trafic prévu, retards T-1)"),
                                        html.Li("Modèles spécialisés par route/compagnie")
                                    ], className="small")
                                ], className="p-3 bg-light border rounded")
                            ], lg=4)
                        ])
                    ])
                ], className="shadow-sm border-danger")
            ])
        ], className="mb-4")
    ], className="py-4")

def ff_create_annotated_heatmap(z, x, y):
    # Fallback si figure_factory n'est pas dispo
    return None # Non utilisé car j'ai fait un tableau HTML plus propre
