import pandas as pd
import numpy as np
import os
import pyodbc
from sqlalchemy import create_engine, text, DECIMAL, Integer, NVARCHAR
import urllib
import logging
import time

logging.basicConfig(
    filename="vendor_sales_summary_extract.log",
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

server   = r"SANJAY\BOSS"
database = "inv"

conn_str = (
    "DRIVER={ODBC DRIVER 17 FOR SQL SERVER};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "trusted_connection=yes"
)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(conn_str)}",
    connect_args={"use_setinputsizes": False},
    fast_executemany=True,
)

  


def create_vendor_summary(engine):
    start = time.time()

    sql = """
    WITH freight_summ AS (
        SELECT
            VendorNumber,
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
            pp.[Volume(in mL)]  AS Volume,
            pp.Price            AS ActualPrice,
            SUM(p.Quantity)     AS TotalPurchasedQuantity,
            SUM(p.Dollars)      AS TotalPurchasedDollars
        FROM purchases p
        JOIN purchase_prices pp
            ON 
             p.VendorNumber  = pp.VendorNumber      
             AND p.Brand  = pp.Brand
             AND p.Description   = pp.Description       

        WHERE p.PurchasePrice > 0
        GROUP BY
            p.VendorNumber, p.VendorName, p.Brand,
            p.Description, p.PurchasePrice,
            pp.Price, pp.[Volume(in mL)]
    ),

    sales_summ AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesQuantity)  AS TotalSalesQuantity,
            SUM(SalesDollars)   AS TotalSalesDollars,
            SUM(SalesPrice)     AS TotalSalesPrice,
            SUM(ExciseTax)      AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )

    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice        AS TotalUnitPurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchasedQuantity,
        ps.TotalPurchasedDollars,
        ISNULL(ss.TotalSalesQuantity, 0)    AS TotalSalesQuantity,   -- handle NULLs in SQL
        ISNULL(ss.TotalSalesDollars,  0)    AS TotalSalesDollars,
        ISNULL(ss.TotalSalesPrice,    0)    AS TotalSalesPrice,
        ISNULL(ss.TotalExciseTax,     0)    AS TotalExciseTax,
        ISNULL(fs.TotalFreightCost,   0)    AS TotalFreightCost
    FROM purchase_summ ps
    LEFT JOIN sales_summ ss
        ON  ps.VendorNumber = ss.VendorNo
        AND ps.Brand        = ss.Brand
    LEFT JOIN freight_summ fs
        ON  ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchasedDollars DESC;
    """

    with engine.connect() as conn:
        df = pd.read_sql_query(sql, conn)

    elapsed = round(time.time() - start, 3)
    logging.info(f"Extracted {len(df)} rows in {elapsed}s")
    print(f"Extracted {len(df)} rows in {elapsed}s")
    return df



def vendor_summary_cleaning(df):

    # FIX: fillna must be assigned back (was a no-op before)
    df = df.fillna(0)

    # Type coercion
    df["Volume"]      = pd.to_numeric(df["Volume"],      errors="coerce").fillna(0)
    df['VendorNumber'] = df['VendorNumber'].astype(str)
    df['Brand'] = df['Brand'].astype(str)

    # Strip whitespace
    df["Description"] = df["Description"].str.strip()
    df["VendorName"]  = df["VendorName"].str.strip()

    # KPIs 
    df["GrossProfit"] = df["TotalSalesDollars"] - df["TotalPurchasedDollars"]

    # guard against division by zero was producing inf/NaN 
    df["ProfitMarginPercent"] = np.where(
        df["TotalSalesDollars"] != 0,
        (df["GrossProfit"] / df["TotalSalesDollars"]) * 100,
        0.0
    )

    df["Inventory"] = df["TotalPurchasedQuantity"] - df["TotalSalesQuantity"]

    df["StockTurnover"] = np.where(
        df["TotalPurchasedQuantity"] != 0,
        df["TotalSalesQuantity"] / df["TotalPurchasedQuantity"],
        0.0
    )

    df["SalesPurchaseRatio"] = np.where(
        df["TotalPurchasedDollars"] != 0,
        df["TotalSalesDollars"] / df["TotalPurchasedDollars"],
        0.0
    )

    # Replace any residual inf values (just in case)
    df.replace([np.inf, -np.inf], 0.0, inplace=True)

    logging.info(f"Cleaned dataframe shape: {df.shape}")
    return df



def ingest_vendor_summary(final_df, engine):
    dtype_map = {
        "VendorNumber":          NVARCHAR(10),
        "VendorName":            NVARCHAR(200),
        "Brand":                 NVARCHAR(10),
        "Description":           NVARCHAR(400),
        "TotalUnitPurchasePrice":DECIMAL(18, 4),
        "ActualPrice":           DECIMAL(18, 4),
        "Volume":                DECIMAL(10, 3),
        "TotalPurchasedQuantity":Integer(),
        "TotalPurchasedDollars": DECIMAL(18, 2),
        "TotalSalesQuantity":    Integer(),
        "TotalSalesDollars":     DECIMAL(18, 2),
        "TotalSalesPrice":       DECIMAL(18, 2),
        "TotalExciseTax":        DECIMAL(18, 2),
        "TotalFreightCost":      DECIMAL(18, 2),
        "GrossProfit":           DECIMAL(18, 2),
        "ProfitMarginPercent":   DECIMAL(18, 4),
        "Inventory":             Integer(),
        "StockTurnover":         DECIMAL(18, 4),
        "SalesPurchaseRatio":    DECIMAL(18, 4),
    }

    try:
        # FIX: to_sql was commented out — this is the ACTUAL ingestion step
        rows_written = final_df.to_sql(
            "vendor_sales_summary",
            con=engine,
            if_exists="replace",   # drops and recreates the table
            index=False
        )
        logging.info(f"to_sql wrote {rows_written} rows")
        print(final_df, f"to_sql wrote {rows_written} rows")

        # logging.info(f"to_sql wrote {final_df} rows")
        # print(f"to_sql wrote {final_df} rows")
        print(final_df['Description'].apply(lambda x: repr(x)))

        # Add Primary Key after table is created
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE vendor_sales_summary
                ALTER COLUMN VendorNumber NVARCHAR(10) NOT NULL;
            """))
            conn.execute(text("""
                ALTER TABLE vendor_sales_summary
                ALTER COLUMN Brand NVARCHAR(10) NOT NULL;
            """))
            # Drop PK if it already exists (idempotent re-runs)
            conn.execute(text("""
                IF EXISTS (
                    SELECT 1 FROM sys.key_constraints
                    WHERE name = 'PK_vendor_sales_summary'
                )
                ALTER TABLE vendor_sales_summary
                DROP CONSTRAINT PK_vendor_sales_summary;
            """))
            conn.execute(text("""
                ALTER TABLE vendor_sales_summary
                ADD CONSTRAINT PK_vendor_sales_summary
                PRIMARY KEY (VendorNumber, Brand);
            """))
            conn.commit()

        logging.info("Primary key applied successfully.")

    except Exception:
        logging.exception("Ingestion failed!")
        raise



if __name__ == "__main__":
    pd.set_option("display.width", os.get_terminal_size().columns)
    pd.set_option("display.max_columns", None)

    logging.info("── Step 1: Extracting ──")
    Vendor_summary = create_vendor_summary(engine)

    logging.info("── Step 2: Cleaning ──")
    final_df = vendor_summary_cleaning(Vendor_summary)

    logging.info("── Step 3: Ingesting ──")
    ingest_vendor_summary(final_df, engine)

    logging.info("── Step 4: Validating ──")
    validate_row_count(final_df, engine)

    print("Completed!")
