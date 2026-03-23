import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind
import scipy.stats as stats
from sqlalchemy import text,create_engine

pd.set_option("display.max_rows",None)
pd.set_option("display.max_columns",None)

# creating db connection
engine=create_engine(r"mssql+pyodbc://@your_server/inv?DRIVER=ODBC DRIVER 17 FOR SQL SERVER&Trusted+Connection=Yes")

#Loading the dataframe
df= pd.read_sql_query("SELECT * FROM vendor_sales_summary",engine)
# print(df.head(20))
# print(df.describe().T)
# print(df.dtypes)

#"""EXPLORATORY DATA ANALYSIS"""
# Previously we examined various tables in the databas,identified key variable,understood their relationships,
# and finalised the ones to include in the final analysis
# In this phase of the EDA we will explore the resultnt table to gain insights from the individual columns.
# This will enable to find data patterns and identify anomalies,ensure data quality before proceeding for
#  further analyses


# Distribution plots for numerical columns
numerical_cols= df.select_dtypes(include=np.number).columns



# Gross profit: Min value is... indicating losses.Some produccts/transactions might be sold at a loss 
# due to high costs orselling at a discount lower than the purchase price.
# ProfitMargin : has a min value of -2.802712e+06 indicating very high purchase price compared to the
# sales and revenue is low
# TotalSalesQty and TotalSalesDollars: have min values 0, indicating slow moving or obsolete stock

# OUTLIERS INDICATED BY HIGH DEVIATIONS:
# Purchase and Actual Prices: The max ActualPrice and total purchase price in Dollars
# (7.499990e+03, 1.584606e+06) is >> than the mean( 32.188422 ,15786.558580) indicating potential 
# premium proucts
# freight cost : has vast deviation from 2.700000e-01 to 2.570321e+05 suggests logistic ineficiencies
# or bulk shipments
# StockTurnover: Ranges form 0 to 102, implying some products sell extremely fast while otherrs remain
#  in stock indefinitely.
# Value>1 indiactes sold qty is greater than purchased qty for the product perhaps due to qty being sold
# from older stock


df_analyse=pd.read_sql_query("""SELECT * FROM vendor_sales_summary
                             WHERE GrossProfit>0 AND ProfitMarginPercent>0 AND TotalSalesQuantity>0""",engine)

# print(df_analyse)
numerical_cols= df_analyse.select_dtypes(include=np.number).columns

# plt.figure(figsize=(15,10))
# for i,col in enumerate(numerical_cols):
#     plt.subplot(4,4,i+1) #Adjust grid layout as needed
#     sns.histplot(df_analyse[col], kde=True, bins=30)
#     plt.suptitle(f"Numerical col distributions")       
#     # plt.title(col)
# plt.tight_layout(rect=[0, 0, 1, 0.95])
# plt.show()


# # Distribution plots for numerical columns
plt.figure(figsize=(15,10))
for i,col in enumerate(numerical_cols):
    plt.subplot(4,4,i+1) #Adjust grid layout as needed
    sns.boxplot(df_analyse[col])
    plt.suptitle(f"Numerical col distributions")       
    # plt.title(col)
plt.tight_layout(rect=[0, 0, 1, 0.95]) #rect=[left, bottom, right, top]         
plt.show()



# #Count plot for categorical cols(aiding in vendors and prod insights)
categorical_cols= ['VendorName', 'Description']
plt.figure(figsize=(12,5))
for i,col in enumerate(categorical_cols): #for i,col in enumerate(numerical_cols):
    plt.subplot(1,2,i+1) #Adjust grid layout as needed #ValueError: num must be an integer with 1 <= num <= 2, not 3 occuring due tp numerical_cols being called as limit i for looop
    sns.countplot(y=df_analyse[col], order=df_analyse[col].value_counts().index[:10]) #top 10
    plt.suptitle(f"CountPlot of Categories")      
    plt.title(f"CountPlot of {col}") 
    # plt.title(col)
plt.tight_layout(rect=[0, 0, 1, 0.95]) #rect=[left, bottom, right, top]         
plt.show()


#Correlation Heatmap
plt.figure(figsize=(12,8))
correlation_matrix=df_analyse[numerical_cols].corr()
sns.heatmap(correlation_matrix,annot=True, fmt=".3f", cmap='coolwarm', linewidth=0.5)
plt.title("Correlation Heatmap")
plt.show()

# Purchase Price has weak correlation with gross_profit_margin(-0.01) and TotalsalesDollars(0.004),suggesting tat price variatins do not impact the sales revenue or profit
# Purchased quantity has strong correlationwith inventory(.06) and negative high correlation with stockTurnover(-0.05)
# TotalsalesPrice has direct +ve correlation with ExciseTax
# Inventory has direct and low correlation with Volume(0.12)
# Strong +ve correlation between pucrchased and salesQuantity(0.9) signalling efficient inventory turnover
# High +ve Correlation between Total Sales Dollars and TotalSalesPrice(0.8)
# StockTurnover has high direct correlation with SalesPurchaseRatio and profitMargin(0/0.5)indicating higher profitability 

