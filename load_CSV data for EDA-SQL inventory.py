import pyodbc
import pandas as pd
import os
import time
import logging

# '''
# DESKTOP-FI1PI5E\SHIVSHAKTI
# r"h:\KG PD\KG\Codebasics\ANALYTICS ALL\Python-SQL EDA\data\data" '''

logging.basicConfig(filename='db_load.log', level=logging.INFO)

def log_event(event, start, end=None):
    start_time= time.time()
    msg = f"{event} | Start: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))}"
    if end:
        msg += f" | End: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))} | Duration: {end-start:.2f}s"
        end_time=time.time()
    logging.info(msg)
    print(end_time-start_time)

def create_db(server, db_name):
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=Yes"
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE {db_name}")
        print("Database Created Successfully!")
    except pyodbc.Error as e:
        logging.info(f"Create DB error: {e}")
        print("Error while connecting to DB", e)
    cursor.close()
    conn.close()

def connect_db(server, db_name):
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db_name};Trusted_Connection=Yes"
    print("Connected to DB sucessfully!")
    return pyodbc.connect(conn_str, autocommit=True)
    
def load_raw_data(folder_path):
    file_list = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(file_list)
    dfs = []                                                                                                                                                                  
    for file in file_list:
            print(f' Loading ...{file}')
            df = pd.read_csv(os.path.join(folder_path, file))
            dfs.append((file, df))
    return dfs

def db_ingest(conn, dfs):
    print(" Beginning DB ingestion ")
    cursor = conn.cursor()
    for file, df in dfs:
        table_name = os.path.splitext(file)[0]
        cols = ','.join([f'[{col}] VARCHAR(255)' for col in df.columns])
        cursor.execute(f"IF OBJECT_ID('{table_name}', 'U') IS NULL CREATE TABLE {table_name} ({cols})")
        for row in df.itertuples(index=False, name=None):
            col_names = ','.join([f'[{col}]' for col in df.columns])
            placeholders = ','.join(['?' for _ in df.columns])
            cursor.execute(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})", row)
            print(f"Ingested {file}")
    conn.commit()
    cursor.close()

def main_loop(server, db_name, data_folder):
    while True:
        start = time.time()
        dfs = load_raw_data(data_folder)
        print("Connecting to Server")
        conn = connect_db(server, db_name)
        print("connected") #changes
        db_ingest(conn, dfs)
        print("Loaded and ingested") #changes
        conn.close()
        end = time.time()
        log_event(f'Data load from CSVs {", ".join([f for f, _ in dfs])}', start, end)
        print(f"Loaded to DB {db_name}. Sleeping 10 minutes…")
        #time.sleep(600)

if __name__ == "__main__":
    server = input("Enter SQL Server name (e.g. DESKTOP-FI1PI5E\\SHIVSHAKTI): ")
    db_name = input("Enter database name to create/use: ")
    data_folder = input("Enter folder path containing CSVs: ")
    create = input("Create new DB? (yes/no): ").strip().lower()
    if create == 'yes':
        create_db(server, db_name)
    main_loop(server, db_name, data_folder)
