from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Ajout du répertoire flight-collector au PYTHONPATH
sys.path.append('/opt/airflow/flight-collector')

from config.collection_config import CollectionConfig
from orchestration.flight_orchestrator import FlightOrchestrator

default_args = {
    'owner': 'airlines',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def get_orchestrator():
    config = CollectionConfig()
    return FlightOrchestrator(config)

def task_wrapper(step_name, **context):
    orchestrator = get_orchestrator()
    
    # Utilisation de logical_date de Airflow pour garantir un ID unique par run
    logical_date = context['logical_date']
    session_id = logical_date.strftime('%Y%m%d_%H%M%S')
    
    print(f"Executing step {step_name} for session {session_id}")
    
    success = False
    if step_name == 'collect_realtime':
        res = orchestrator.collect_and_store_realtime_flights(session_id)
        success = res.success
    
    elif step_name == 'collect_weather':
        res = orchestrator.collect_and_store_weather_data()
        success = res.success
        
    elif step_name == 'collect_past':
        res = orchestrator.collect_and_store_past_flights(session_id)
        success = res.success
        
    elif step_name == 'associate_metar':
        res = orchestrator.associate_flights_with_metar(session_id)
        success = res.success
        
    elif step_name == 'associate_taf':
        res = orchestrator.associate_flights_with_taf(session_id)
        success = res.success
        
    elif step_name == 'insert_postgres':
        res = orchestrator.insert_weather_and_flight_data_to_postgres(session_id)
        if res.success and res.details and 'inserted_flight_ids' in res.details:
            # Pousse les IDs insérés vers XCom pour l'étape suivante
            context['ti'].xcom_push(key='inserted_flight_ids', value=res.details['inserted_flight_ids'])
        success = res.success
        
    elif step_name == 'predict_ml':
        # Récupère les IDs depuis XCom
        inserted_ids = context['ti'].xcom_pull(task_ids='step_insert_postgres', key='inserted_flight_ids')
        if not inserted_ids:
            print("No flight IDs found in XCom, skipping ML prediction.")
            return True
        res = orchestrator.predict_flights_ml(inserted_ids)
        success = res.success
        
    elif step_name == 'update_postgres':
        res = orchestrator.update_flights_data_to_postgres(session_id)
        success = res.success

    if not success:
        raise Exception(f"Step {step_name} failed. Check logs for details.")
    
    return True

with DAG(
    'flight_collection_full_workflow',
    default_args=default_args,
    description='A complete workflow for airline data collection and processing',
    schedule_interval='35 * * * *', # Toutes les heures à la minute 35
    catchup=False,
    is_paused_upon_creation=False,
    tags=['airlines', 'collection'],
) as dag:

    # Définition des tâches
    t1 = PythonOperator(task_id='step_collect_realtime', python_callable=task_wrapper, op_args=['collect_realtime'])
    t2 = PythonOperator(task_id='step_collect_weather', python_callable=task_wrapper, op_args=['collect_weather'])
    t3 = PythonOperator(task_id='step_collect_past', python_callable=task_wrapper, op_args=['collect_past'])
    
    t4 = PythonOperator(task_id='step_associate_metar', python_callable=task_wrapper, op_args=['associate_metar'])
    t5 = PythonOperator(task_id='step_associate_taf', python_callable=task_wrapper, op_args=['associate_taf'])
    
    t6 = PythonOperator(task_id='step_insert_postgres', python_callable=task_wrapper, op_args=['insert_postgres'])
    
    t7 = PythonOperator(task_id='step_predict_ml', python_callable=task_wrapper, op_args=['predict_ml'])
    
    t8 = PythonOperator(task_id='step_update_postgres', python_callable=task_wrapper, op_args=['update_postgres'])

    # Dépendances du workflow
    # 1. Collectes initiales
    # 2. Associations après collectes
    # 3. Insertion après associations
    # 4. ML après insertion
    # 5. Update flights après collecte passée
    
    t1 >> [t4, t5]
    t2 >> [t4, t5]
    
    [t4, t5] >> t6 >> t7
    
    t3 >> t8
