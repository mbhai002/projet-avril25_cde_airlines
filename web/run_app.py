#!/usr/bin/env python3
"""
Script de demarrage pour DST Airlines
Lance l'API FastAPI et le Dashboard Dash simultanement
"""

import subprocess
import time
import sys
import os

def main():
    print("\n" + "="*70)
    print("DEMARRAGE DST AIRLINES")
    print("="*70)
    
    web_dir = os.path.dirname(__file__)
    
    print("\nDemarrage de l'API FastAPI...")
    api_process = subprocess.Popen(
        [sys.executable, os.path.join(web_dir, "FastAPI", "main.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(3)
    print("   [OK] API demarree sur http://127.0.0.1:8000")
    print("   [OK] Documentation: http://127.0.0.1:8000/docs")
    
    print("\nDemarrage du Dashboard Multi-Pages...")
    dashboard_process = subprocess.Popen(
        [sys.executable, os.path.join(web_dir, "app.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(2)
    print("   [OK] Dashboard demarre sur http://127.0.0.1:8050")
    
    print("\n" + "="*70)
    print("TOUS LES SERVICES SONT DEMARRES")
    print("="*70)
    print("\nDashboard: http://127.0.0.1:8050/")
    print("  - Page Vols: http://127.0.0.1:8050/")
    print("  - Page Meteo: http://127.0.0.1:8050/meteo")
    print("  - Page Analyses: http://127.0.0.1:8050/analyses")
    print("\nAPI Documentation: http://127.0.0.1:8000/docs")
    print("\nAppuyez sur CTRL+C pour arreter tous les services\n")
    
    try:
        api_process.wait()
        dashboard_process.wait()
    except KeyboardInterrupt:
        print("\n\nArret des services...")
        api_process.terminate()
        dashboard_process.terminate()
        api_process.wait()
        dashboard_process.wait()
        print("Tous les services arretes\n")

if __name__ == "__main__":
    main()