import pandas as pd
import numpy as np
import os
import pyodbc
from sqlalchemy import create_engine,inspect,text , DECIMAL, Float, Integer,NVARCHAR
import urllib
import logging
import time


logging.basicConfig(filename="vendor_sales_summary_extract.log", level=logging.INFO,filemode="w", format="%(asctime)s - %(levelname)s - %(message)s")


server= r"SANJAY\BOSS" #r"DESKTOP-FI1PI5E\SHIVSHAKTI"
database="inv"
conn_str=(
    "DRIVER={ODBC DRIVER 17 FOR SQL SERVER};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"trusted_connection=yes"
    )
engine=create_engine(f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(conn_str)}" , 
                     connect_args={"use_setinputsizes": False},
                     fast_executemany=True,)
conn=engine.connect()




#'''This fn merges diff tables to consolidate into a single dataframe'''
def create_vendor_summary(conn):
    start=time.time()
        
    sql = """
        WITH freight_summ AS (
    SELECT VendorNumber,
           SUM(Freight) AS TotalFreightCost
    FROM vendor_invoice
    GROUP BY VendorNumber
    ),
    purchase_summ AS (
    SELECT 
        p.VendorNumber,
        p.VendorName,
        p.Brand,
        p.Description,
        p.PurchasePrice,
        pp.[Volume(in mL)] AS Volume,
        pp.Price AS ActualPrice,
        SUM(p.Quantity) AS TotalPurchasedQuantity,
        SUM(p.Dollars) AS TotalPurchasedDollars
    FROM purchases p
    JOIN purchase_prices pp
        ON p.Brand = pp.Brand
    WHERE p.PurchasePrice > 0
    GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, pp.Price,pp.[Volume(in mL)]
    ),
    sales_summ AS (
    SELECT 
        VendorNo,
        Brand,
        SUM(SalesQuantity) AS TotalSalesQuantity,
        SUM(SalesDollars) AS TotalSalesDollars,
        SUM(SalesPrice) AS TotalSalesPrice,
        SUM(ExciseTax) AS TotalExciseTax
    FROM sales 
    GROUP BY VendorNo, Brand
    )
    SELECT 
    ps.VendorNumber,
    ps.VendorName,
    ps.Brand,
    ps.Description,
    ps.PurchasePrice AS TotalUnitPurchasePrice,
    ps.ActualPrice,
    ps.Volume,
    ps.TotalPurchasedQuantity,
    ps.TotalPurchasedDollars,
    ss.TotalSalesQuantity,
    ss.TotalSalesDollars,
    ss.TotalSalesPrice,
    ss.TotalExciseTax,
    fs.TotalFreightCost
    FROM purchase_summ ps
    LEFT JOIN sales_summ ss
    ON ps.VendorNumber = ss.VendorNo
    AND ps.Brand = ss.Brand
    LEFT JOIN freight_summ fs
    ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchasedDollars DESC;

    """
    Vendor_summary =pd.read_sql_query(sql,conn)
    end=time.time()
        # print(df, df.dtypes,sep='\n')
    print(f"Time taken to extract the dataframe: {round(end-start,3)}sec")
    return Vendor_summary


#'''This fn Cleans the extracted vendor dataframe'''
def vendor_summary_cleaning(Vendor_summary):
    #Replaces all NaN(nulls) with a 0
    Vendor_summary.fillna(0)

    #Converts the Volume col datatype into numeric type
    Vendor_summary["Volume"]=pd.to_numeric(Vendor_summary["Volume"],errors="coerce")

    #Trims all the leading and trailing whitespaces
    Vendor_summary["Description"]=Vendor_summary["Description"].str.lstrip()
    Vendor_summary["VendorName"]= Vendor_summary["VendorName"].str.lstrip()

    #creating new columns for ease of analysis
    Vendor_summary['GrossProfit'] =Vendor_summary['TotalSalesDollars'] - Vendor_summary['TotalPurchasedDollars']
    Vendor_summary['ProfitMarginPercent'] = (Vendor_summary["GrossProfit"] * 100)/ Vendor_summary["TotalSalesDollars"]
    Vendor_summary['Inventory'] = Vendor_summary['TotalPurchasedQuantity'] - Vendor_summary['TotalSalesQuantity']
    Vendor_summary['StockTurnover'] = Vendor_summary['TotalSalesQuantity']/Vendor_summary['TotalPurchasedQuantity']
    Vendor_summary['SalesPurchaseRatio'] = Vendor_summary['TotalSalesDollars'] / Vendor_summary['TotalPurchasedDollars']
    return Vendor_summary