# TotalSalesPrice has weak correlation with GrossProfit and Profitmargin, indicating that Profit is not necessarily high with  increasing sales,,indiicating cerrtaain products have  premium pricing that affects the profits
# print(df_analyse['Description'].value_counts())



#BUSINESS PROBLEM

# Q1 Identify Brands that need promotional or pricing adjustments that exhibit lower sales performance but higher profit margins

brand_performance= df_analyse.groupby('Description').aggregate({'TotalSalesDollars': 'sum', 'ProfitMarginPercent': 'mean'}).reset_index()
# brand_performance=brand_performance[brand_performance['TotalSalesDollars']<5000] #just for better visualization

low_sales_threshold = brand_performance['TotalSalesDollars'].quantile(.15)
high_margin_threshold = brand_performance['ProfitMarginPercent'].quantile(.85)
print(low_sales_threshold, high_margin_threshold)

#filtering brands with low sales and high margin threshold based on above logic 
target_brands=brand_performance[
    (brand_performance['TotalSalesDollars'] <=low_sales_threshold) &
    (brand_performance['ProfitMarginPercent']>=high_margin_threshold)
    ]
# print(target_brands)
plt.figure(figsize=(10,6))
sns.scatterplot(data=brand_performance, x='TotalSalesDollars', y='ProfitMarginPercent', color='blue', label='All Brands', alpha=.2)
sns.scatterplot(data=target_brands,x='TotalSalesDollars', y='ProfitMarginPercent', color='red', label='Target Brands')

plt.axhline(high_margin_threshold, linestyle="--" , color='black', label="High Margin Threshold")
plt.axvline(low_sales_threshold, linestyle="--" , color='black', label="Low Sales Threshold")

plt.ylabel('ProfitMargin %')
plt.xlabel('Total Sales $')
plt.legend()
plt.grid(True)
plt.show()


# # Q2 Which brands and vendor show highest sales performance

#fn to format the output of Vendor and Brand Sales
def format_dollar(value):
    if value>= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    if value >1000:
        return f"{value/1000:.2f}K"
    else:
        return str(value)
    

# # Top vendors and brands by sales performance
top_vendors = df_analyse.groupby("VendorName")['TotalSalesDollars'].sum().nlargest(10)
top_brands = df_analyse.groupby("Description")['TotalSalesDollars'].sum().nlargest(10)
print(top_vendors.apply(lambda x: format_dollar(x)), top_brands.apply(lambda x: format_dollar(x)))

# Plots for top Vendors andTop brands

plt.subplot(1,2,1)
ax1= sns.barplot(y=top_vendors.index,x= top_vendors.values, palette='Blues_r' )
plt.title("Top 10 Vendors by sale")
for bar in ax1.patches:
    ax1.text(bar.get_linewidth() + (bar.get_linewidth()*.02), 
             bar.get_y() + bar.get_height()/2,
              format_dollar(bar.get_linewidth()),
               ha='left', va='center',fontsize=10, color= 'black' )


plt.subplot(1,2,1)
ax1= sns.barplot(y=top_brands.index.astype(str),x= top_brands.values, palette='Reds_r' )
plt.title("Top 10 Brands by sale")
plt.tight_layout()
plt.show()

# Q3 Which vendors contribute most to the total Purchased Dollars?

vendor_contribution=df_analyse.groupby('VendorName').agg({
    'TotalPurchasedDollars': 'sum' ,
    'TotalSalesDollars': 'sum',
    'GrossProfit': 'sum'}).reset_index()

vendor_contribution['PurchasedContribution%'] = (vendor_contribution['TotalPurchasedDollars']/vendor_contribution['TotalPurchasedDollars'].sum()).round(3)
top_10_vendors = vendor_contribution.head(10)
top_10_vendors['TotalPurchasedDollars'] = top_10_vendors['TotalPurchasedDollars'].apply( lambda x: format_dollar(x) )
top_10_vendors['TotalSalesDollars'] = top_10_vendors['TotalSalesDollars'].apply( lambda x: format_dollar(x) )
top_10_vendors['GrossProfit'] = top_10_vendors['GrossProfit'].round(2).apply( lambda x: format_dollar(x) )




# Q4 How much of the total procurement is dependent on top vendors
top_10_vendors['PurchasedContri_cum_sum'] = top_10_vendors['PurchasedContribution%'].cumsum().round(3)
# print(f"total purchcase contribution of top 10 vendorts is : {round(top_10_vendors['PurchasedContribution%'].sum(),2)} %")


