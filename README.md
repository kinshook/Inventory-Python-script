
AIM: 
1)Collect and ingest the required dataset into a single place, like a database(in our case).
2) Extract only the meaningful data from the pool of the database.
3) Explore, refine, and clean the extracted dataset and then upload it to the database
4) Perform EDA on the cleaned analysis-ready dataset using statistical and graphical tools and answer the required questions.
5) Use the EDA insights to visualize them.

# Vendor Performance Analyses
The [load_CSV data for EDA-SQL inventory.py ](https://github.com/kinshook/Inventory-Python-script/commit/5edd3e1ac01be3bb2b571fa00f3ad008ce97b77e)ingests all the .csv files from the local device to a database(MSSQL in this case).

ETL and EDA of inventory:
To perform accurate analyses, we run an ETL process to extract relevant data from the dataset, clean and transform it, and reinsert it into the database for easy access by stakeholders. The cleaning script is attached as [vendor_sales_summary_db.py](https://github.com/kinshook/Inventory-Python-script/blob/main/vendor_sales_summary_db.py) along with the KPIs.

After ingesting the consolidated dataset vendor_sales_summary into the database, the statistical representation and variable relationships are analyzed using EDA. To answer relevant KPI and business questions, we break down the dataset and perform the required operations and graphical plots.

The Dashboard report and detailed analysis can be viewed here [Vendor Performance Dashboard](https://github.com/kinshook/Inventory-Python-script/blob/main/Vendor%20Performance%20Analysis.pbix)