#"""Adds cols in the resultant dataframe"""
def ingest_vendor_summary(final_df,engine,conn):
    from sqlalchemy.types import DECIMAL, Float, Integer, NVARCHAR

def ingest_vendor_summary(final_df, engine, conn):
    try:
        dtype = {
            "VendorNumber": Integer(),
            "VendorName": NVARCHAR(length=200),
            "Brand": Integer(),
            "Description": NVARCHAR(length=400),
            "TotalUnitPurchasePrice": DECIMAL(18, 4),
            "ActualPrice": DECIMAL(18, 4),
            "Volume": DECIMAL(10, 3),
            "TotalPurchasedQuantity": Integer(),
            "TotalPurchasedDollars": DECIMAL(18, 2),
            "TotalSalesQuantity": Integer(),
            "TotalSalesDollars": DECIMAL(18, 2),
            "TotalSalesPrice": DECIMAL(18, 2),
            "TotalExciseTax": DECIMAL(18, 2),
            "TotalFreightCost": DECIMAL(18, 2),
            "GrossProfit": DECIMAL(18, 2),
            "ProfitMarginPercent": DECIMAL(18, 4),
            "Inventory": Integer(),
            "StockTurnover": DECIMAL(18, 4),
            "SalesPurchaseRatio": DECIMAL(18, 4),
        }
    #     for col in dtype.keys():
    #      print(col, final_df[col].dtype)
    # # show problematic values
    #      bad = final_df[pd.to_numeric(final_df[col], errors="coerce").isna() & final_df[col].notna()]
    #      if not bad.empty:
    #          print("Bad values in", col)
    #          print(bad[col].head(10))
    #          print(final_df.dtypes)   

    #     final_df.to_sql(
    #         "vendor_sales_summary",
    #         con=engine,
    #         if_exists="replace",
    #         index=False,
    #         dtype=dtype,
    #     )
        conn.execute(text("""
            ALTER TABLE vendor_sales_summary
            ALTER COLUMN VendorNumber INT NOT NULL;
        """))

        conn.execute(text("""
            ALTER TABLE vendor_sales_summary
            ALTER COLUMN Brand NVARCHAR(100) NOT NULL;
        """))

        conn.execute(text("""
            ALTER TABLE vendor_sales_summary
            ADD CONSTRAINT PK_vendor_sales_summary
            PRIMARY KEY (VendorNumber, Brand);
        """))
    except Exception:
        logging.exception("Ingestion Needs Attention!")
        raise

if __name__== "__main__" :
        pd.set_option("display.width",os.get_terminal_size().columns)
        pd.set_option("display.max_columns", None)

        start=time.time()
        logging.info("Extracting the Vendor Summary Table...")
        Vendor_summary=create_vendor_summary(conn)
        end=time.time()
        logging.info(f"Vendor_summary created in {round(end-start,3)} seconds")
        logging.info(Vendor_summary.head(5))


        logging.info("Cleaning the Vendor Summary Table...")
        start=time.time( )
        final_df=vendor_summary_cleaning(Vendor_summary)
        end=time.time()
        logging.info(f"Vendor_summary cleaned in {round(end-start,3)} seconds")
        logging.info(final_df.head(5))

        logging.info("Ingesting the Cleaned data...")
        start=time.time()
        ingest_vendor_summary(final_df,engine,conn)
        end=time.time()
        logging.info(f"Completed ingestion in {round(end-start,3)} seconds!")
        print("Completed!")