#Q5 Does purchasing in bulk reduce the unit price? What is the optimal purchase volume for cost savings?
# approach: create rough unit prices based on purchase size; compare based on Order size 
df_analyse['UnitPurchasePrice'] = df_analyse['TotalPurchasedDollars']/ df_analyse['TotalPurchasedQuantity']
df_analyse['OrderSize'] = pd.qcut(df_analyse['TotalPurchasedQuantity'], q=3,  labels=["Small", "Medium", "Large"])
print(df_analyse.groupby(['OrderSize'])['UnitPurchasePrice'].mean())
# plt.figure(figsize=(15,10))
# sns.boxplot(x=df_analyse['OrderSize'], y= df_analyse['UnitPurchasePrice'])
# plt.suptitle(f"OrderSize Outliers")       
#     # plt.title(col)
# plt.tight_layout(rect=[0, 0, 1, 0.95]) #rect=[left, bottom, right, top]         
# plt.show()

# Vendors buying in bulk(large Order size) get the lowest avg unit prices($ 11.24) i.e higher margins if they maintain inventory efficiently
# The price difference between large and small ordersize is substantial(~ 72% reduction in unit cost)
# The above proves that bulk strategy aids in 



# Q6 Which vendors have low inventory turnover, indicating excess stock and slow-moving products   
print(df_analyse[df_analyse['StockTurnover']<1].groupby('VendorName')['StockTurnover'].mean().sort_values(ascending=True))
plt.figure(figsize=(15,10))
sns.boxplot(x=df_analyse['VendorName'], y=df_analyse['StockTurnover'])
plt.suptitle(f"Stock Turnover Per Vendor")
plt.show()

# Q7 How much inventory is locked in unsold inventory per vendor, which vendors contribute the most to it
unsold_capital= (df_analyse['TotalPurchasedQuantity'] - df_analyse['TotalSalesQuantity']) * df_analyse['UnitPurchasePrice']


# Q8 what is 95% confidence interval for profit margins top and low performing vendors
top_threshold = df_analyse['TotalSalesDollars'].quantile(.75)
low_threshold = df_analyse['TotalSalesDollars'].quantile(.15)

top_vendors= df_analyse[df_analyse['TotalSalesDollars'] >= top_threshold]['TotalSalesDollars'].dropna()
low_vendors = df_analyse[df_analyse['TotalSalesDollars'] <= low_threshold]['TotalSalesDollars'].dropna()

def confidence_interval(data, confidence= .95):
    mean_val=np.mean(data)
    std_error=np.std(data,ddof=1)/np.sqrt(len(data))
    t_critical = stats.t.ppf((1+confidence)/2 , df= len(data)-1)
    error_margin = t_critical*std_error
    return mean_val, mean_val-error_margin, mean_val+error_margin

# ── Compute confidence intervals ─────────────────────────────────
top_mean, top_lower, top_upper = confidence_interval(top_vendors)
low_mean, low_lower, low_upper = confidence_interval(low_vendors)

print(f"Top Vendors 95% CI: ({top_lower:.2f}, {top_upper:.2f}), Mean: {top_mean:.2f}")
print(f"Low Vendors 95% CI: ({low_lower:.2f}, {low_upper:.2f}), Mean: {low_mean:.2f}")


plt.figure(figsize=(12, 6))

# Top Vendors distribution
sns.histplot(top_vendors, kde=True, color="blue", bins=30,
             alpha=0.5, label="Top Vendors")
plt.axvline(top_lower, color="blue", linestyle="--",
            label=f"Top Lower: {top_lower:.2f}")
plt.axvline(top_upper, color="blue", linestyle="--",
            label=f"Top Upper: {top_upper:.2f}")
plt.axvline(top_mean,  color="blue", linestyle="-",
            label=f"Top Mean:  {top_mean:.2f}")

# Low Vendors distribution
sns.histplot(low_vendors, kde=True, color="red", bins=30,
             alpha=0.5, label="Low Vendors")
plt.axvline(low_lower, color="red", linestyle="--",
            label=f"Low Lower: {low_lower:.2f}")
plt.axvline(low_upper, color="red", linestyle="--",
            label=f"Low Upper: {low_upper:.2f}")
plt.axvline(low_mean,  color="red", linestyle="-",
            label=f"Low Mean:  {low_mean:.2f}")

plt.title("95% Confidence Interval — Stock Turnover: Top vs Low Vendors")
plt.xlabel("Stock Turnover")
plt.ylabel("Frequency")
plt.legend()
plt.tight_layout()
plt.show()

 ## What Each Part Does

# | Component | Purpose |
# |---|---|
# | `stats.sem()` | Standard error of mean — measures how precisely the mean is estimated |
# | `stats.t.interval()` | t-distribution CI — more accurate than z-distribution for real datasets |
# | `df=len(data)-1` | Degrees of freedom — accounts for sample size |
# | `axvline` solid `-` | Mean of the distribution |
# | `axvline` dashed `--` | Lower and upper CI bounds |
# | `kde=True` | Smooth density curve overlaid on histogram |


# If the two CI ranges DON'T overlap → statistically significant difference
# If they DO overlap               → difference may be due to chance
