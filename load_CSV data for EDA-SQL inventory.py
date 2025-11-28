import os
import time
import logging
import pandas as pd
import urllib
from sqlalchemy import create_engine, text


logging.basicConfig(filename="DB_Ingest.log", level=logging.INFO)


def log_event(event, start, end=None):
    start_time= time.time()
    msg = f"{event} | Start: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))}"
    if end:
        msg += f" | End: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))} | Duration: {end-start:.2f}s"
        end_time=time.time()
    logging.info(msg)
    print(end_time-start_time)

server = r"xyz"   # Your SQL server name
database = "DB_name"                   # change to your DB name

# This string MUST be exactly what works with pyodbc.connect
odbc_conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)
#With Windows Authentication, no requirements for username and Password to connect
params = urllib.parse.quote_plus(odbc_conn_str)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

print(f"Connected to DB {database} successfully!")

#Test to verify the connection with the server is proper. Initially, because of multi method the ingestion was failing
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS test"))
        print("Connection OK, result:", result.scalar())
except Exception as e:
    print("Connection FAILED:", e)



# INGEST ALL CSVs FROM THE FOLDER
def ingest_folder_to_mssql(folder_path: str):
    
    folder_path = folder_path.strip()
    files = sorted([f for f in os.listdir(folder_path)
             if f.lower().endswith(".csv")])

    for file in files:
        start=time.time()
        table_name = os.path.splitext(file)[0]
        csv_path = os.path.join(folder_path, file)

        print(f"Loading {csv_path} -> table [{table_name}]")

        df = pd.read_csv(csv_path)

        df = df.apply(
            lambda col: col.astype(str).str.strip()
            if col.dtype == object else col
        )

        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=1000,
            #method="multi"  
        )
        end=time.time()
        log_event(f"Loaded {file}", start, end)
        print(f"✅ Ingested {file} into [{table_name}]")

folder = r"Your folder location"   # e.g. r"C:\Users\you\vendor_project\data"
ingest_folder_to_mssql(folder)



