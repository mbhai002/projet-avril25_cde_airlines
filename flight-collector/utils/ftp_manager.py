import os
import json
import requests
import urllib3
from ftplib import FTP, FTP_TLS
from typing import Dict, List, Optional
from datetime import datetime
from config.simple_logger import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FTPManager:
    
    def __init__(self, host: str, port: int = 21, username: str = "", 
                 password: str = "", use_tls: bool = False, 
                 remote_directory: str = "/"):
        self.logger = get_logger(__name__)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.remote_directory = remote_directory
        self.ftp = None
        
    def connect(self) -> bool:
        try:
            if self.use_tls:
                self.logger.info(f"Connexion FTPS à {self.host}:{self.port}")
                self.ftp = FTP_TLS()
            else:
                self.logger.info(f"Connexion FTP à {self.host}:{self.port}")
                self.ftp = FTP()
            
            self.ftp.connect(self.host, self.port, timeout=30)
            
            if self.username and self.password:
                self.ftp.login(self.username, self.password)
                self.logger.info(f"Authentification réussie pour {self.username}")
            else:
                self.ftp.login()
                self.logger.info("Connexion anonyme réussie")
            
            if self.use_tls:
                self.ftp.prot_p()
            
            if self.remote_directory != "/":
                self.ftp.cwd(self.remote_directory)
                self.logger.info(f"Répertoire changé vers {self.remote_directory}")
            
            self.logger.info(f"✓ Connexion FTP établie avec {self.host}")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de connexion FTP: {e}")
            self.ftp = None
            return False
    
    def disconnect(self):
        if self.ftp:
            try:
                self.ftp.quit()
                self.logger.info("Déconnexion FTP réussie")
            except Exception as e:
                self.logger.warning(f"Erreur lors de la déconnexion: {e}")
            finally:
                self.ftp = None
    
    def list_files(self) -> List[str]:
        if not self.ftp:
            self.logger.error("Pas de connexion FTP active")
            return []
        
        try:
            files = self.ftp.nlst()
            self.logger.info(f"Listage: {len(files)} fichiers trouvés")
            return files
        except Exception as e:
            self.logger.error(f"Échec du listage: {e}")
            return []
    
    def delete_file(self, filename: str) -> bool:
        """Supprime un fichier sur le serveur FTP"""
        if not self.ftp:
            self.logger.error("Pas de connexion FTP active")
            return False
        
        try:
            self.ftp.delete(filename)
            self.logger.info(f"✓ Fichier {filename} supprimé")
            return True
        except Exception as e:
            self.logger.error(f"Échec de la suppression de {filename}: {e}")
            return False
    
    def cleanup_old_files(self, pattern: str = "raw_*.html", max_age_hours: int = 24, 
                         list_php_url: Optional[str] = None) -> int:
        """
        Supprime les fichiers correspondant au pattern et plus vieux que max_age_hours
        
        Args:
            pattern: Pattern des fichiers à nettoyer (non utilisé si list_php_url fourni)
            max_age_hours: Âge maximum en heures
            list_php_url: URL de list.php pour récupération rapide
            
        Returns:
            Nombre de fichiers supprimés
        """
        if not self.ftp:
            self.logger.error("Pas de connexion FTP active")
            return 0
        
        if not list_php_url:
            self.logger.error("list_php_url requis pour le nettoyage")
            return 0
        
        self.logger.info(f"Récupération de la liste des fichiers via {list_php_url}...")
        
        try:
            response = requests.get(list_php_url, timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            
            files_list = data.get('files', [])
            self.logger.info(f"✓ {len(files_list)} fichiers trouvés via list.php")
            
            deleted_count = 0
            files_to_delete = []
            
            # Identifier les fichiers à supprimer
            for file_info in files_list:
                age_hours = file_info.get('age_hours', 0)
                filename = file_info.get('filename')
                
                if age_hours > max_age_hours and filename:
                    files_to_delete.append((filename, age_hours))
            
            # Suppression groupée
            if files_to_delete:
                self.logger.info(f"Suppression de {len(files_to_delete)} fichier(s) (> {max_age_hours}h)...")
                for filename, age_hours in files_to_delete:
                    if self.delete_file(filename):
                        deleted_count += 1
                        self.logger.debug(f"  └─ {filename} supprimé (âge: {age_hours:.1f}h)")
            
            if deleted_count > 0:
                self.logger.info(f"✓ Nettoyage terminé: {deleted_count} fichier(s) supprimé(s)")
            else:
                self.logger.info("✓ Nettoyage terminé: aucun fichier à supprimer")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Échec du nettoyage via list.php: {e}")
            return 0
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()





