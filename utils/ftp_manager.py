import os
import json
from ftplib import FTP, FTP_TLS
from typing import Dict, List, Optional
from datetime import datetime
from config.simple_logger import get_logger


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
    
    def get_file_modified_time(self, filename: str) -> Optional[float]:
        """Récupère le timestamp de modification d'un fichier"""
        if not self.ftp:
            return None
        
        try:
            response = self.ftp.sendcmd(f'MDTM {filename}')
            # Format: 213 YYYYMMDDhhmmss
            if response.startswith('213 '):
                timestamp_str = response[4:].strip()
                from datetime import datetime
                dt = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                return dt.timestamp()
        except Exception as e:
            self.logger.debug(f"Impossible de récupérer MDTM pour {filename}: {e}")
        
        return None
    
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
    
    def cleanup_old_files(self, pattern: str = "raw_*.html", max_age_hours: int = 24) -> int:
        """
        Supprime les fichiers correspondant au pattern et plus vieux que max_age_hours
        
        Args:
            pattern: Pattern des fichiers à nettoyer (ex: raw_*.html)
            max_age_hours: Âge maximum en heures
            
        Returns:
            Nombre de fichiers supprimés
        """
        if not self.ftp:
            self.logger.error("Pas de connexion FTP active")
            return 0
        
        try:
            import fnmatch
            import time
            
            all_files = self.list_files()
            matching_files = [f for f in all_files if fnmatch.fnmatch(f, pattern)]
            
            if not matching_files:
                self.logger.info(f"Aucun fichier correspondant à '{pattern}'")
                return 0
            
            deleted_count = 0
            max_age_seconds = max_age_hours * 3600
            current_time = time.time()
            
            self.logger.info(f"Analyse de {len(matching_files)} fichiers (pattern: {pattern})...")
            
            for filename in matching_files:
                file_time = self.get_file_modified_time(filename)
                
                if file_time:
                    age_seconds = current_time - file_time
                    age_hours = age_seconds / 3600
                    
                    if age_seconds > max_age_seconds:
                        if self.delete_file(filename):
                            deleted_count += 1
                            self.logger.info(f"  └─ {filename} supprimé (âge: {age_hours:.1f}h)")
                    else:
                        self.logger.debug(f"  └─ {filename} conservé (âge: {age_hours:.1f}h)")
            
            if deleted_count > 0:
                self.logger.info(f"✓ Nettoyage terminé: {deleted_count} fichier(s) supprimé(s)")
            else:
                self.logger.info("✓ Nettoyage terminé: aucun fichier à supprimer")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage: {e}")
            return 0
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()





