import pandasai as pai
import sqlite3
import pandas as pd
import os

# Set API key
pai.api_key.set("YOUR_API_KEY")

db_path = os.path.join('..', 'pii_scan_history.db')

conn = sqlite3.connect(db_path)

# Query the scan_history table
pandas_df = pd.read_sql_query("SELECT * FROM scan_history", conn)

# Close the connection
conn.close()

# Convert pandas DataFrame to PandaAI DataFrame
df = pai.DataFrame(pandas_df)

# Save your dataset configuration
dataset = pai.create(
    path="pai-personal-6a9b7/vbr-pii-scanner", 
    df=df,  # Pass the DataFrame here
    description="PII Scanner for Veeam"
)

# Push your dataset to PandaBI
dataset.push()