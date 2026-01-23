import os
import io
import pandas as pd
from sqlalchemy import create_engine, text
import glob

def get_engine():
    user = os.getenv('DBT_USER', 'postgres')
    password = os.getenv('DBT_PASSWORD', 'postgres')
    host = os.getenv('DBT_HOST', 'airlines_postgresql')
    port = os.getenv('DBT_PORT', '5432')
    dbname = os.getenv('DBT_DBNAME', 'airlines_db')
    return create_engine(f'postgresql://{user}:{password}@{host}:{port}/{dbname}')

def fast_load_csv(file_path, schema, engine):
    table_name = os.path.basename(file_path).replace('.csv', '')
    print(f"Loading {file_path} into {schema}.{table_name}...")
    
    # Read CSV with pandas to handle types and potential issues
    df = pd.read_csv(file_path)
    
    # Create schema and table structure
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()
        # Use pandas to create table structure (empty)
        df.head(0).to_sql(table_name, engine, schema=schema, if_exists='replace', index=False)
    
    # Fast COPY
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        output = io.StringIO()
        df.to_csv(output, sep='\t', header=False, index=False)
        output.seek(0)
        
        sql = f"COPY {schema}.{table_name} FROM STDIN WITH (FORMAT CSV, DELIMITER '\t')"
        cursor.copy_expert(sql, output)
        raw_conn.commit()
        print(f"  ✓ {len(df)} rows loaded successfully.")
    except Exception as e:
        print(f"  ✗ Error loading {table_name}: {e}")
        raw_conn.rollback()
    finally:
        cursor.close()
        raw_conn.close()

def main():
    engine = get_engine()
    seeds_dir = "/seeds"
    schema = "raw"
    
    csv_files = glob.glob(os.path.join(seeds_dir, "*.csv"))
    
    if not csv_files:
        print("No CSV files found in /seeds")
        return

    for csv_file in csv_files:
        fast_load_csv(csv_file, schema, engine)

if __name__ == "__main__":
    main()
