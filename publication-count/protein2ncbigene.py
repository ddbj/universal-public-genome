import os
import argparse
import sqlite3
import configparser

# Get necessary configuration values from config.ini
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.ini")
config = configparser.ConfigParser()
config.read(config_path)
db_file = config["config"]["db_file"]

# Configure the parser to receive Assembly Accession input
parser = argparse.ArgumentParser(description="Refer to gene2accession and display NCBI GeneID obtained subject to protein ID")
parser.add_argument(
    "-i", "--input",
    dest="protein_id",
    help="Protein ID",
    required=True
)
args = parser.parse_args()

# Connect to database
conn = sqlite3.connect(db_file)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# SQL to get ncbigene conditional on protein_id
sql = """
    SELECT gene_id
    FROM accession
    WHERE protein_accession = ?
"""

# Execute SQL to get ncbigene conditional on protein_id
cur.execute(sql, (args.protein_id,))
row = cur.fetchone()
if row is not None:
    ncbigene = row["gene_id"]
    print(f"NCBI Gene ID: {ncbigene}")
else:
    print(f"NCBI Gene ID: N/A")
