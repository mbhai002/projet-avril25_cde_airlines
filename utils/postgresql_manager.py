#!/usr/bin/env python3
"""
Gestionnaire pour PostgreSQL - Insertion des données météo METAR et TAF
"""

import sys
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from decimal import Decimal
import re

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.simple_logger import get_logger, log_database_operation


class PostgreSQLManager:
    """
    Gestionnaire pour les opérations PostgreSQL
    """
    
    def __init__(self, db_uri: str):
        """
        Initialise le gestionnaire PostgreSQL
        
        Args:
            db_uri: URI de connexion à la base de données
        """
        self.db_uri = db_uri
        self.logger = get_logger(__name__)
        self.connection = None
        
    def connect(self) -> bool:
        """
        Établit la connexion à PostgreSQL
        
        Returns:
            bool: True si connexion réussie, False sinon
        """
        try:
            self.connection = psycopg2.connect(self.db_uri)
            self.connection.autocommit = False
            self.logger.info(f"Connexion PostgreSQL établie")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur de connexion PostgreSQL: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion PostgreSQL"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Connexion PostgreSQL fermée")
    
    def test_connection(self) -> bool:
        """
        Test la connexion PostgreSQL
        
        Returns:
            bool: True si connexion fonctionne, False sinon
        """
        if not self.connection:
            return self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"Test de connexion échoué: {e}")
            return False
    
    def _format_timestamp(self, timestamp_str: str) -> Optional[str]:
        """
        Formate un timestamp pour PostgreSQL
        
        Args:
            timestamp_str: Timestamp au format ISO ou autre
            
        Returns:
            str: Timestamp formaté pour PostgreSQL ou None si erreur
        """
        if not timestamp_str:
            return None
        
        try:
            # Nettoyer le timestamp (enlever Z et millisecondes si présentes)
            clean_timestamp = timestamp_str.replace('Z', '').split('.')[0]
            
            # Essayer de parser différents formats
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y%m%d_%H%M%S',
                '%Y-%m-%dT%H:%M'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(clean_timestamp, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            
            # Si aucun format ne fonctionne
            self.logger.warning(f"Format de timestamp non reconnu: {timestamp_str}")
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur de formatage timestamp {timestamp_str}: {e}")
            return None
    
    def _clean_numeric_value(self, value: Any, decimal_places: int = 2) -> Optional[Decimal]:
        """
        Nettoie et convertit une valeur numérique
        
        Args:
            value: Valeur à convertir
            decimal_places: Nombre de décimales
            
        Returns:
            Decimal: Valeur convertie ou None si impossible
        """
        if value is None or value == '':
            return None
        
        try:
            # Convertir en string et nettoyer
            str_value = str(value).strip()
            
            # Enlever les caractères non numériques (sauf . et -)
            cleaned = re.sub(r'[^\d\.\-]', '', str_value)
            
            if not cleaned or cleaned == '-':
                return None
            
            return Decimal(cleaned).quantize(Decimal('0.' + '0' * decimal_places))
            
        except Exception as e:
            self.logger.debug(f"Impossible de convertir '{value}' en numérique: {e}")
            return None
    
    def _clean_integer_value(self, value: Any) -> Optional[int]:
        """
        Nettoie et convertit une valeur entière
        
        Args:
            value: Valeur à convertir
            
        Returns:
            int: Valeur convertie ou None si impossible
        """
        if value is None or value == '':
            return None
        
        try:
            # Nettoyer et convertir
            str_value = str(value).strip()
            cleaned = re.sub(r'[^\d\-]', '', str_value)
            
            if not cleaned or cleaned == '-':
                return None
            
            return int(cleaned)
            
        except Exception as e:
            self.logger.debug(f"Impossible de convertir '{value}' en entier: {e}")
            return None
    
    def _extract_sky_conditions(self, doc: Dict, prefix: str = "") -> List[Dict]:
        """
        Extrait les conditions de ciel d'un document METAR ou TAF
        
        Args:
            doc: Document METAR ou TAF depuis MongoDB
            prefix: Préfixe pour les champs (ex: "forecast_" pour TAF)
            
        Returns:
            List[Dict]: Liste des conditions de ciel
        """
        conditions = []
        
        # Construire le nom du champ selon le préfixe
        sky_condition_field = f"{prefix}sky_condition" if prefix else "sky_condition"
        
        # Vérifier si sky_condition est un tableau
        sky_condition = doc.get(sky_condition_field)
        if isinstance(sky_condition, list):
            # Cas où on a un tableau de conditions de ciel
            for idx, condition in enumerate(sky_condition[:4]):  # Limiter à 4 conditions
                if isinstance(condition, dict):
                    sky_cover = condition.get('@sky_cover')
                    cloud_base = condition.get('@cloud_base_ft_agl')
                    cloud_type = condition.get('@cloud_type')
                    
                    if sky_cover:  # Au minimum sky_cover doit être présent
                        conditions.append({
                            'sky_cover': sky_cover,
                            'cloud_base_ft_agl': self._clean_integer_value(cloud_base),
                            'cloud_type': cloud_type,
                            'condition_order': idx + 1
                        })
        else:
            # Cas où on a une seule condition (format direct)
            sky_cover = (doc.get(f'{prefix}sky_condition_@sky_cover') or 
                        doc.get(f'@{prefix}sky_condition_sky_cover') or 
                        doc.get(f'{prefix}sky_condition_sky_cover'))
            cloud_base = (doc.get(f'{prefix}sky_condition_@cloud_base_ft_agl') or 
                         doc.get(f'@{prefix}sky_condition_cloud_base_ft_agl') or 
                         doc.get(f'{prefix}sky_condition_cloud_base_ft_agl'))
            cloud_type = (doc.get(f'{prefix}sky_condition_@cloud_type') or 
                         doc.get(f'@{prefix}sky_condition_cloud_type') or 
                         doc.get(f'{prefix}sky_condition_cloud_type'))
            
            if sky_cover:
                conditions.append({
                    'sky_cover': sky_cover,
                    'cloud_base_ft_agl': self._clean_integer_value(cloud_base),
                    'cloud_type': cloud_type,
                    'condition_order': 1
                })
        
        return conditions
    
    def _parse_sky_conditions(self, metar_doc: Dict) -> Dict:
        """
        Parse les conditions de ciel multiples depuis le document METAR
        
        Args:
            metar_doc: Document METAR depuis MongoDB
            
        Returns:
            Dict: Dictionnaire avec les conditions de ciel parsées (sky_condition_sky_cover1, etc.)
        """
        sky_conditions = {}
        
        # Initialiser les 4 emplacements possibles
        for i in range(1, 5):
            sky_conditions[f'sky_condition_sky_cover{i}'] = None
            sky_conditions[f'sky_condition_cloud_base_ft_agl{i}'] = None
        
        # Vérifier si sky_condition est un tableau
        sky_condition = metar_doc.get('sky_condition')
        if isinstance(sky_condition, list):
            # Cas où on a un tableau de conditions de ciel
            for idx, condition in enumerate(sky_condition[:4]):  # Limiter à 4 conditions
                position = idx + 1
                if isinstance(condition, dict):
                    # Extraire @sky_cover et @cloud_base_ft_agl
                    sky_cover = condition.get('@sky_cover')
                    cloud_base = condition.get('@cloud_base_ft_agl')
                    
                    sky_conditions[f'sky_condition_sky_cover{position}'] = sky_cover
                    sky_conditions[f'sky_condition_cloud_base_ft_agl{position}'] = self._clean_integer_value(cloud_base)
        
        else:
            # Cas où on a une seule condition (format direct)
            sky_cover = (metar_doc.get('sky_condition_@sky_cover') or 
                        metar_doc.get('@sky_condition_sky_cover') or 
                        metar_doc.get('sky_condition_sky_cover'))
            cloud_base = (metar_doc.get('sky_condition_@cloud_base_ft_agl') or 
                         metar_doc.get('@sky_condition_cloud_base_ft_agl') or 
                         metar_doc.get('sky_condition_cloud_base_ft_agl'))
            
            if sky_cover is not None:
                sky_conditions['sky_condition_sky_cover1'] = sky_cover
                sky_conditions['sky_condition_cloud_base_ft_agl1'] = self._clean_integer_value(cloud_base)
        
        return sky_conditions
    
    def _prepare_metar_data(self, metar_doc: Dict) -> Dict:
        """
        Prépare un document METAR pour l'insertion PostgreSQL
        
        Args:
            metar_doc: Document METAR depuis MongoDB
            
        Returns:
            Dict: Données formatées pour PostgreSQL
        """
        # Mapping des champs MongoDB vers PostgreSQL
        data = {
            'external_id': metar_doc.get('_id'),  # Stocker l'ID MongoDB original
            'observation_time': self._format_timestamp(
                metar_doc.get('@observation_time') or metar_doc.get('observation_time')
            ),
            'raw_text': metar_doc.get('@raw_text') or metar_doc.get('raw_text') or '',
            'station_id': metar_doc.get('@station_id') or metar_doc.get('station_id'),
            'wind_dir_degrees': str(self._clean_integer_value(
                metar_doc.get('@wind_dir_degrees') or metar_doc.get('wind_dir_degrees')
            )) if self._clean_integer_value(
                metar_doc.get('@wind_dir_degrees') or metar_doc.get('wind_dir_degrees')
            ) is not None else None,
            'temp_c': self._clean_numeric_value(
                metar_doc.get('@temp_c') or metar_doc.get('temp_c')
            ),
            'dewpoint_c': self._clean_numeric_value(
                metar_doc.get('@dewpoint_c') or metar_doc.get('dewpoint_c')
            ),
            'wind_speed_kt': self._clean_integer_value(
                metar_doc.get('@wind_speed_kt') or metar_doc.get('wind_speed_kt')
            ),
            'wind_gust_kt': self._clean_integer_value(
                metar_doc.get('@wind_gust_kt') or metar_doc.get('wind_gust_kt')
            ),
            'visibility_statute_mi': self._clean_numeric_value(
                metar_doc.get('@visibility_statute_mi') or metar_doc.get('visibility_statute_mi')
            ),
            'altim_in_hg': self._clean_numeric_value(
                metar_doc.get('@altim_in_hg') or metar_doc.get('altim_in_hg')
            ),
            'sea_level_pressure_mb': self._clean_numeric_value(
                metar_doc.get('@sea_level_pressure_mb') or metar_doc.get('sea_level_pressure_mb'), 2
            ),
            'flight_category': metar_doc.get('@flight_category') or metar_doc.get('flight_category'),
            'maxt_c': self._clean_numeric_value(
                metar_doc.get('@maxT_c') or metar_doc.get('maxT_c')
            ),
            'mint_c': self._clean_numeric_value(
                metar_doc.get('@minT_c') or metar_doc.get('minT_c')
            ),
            'metar_type': metar_doc.get('@metar_type') or metar_doc.get('metar_type'),
            'pcp3hr_in': self._clean_numeric_value(
                metar_doc.get('@pcp3hr_in') or metar_doc.get('pcp3hr_in'), 3
            ),
            'pcp6hr_in': self._clean_numeric_value(
                metar_doc.get('@pcp6hr_in') or metar_doc.get('pcp6hr_in'), 3
            ),
            'pcp24hr_in': self._clean_numeric_value(
                metar_doc.get('@pcp24hr_in') or metar_doc.get('pcp24hr_in'), 3
            ),
            'precip_in': self._clean_numeric_value(
                metar_doc.get('@precip_in') or metar_doc.get('precip_in'), 3
            ),
            'three_hr_pressure_tendency_mb': self._clean_numeric_value(
                metar_doc.get('@three_hr_pressure_tendency_mb') or metar_doc.get('three_hr_pressure_tendency_mb'), 2
            ),
            'vert_vis_ft': self._clean_integer_value(
                metar_doc.get('@vert_vis_ft') or metar_doc.get('vert_vis_ft')
            ),
            'wx_string': metar_doc.get('@wx_string') or metar_doc.get('wx_string')
        }
        
        # Ajouter les conditions de ciel multiples
        sky_conditions = self._parse_sky_conditions(metar_doc)
        data.update(sky_conditions)
        
        # Vérifier les champs obligatoires
        if not data['external_id'] or not data['station_id']:
            raise ValueError(f"Champs obligatoires manquants: external_id={data['external_id']}, station_id={data['station_id']}")
        
        return data
    
    def _prepare_taf_data(self, taf_doc: Dict) -> Dict:
        """
        Prépare un document TAF pour l'insertion PostgreSQL
        
        Args:
            taf_doc: Document TAF depuis MongoDB
            
        Returns:
            Dict: Données formatées pour PostgreSQL
        """
        # Mapping des champs MongoDB vers PostgreSQL
        data = {
            'external_id': taf_doc.get('_id'),  # Stocker l'ID MongoDB original
            'station_id': taf_doc.get('@station_id') or taf_doc.get('station_id'),
            'issue_time': self._format_timestamp(
                taf_doc.get('@issue_time') or taf_doc.get('issue_time')
            ),
            'bulletin_time': self._format_timestamp(
                taf_doc.get('@bulletin_time') or taf_doc.get('bulletin_time')
            ),
            'valid_time_from': self._format_timestamp(
                taf_doc.get('@valid_time_from') or taf_doc.get('valid_time_from')
            ),
            'valid_time_to': self._format_timestamp(
                taf_doc.get('@valid_time_to') or taf_doc.get('valid_time_to')
            ),
            'remarks': taf_doc.get('@remarks') or taf_doc.get('remarks'),
            'fcst_time_from': self._format_timestamp(
                taf_doc.get('forecast_@fcst_time_from') or taf_doc.get('forecast_fcst_time_from')
            ),
            'fcst_time_to': self._format_timestamp(
                taf_doc.get('forecast_@fcst_time_to') or taf_doc.get('forecast_fcst_time_to')
            ),
            'wind_dir_degrees': self._clean_integer_value(
                taf_doc.get('forecast_@wind_dir_degrees') or taf_doc.get('forecast_wind_dir_degrees')
            ),
            'wind_speed_kt': self._clean_integer_value(
                taf_doc.get('forecast_@wind_speed_kt') or taf_doc.get('forecast_wind_speed_kt')
            ),
            'wind_gust_kt': self._clean_integer_value(
                taf_doc.get('forecast_@wind_gust_kt') or taf_doc.get('forecast_wind_gust_kt')
            ),
            'visibility_statute_mi': self._clean_numeric_value(
                taf_doc.get('forecast_@visibility_statute_mi') or taf_doc.get('forecast_visibility_statute_mi')
            ),
            'vert_vis_ft': self._clean_integer_value(
                taf_doc.get('forecast_@vert_vis_ft') or taf_doc.get('forecast_vert_vis_ft')
            ),
            'wx_string': taf_doc.get('forecast_@wx_string') or taf_doc.get('forecast_wx_string'),
            'altim_in_hg': self._clean_numeric_value(
                taf_doc.get('forecast_@altim_in_hg') or taf_doc.get('forecast_altim_in_hg')
            ),
            'change_indicator': taf_doc.get('forecast_@change_indicator') or taf_doc.get('forecast_change_indicator'),
            'probability': self._clean_integer_value(
                taf_doc.get('forecast_@probability') or taf_doc.get('forecast_probability')
            ),
            'max_temp_c': self._clean_numeric_value(
                taf_doc.get('forecast_@max_temp_c') or taf_doc.get('forecast_max_temp_c')
            ),
            'min_temp_c': self._clean_numeric_value(
                taf_doc.get('forecast_@min_temp_c') or taf_doc.get('forecast_min_temp_c')
            ),
            'raw_text': taf_doc.get('@raw_text') or taf_doc.get('raw_text') or ''
        }
        
        # Vérifier les champs obligatoires
        if not data['external_id'] or not data['station_id']:
            raise ValueError(f"Champs obligatoires manquants: external_id={data['external_id']}, station_id={data['station_id']}")
        
        return data
    
    def _insert_sky_conditions(self, sky_conditions: List[Dict], metar_external_id: str = None, taf_external_id: str = None) -> int:
        """
        Insère les conditions de ciel dans la table sky_condition
        
        Args:
            sky_conditions: Liste des conditions de ciel
            metar_external_id: External ID du METAR (optionnel)
            taf_external_id: External ID du TAF (optionnel)
            
        Returns:
            int: Nombre de conditions insérées
        """
        if not sky_conditions or not self.connection:
            return 0
        
        inserted_count = 0
        cursor = None
        
        try:
            cursor = self.connection.cursor()
            
            # Récupérer l'ID numérique PostgreSQL à partir de l'external_id
            metar_fk = None
            taf_fk = None
            
            if metar_external_id:
                cursor.execute("SELECT id FROM metar WHERE external_id = %s", (metar_external_id,))
                result = cursor.fetchone()
                if result:
                    metar_fk = result[0]
            
            if taf_external_id:
                cursor.execute("SELECT id FROM taf WHERE external_id = %s", (taf_external_id,))
                result = cursor.fetchone()
                if result:
                    taf_fk = result[0]
            
            # Si on n'a pas trouvé l'ID parent, on ne peut pas insérer
            if not metar_fk and not taf_fk:
                self.logger.warning(f"Aucun parent trouvé pour les sky_conditions (metar_external_id={metar_external_id}, taf_external_id={taf_external_id})")
                return 0
            
            insert_query = """
                INSERT INTO sky_condition (
                    metar_fk, taf_fk, sky_cover, cloud_base_ft_agl, cloud_type, condition_order
                ) VALUES (
                    %(metar_fk)s, %(taf_fk)s, %(sky_cover)s, %(cloud_base_ft_agl)s, %(cloud_type)s, %(condition_order)s
                )
            """
            
            for condition in sky_conditions:
                try:
                    condition_data = {
                        'metar_fk': metar_fk,
                        'taf_fk': taf_fk,
                        'sky_cover': condition['sky_cover'],
                        'cloud_base_ft_agl': condition['cloud_base_ft_agl'],
                        'cloud_type': condition.get('cloud_type'),
                        'condition_order': condition['condition_order']
                    }
                    
                    cursor.execute(insert_query, condition_data)
                    
                    if cursor.rowcount > 0:
                        inserted_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Erreur insertion sky_condition: {e}")
                    continue
            
            return inserted_count
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'insertion des sky_conditions: {e}")
            return 0
        
        finally:
            if cursor:
                cursor.close()
    
    def insert_metar_batch(self, metar_docs: List[Dict]) -> int:
        """
        Insère un lot de documents METAR dans PostgreSQL
        
        Args:
            metar_docs: Liste des documents METAR à insérer
            
        Returns:
            int: Nombre de documents insérés avec succès
        """
        if not metar_docs:
            return 0
        
        if not self.test_connection():
            self.logger.error("Pas de connexion PostgreSQL pour l'insertion METAR")
            return 0
        
        inserted_count = 0
        cursor = None
        
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
                INSERT INTO metar (
                    external_id, observation_time, raw_text, station_id, wind_dir_degrees,
                    temp_c, dewpoint_c, wind_speed_kt, wind_gust_kt, visibility_statute_mi,
                    altim_in_hg, sea_level_pressure_mb, flight_category,
                    maxt_c, mint_c, metar_type, pcp3hr_in, pcp6hr_in, pcp24hr_in,
                    precip_in, three_hr_pressure_tendency_mb, vert_vis_ft, wx_string
                ) VALUES (
                    %(external_id)s, %(observation_time)s, %(raw_text)s, %(station_id)s, %(wind_dir_degrees)s,
                    %(temp_c)s, %(dewpoint_c)s, %(wind_speed_kt)s, %(wind_gust_kt)s, %(visibility_statute_mi)s,
                    %(altim_in_hg)s, %(sea_level_pressure_mb)s, %(flight_category)s,
                    %(maxt_c)s, %(mint_c)s, %(metar_type)s, %(pcp3hr_in)s, %(pcp6hr_in)s, %(pcp24hr_in)s,
                    %(precip_in)s, %(three_hr_pressure_tendency_mb)s, %(vert_vis_ft)s, %(wx_string)s
                )
                ON CONFLICT (external_id) DO NOTHING
            """
            
            for metar_doc in metar_docs:
                try:
                    prepared_data = self._prepare_metar_data(metar_doc)
                    cursor.execute(insert_query, prepared_data)
                    
                    if cursor.rowcount > 0:
                        inserted_count += 1
                        
                        # Insérer les conditions de ciel dans la table séparée
                        sky_conditions = self._extract_sky_conditions(metar_doc)
                        if sky_conditions:
                            sky_inserted = self._insert_sky_conditions(
                                sky_conditions, 
                                metar_external_id=prepared_data['external_id']
                            )
                            self.logger.debug(f"✓ {sky_inserted} conditions de ciel insérées pour METAR {prepared_data['external_id']}")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur insertion METAR {metar_doc.get('_id', 'unknown')}: {e}")
                    continue
            
            self.connection.commit()
            self.logger.info(f"✓ {inserted_count} documents METAR insérés dans PostgreSQL")
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"Erreur lors de l'insertion METAR: {e}")
            
        finally:
            if cursor:
                cursor.close()
        
        return inserted_count
    
    def insert_taf_batch(self, taf_docs: List[Dict]) -> int:
        """
        Insère un lot de documents TAF dans PostgreSQL
        
        Args:
            taf_docs: Liste des documents TAF à insérer
            
        Returns:
            int: Nombre de documents insérés avec succès
        """
        if not taf_docs:
            return 0
        
        if not self.test_connection():
            self.logger.error("Pas de connexion PostgreSQL pour l'insertion TAF")
            return 0
        
        inserted_count = 0
        cursor = None
        
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
                INSERT INTO taf (
                    external_id, station_id, issue_time, bulletin_time, valid_time_from, valid_time_to,
                    remarks, fcst_time_from, fcst_time_to, wind_dir_degrees, wind_speed_kt,
                    wind_gust_kt, visibility_statute_mi, vert_vis_ft, wx_string,
                    altim_in_hg, change_indicator, probability,
                    max_temp_c, min_temp_c, raw_text
                ) VALUES (
                    %(external_id)s, %(station_id)s, %(issue_time)s, %(bulletin_time)s, %(valid_time_from)s, %(valid_time_to)s,
                    %(remarks)s, %(fcst_time_from)s, %(fcst_time_to)s, %(wind_dir_degrees)s, %(wind_speed_kt)s,
                    %(wind_gust_kt)s, %(visibility_statute_mi)s, %(vert_vis_ft)s, %(wx_string)s,
                    %(altim_in_hg)s, %(change_indicator)s, %(probability)s,
                    %(max_temp_c)s, %(min_temp_c)s, %(raw_text)s
                )
                ON CONFLICT (external_id) DO NOTHING
            """
            
            for taf_doc in taf_docs:
                try:
                    prepared_data = self._prepare_taf_data(taf_doc)
                    cursor.execute(insert_query, prepared_data)
                    
                    if cursor.rowcount > 0:
                        inserted_count += 1
                        
                        # Insérer les conditions de ciel dans la table séparée
                        sky_conditions = self._extract_sky_conditions(taf_doc, "forecast_")
                        if sky_conditions:
                            sky_inserted = self._insert_sky_conditions(
                                sky_conditions, 
                                taf_external_id=prepared_data['external_id']
                            )
                            self.logger.debug(f"✓ {sky_inserted} conditions de ciel insérées pour TAF {prepared_data['external_id']}")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur insertion TAF {taf_doc.get('_id', 'unknown')}: {e}")
                    continue
            
            self.connection.commit()
            self.logger.info(f"✓ {inserted_count} documents TAF insérés dans PostgreSQL")
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"Erreur lors de l'insertion TAF: {e}")
            
        finally:
            if cursor:
                cursor.close()
        
        return inserted_count
    
    def _prepare_flight_data(self, flight_doc: Dict) -> Dict:
        """
        Prépare un document vol pour l'insertion PostgreSQL
        
        Args:
            flight_doc: Document vol depuis MongoDB
            
        Returns:
            Dict: Données formatées pour PostgreSQL
        """
        # Extraire le code compagnie (2 premiers caractères du numéro de vol)
        flight_number = flight_doc.get('flight_number', '')
        airline_code = flight_number[:2] if flight_number else None
        
        # Mapping des champs MongoDB vers PostgreSQL
        data = {
            'flight_number': flight_number,
            'from_airport': flight_doc.get('from_code'),
            'to_airport': flight_doc.get('to_code'),
            'airline_code': airline_code,
            'aircraft_code': None,  # Vide pour l'instant comme demandé
            
            # Stocker les IDs MongoDB pour le mapping ultérieur
            'departure_metar_external_id': flight_doc.get('metar_id'),  # ID MongoDB du METAR
            'arrival_taf_external_id': flight_doc.get('taf_id'),        # ID MongoDB du TAF
            
            # Les clés étrangères seront remplies par une requête de mapping séparée
            'departure_metar_fk': None,
            'arrival_taf_fk': None,
            
            # Horaires de départ
            'departure_scheduled_utc': self._format_timestamp(
                flight_doc.get('departure', {}).get('scheduled_utc')
            ),
            'departure_actual_utc': self._format_timestamp(
                flight_doc.get('departure', {}).get('estimated_utc')
            ),
            'departure_terminal': flight_doc.get('departure', {}).get('terminal'),
            'departure_gate': flight_doc.get('departure', {}).get('gate'),
            
            # Horaires d'arrivée
            'arrival_scheduled_utc': self._format_timestamp(
                flight_doc.get('arrival', {}).get('scheduled_utc')
            ),
            'arrival_actual_utc': self._format_timestamp(
                flight_doc.get('arrival', {}).get('estimated_utc')
            ),
            'arrival_terminal': flight_doc.get('arrival', {}).get('terminal'),
            'arrival_gate': flight_doc.get('arrival', {}).get('gate'),
            
            # Statut et retard
            'status': flight_doc.get('status'),
            'status_final': None,  # Sera rempli lors de la mise à jour avec les données réelles
            'delay_min': self._calculate_delay_minutes(flight_doc)
        }
        
        # Vérifier les champs obligatoires
        if not data['flight_number'] or not data['from_airport'] or not data['to_airport']:
            raise ValueError(f"Champs obligatoires manquants: flight_number={data['flight_number']}, "
                           f"from_airport={data['from_airport']}, to_airport={data['to_airport']}")
        
        return data
    
    def _calculate_delay_minutes(self, flight_doc: Dict) -> Optional[int]:
        """
        Calcule le retard en minutes
        
        Args:
            flight_doc: Document vol
            
        Returns:
            int: Retard en minutes ou None si impossible à calculer
        """
        try:
            # Utiliser l'arrivée pour calculer le retard
            scheduled_str = flight_doc.get('arrival', {}).get('scheduled_utc')
            actual_str = flight_doc.get('arrival', {}).get('actual_utc')
            
            if not scheduled_str or not actual_str:
                return None
            
            # Parser les timestamps
            scheduled = datetime.fromisoformat(scheduled_str.replace('Z', '+00:00'))
            actual = datetime.fromisoformat(actual_str.replace('Z', '+00:00'))
            
            # Calculer la différence en minutes
            delay_seconds = (actual - scheduled).total_seconds()
            delay_minutes = int(delay_seconds / 60)
            
            # Retourner seulement les retards positifs
            return max(delay_minutes, 0) if delay_minutes > 0 else 0
            
        except Exception as e:
            self.logger.debug(f"Impossible de calculer le retard: {e}")
            return None
    
    def insert_flights_batch(self, flight_docs: List[Dict]) -> tuple:
        """
        Insère un lot de documents vol dans PostgreSQL et retourne les IDs insérés
        Filtre automatiquement les vols qui ont un operated_by
        
        Args:
            flight_docs: Liste des documents vol à insérer
            
        Returns:
            tuple: (nombre_insérés, liste_des_ids_insérés)
        """
        if not flight_docs:
            return 0, []
        
        # Filtrer les vols qui n'ont PAS de operated_by
        filtered_flights = [
            flight for flight in flight_docs 
            if not flight.get('operated_by')
        ]
        
        if not filtered_flights:
            self.logger.info("Aucun vol à insérer (tous ont un operated_by)")
            return 0, []
        
        self.logger.info(f"Insertion de {len(filtered_flights)} vols (sur {len(flight_docs)} total, {len(flight_docs) - len(filtered_flights)} filtrés)")
        
        if not self.test_connection():
            self.logger.error("Pas de connexion PostgreSQL pour l'insertion des vols")
            return 0, []
        
        inserted_count = 0
        inserted_ids = []
        cursor = None
        
        try:
            cursor = self.connection.cursor()
            
            insert_query = """
                INSERT INTO flight (
                    flight_number, from_airport, to_airport, airline_code, aircraft_code,
                    departure_metar_external_id, departure_scheduled_utc, departure_actual_utc, 
                    departure_terminal, departure_gate,
                    arrival_taf_external_id, arrival_scheduled_utc, arrival_actual_utc, 
                    arrival_terminal, arrival_gate,
                    status, status_final, delay_min
                ) VALUES (
                    %(flight_number)s, %(from_airport)s, %(to_airport)s, %(airline_code)s, %(aircraft_code)s,
                    %(departure_metar_external_id)s, %(departure_scheduled_utc)s, %(departure_actual_utc)s, 
                    %(departure_terminal)s, %(departure_gate)s,
                    %(arrival_taf_external_id)s, %(arrival_scheduled_utc)s, %(arrival_actual_utc)s, 
                    %(arrival_terminal)s, %(arrival_gate)s,
                    %(status)s, %(status_final)s, %(delay_min)s
                )
                ON CONFLICT DO NOTHING
                RETURNING id
            """
            
            for flight_doc in filtered_flights:
                try:
                    prepared_data = self._prepare_flight_data(flight_doc)
                    cursor.execute(insert_query, prepared_data)
                    
                    # Récupérer l'ID du vol inséré
                    result = cursor.fetchone()
                    if result:
                        inserted_ids.append(result[0])
                        inserted_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"Erreur insertion vol {flight_doc.get('flight_number', 'unknown')}: {e}")
                    continue
            
            self.connection.commit()
            self.logger.info(f"✓ {inserted_count} vols insérés dans PostgreSQL (IDs: {len(inserted_ids)})")
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"Erreur lors de l'insertion des vols: {e}")
            
        finally:
            if cursor:
                cursor.close()
        
        return inserted_count, inserted_ids
    
    def update_flight_foreign_keys(self) -> int:
        """
        Met à jour les clés étrangères des vols en utilisant les external_id
        
        Returns:
            int: Nombre de vols mis à jour
        """
        if not self.test_connection():
            self.logger.error("Pas de connexion PostgreSQL pour la mise à jour des clés étrangères")
            return 0
        
        updated_count = 0
        cursor = None
        
        try:
            cursor = self.connection.cursor()
            
            # Mise à jour des clés étrangères METAR de départ
            metar_update_query = """
                UPDATE flight 
                SET departure_metar_fk = m.id
                FROM metar m 
                WHERE flight.departure_metar_external_id = m.external_id
                AND flight.departure_metar_fk IS NULL
                AND flight.departure_metar_external_id IS NOT NULL
            """
            
            cursor.execute(metar_update_query)
            metar_updated = cursor.rowcount
            self.logger.info(f"Clés étrangères METAR mises à jour: {metar_updated}")
            
            # Mise à jour des clés étrangères TAF d'arrivée
            taf_update_query = """
                UPDATE flight 
                SET arrival_taf_fk = t.id
                FROM taf t 
                WHERE flight.arrival_taf_external_id = t.external_id
                AND flight.arrival_taf_fk IS NULL
                AND flight.arrival_taf_external_id IS NOT NULL
            """
            
            cursor.execute(taf_update_query)
            taf_updated = cursor.rowcount
            self.logger.info(f"Clés étrangères TAF mises à jour: {taf_updated}")
            
            self.connection.commit()
            updated_count = metar_updated + taf_updated
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"Erreur lors de la mise à jour des clés étrangères: {e}")
            
        finally:
            if cursor:
                cursor.close()
        
        return updated_count
    
    def update_flights_batch(self, flight_docs: List[Dict]) -> int:
        """
        Met à jour un lot de vols dans PostgreSQL avec les données réelles
        
        Args:
            flight_docs: Liste des documents vol à mettre à jour
            
        Returns:
            int: Nombre de documents mis à jour avec succès
        """
        if not flight_docs:
            return 0
        
        if not self.test_connection():
            self.logger.error("Pas de connexion PostgreSQL pour la mise à jour des vols")
            return 0
        
        updated_count = 0
        cursor = None
        
        try:
            cursor = self.connection.cursor()
            
            # Requête de mise à jour basée sur flight_number + from_airport + to_airport
            update_query = """
                UPDATE flight SET
                    departure_final_utc = %(departure_actual_utc)s,
                    arrival_actual_utc = %(arrival_actual_utc)s,
                    status_final = %(status_final)s,
                    delay_min = %(delay_min)s
                WHERE flight_number = %(flight_number)s 
                  AND from_airport = %(from_airport)s 
                  AND to_airport = %(to_airport)s
                  AND departure_scheduled_utc = %(departure_scheduled_utc)s
            """
            
            for flight_doc in flight_docs:
                try:
                    # Préparer les données de mise à jour
                    update_data = {
                        'flight_number': flight_doc.get('flight_number'),
                        'from_airport': flight_doc.get('from_code'),
                        'to_airport': flight_doc.get('to_code'),
                        'departure_actual_utc': self._format_timestamp(
                            flight_doc.get('departure', {}).get('estimated_utc')
                        ),
                        'arrival_actual_utc': self._format_timestamp(
                            flight_doc.get('arrival', {}).get('estimated_utc')
                        ),
                        'departure_scheduled_utc': self._format_timestamp(
                            flight_doc.get('departure', {}).get('scheduled_utc')
                        ),
                        'status_final': flight_doc.get('status'),
                        'delay_min': flight_doc.get('arrival', {}).get('delay', {}).get('minutes')
                    }
                    
                    # Vérifier que nous avons les données nécessaires
                    if not update_data['flight_number'] or not update_data['from_airport'] or not update_data['to_airport']:
                        self.logger.warning(f"Données insuffisantes pour mise à jour vol: {flight_doc.get('_id', 'unknown')}")
                        continue
                    
                    cursor.execute(update_query, update_data)
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
                        self.logger.debug(f"Vol mis à jour: {update_data['flight_number']} {update_data['from_airport']}->{update_data['to_airport']}")
                    else:
                        self.logger.debug(f"Aucune correspondance trouvée pour: {update_data['flight_number']} {update_data['from_airport']}->{update_data['to_airport']}")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur mise à jour vol {flight_doc.get('flight_number', 'unknown')}: {e}")
                    continue
            
            self.connection.commit()
            self.logger.info(f"✓ {updated_count} vols mis à jour dans PostgreSQL")
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"Erreur lors de la mise à jour des vols: {e}")
            
        finally:
            if cursor:
                cursor.close()
        
        return updated_count
    
    def _calculate_delay_minutes(self, flight_doc: Dict) -> Optional[int]:
        """
        Calcule le retard en minutes entre départ prévu et départ réel
        
        Args:
            flight_doc: Document vol avec informations de départ
            
        Returns:
            int: Retard en minutes (positif = retard, négatif = avance) ou None
        """
        try:
            departure_data = flight_doc.get('departure', {})
            scheduled_utc = departure_data.get('scheduled_utc')
            actual_utc = departure_data.get('actual_utc')
            
            if not scheduled_utc or not actual_utc:
                return None
            
            # Convertir les timestamps en datetime
            scheduled_dt = None
            actual_dt = None
            
            try:
                if isinstance(scheduled_utc, str):
                    scheduled_dt = datetime.fromisoformat(scheduled_utc.replace('Z', '+00:00'))
                if isinstance(actual_utc, str):
                    actual_dt = datetime.fromisoformat(actual_utc.replace('Z', '+00:00'))
            except Exception:
                return None
                
            if scheduled_dt and actual_dt:
                delta = actual_dt - scheduled_dt
                return int(delta.total_seconds() / 60)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur calcul retard pour vol {flight_doc.get('flight_number', 'unknown')}: {e}")
            return None
    
    # ========================================================================
    # MÉTHODES MACHINE LEARNING
    # ========================================================================
    
    def fetch_flights_by_ids(self, flight_ids: List[int]):
        """
        Récupère les vols par leurs IDs depuis la vue "all"
        
        Args:
            flight_ids: Liste des IDs de vols
            
        Returns:
            DataFrame pandas avec les données des vols
        
        Raises:
            Exception: Si pas de connexion ou erreur SQL
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas est requis pour cette méthode. Installez-le avec: pip install pandas")
        
        if not flight_ids:
            self.logger.info("📊 Aucun ID de vol fourni")
            return pd.DataFrame()
        
        if not self.test_connection():
            raise Exception("Pas de connexion PostgreSQL")
        
        self.logger.info(f"📊 Récupération de {len(flight_ids)} vols par IDs depuis la view 'all'...")
        
        query = """
            SELECT * FROM public."all"
            WHERE f_id = ANY(%s)
            ORDER BY f_id DESC
        """
        
        try:
            df = pd.read_sql_query(query, self.connection, params=(flight_ids,))
            self.logger.info(f"✅ {len(df)} vols récupérés par IDs")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la récupération des vols par IDs: {e}")
            raise
    
    def fetch_last_n_flights(self, n: int = 1000):
        """
        Récupère les N dernières lignes de la view "all" pour prédiction ML
        
        Args:
            n: Nombre de lignes à récupérer (défaut: 1000)
        
        Returns:
            DataFrame pandas avec les données des vols
        
        Raises:
            Exception: Si pas de connexion ou erreur SQL
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas est requis pour cette méthode. Installez-le avec: pip install pandas")
        
        if not self.test_connection():
            raise Exception("Pas de connexion PostgreSQL")
        
        self.logger.info(f"📊 Récupération des {n} derniers vols depuis la view 'all'...")
        
        query = f"""
            SELECT * FROM public."all"
            ORDER BY f_id DESC
            LIMIT {n}
        """
        
        try:
            df = pd.read_sql_query(query, self.connection)
            self.logger.info(f"✅ {len(df)} lignes récupérées")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la récupération des données: {e}")
            raise
    
    def update_flight_predictions(self, predictions) -> int:
        """
        Met à jour les probabilités de retard et niveaux de risque dans la table flight
        
        Args:
            predictions: DataFrame pandas avec colonnes:
                        - f_id ou id: Identifiant du vol
                        - delay_probability ou probability: Probabilité de retard (0-1)
                        - risk_level: Niveau de risque ("Faible", "Modéré", "Élevé")
        
        Returns:
            int: Nombre de lignes mises à jour
        
        Raises:
            Exception: Si pas de connexion ou erreur SQL
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas est requis pour cette méthode. Installez-le avec: pip install pandas")
        
        if not self.test_connection():
            raise Exception("Pas de connexion PostgreSQL")
        
        self.logger.info("💾 Mise à jour des probabilités et niveaux de risque dans PostgreSQL...")
        
        cursor = None
        updated_count = 0
        
        try:
            cursor = self.connection.cursor()
            
            # Détection automatique des noms de colonnes
            id_col = 'f_id' if 'f_id' in predictions.columns else 'id'
            prob_col = 'delay_probability' if 'delay_probability' in predictions.columns else 'probability'
            risk_col = 'risk_level'
            
            # Requête UPDATE pour probabilité ET niveau de risque
            update_query = "UPDATE flight SET delay_prob = %s, delay_risk_level = %s WHERE id = %s"
            
            for idx, row in predictions.iterrows():
                try:
                    flight_id = row[id_col]
                    delay_prob = row[prob_col]
                    risk_level = row.get(risk_col, None)
                    
                    if pd.notna(delay_prob):
                        cursor.execute(update_query, (
                            float(delay_prob), 
                            risk_level if pd.notna(risk_level) else None,
                            int(flight_id)
                        ))
                        if cursor.rowcount > 0:
                            updated_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Erreur vol {flight_id}: {e}")
                    continue
            
            self.connection.commit()
            self.logger.info(f"✅ {updated_count} lignes mises à jour (delay_prob + delay_risk_level)")
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"❌ Erreur lors de la mise à jour: {e}")
            raise
            
        finally:
            if cursor:
                cursor.close()
        
        return updated_count


if __name__ == "__main__":
    # Test de base
    logger = get_logger(__name__)
    
    # Configuration de test
    test_uri = "postgresql://user:password@host:port/database"
    
    manager = PostgreSQLManager(test_uri)
    
    if manager.connect():
        logger.info("Test de connexion PostgreSQL réussi")
        manager.disconnect()
    else:
        logger.error("Test de connexion PostgreSQL échoué")
