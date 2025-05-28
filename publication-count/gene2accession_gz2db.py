import os
import sys
import gzip
import sqlite3
import configparser

config = configparser.ConfigParser()
config.read("config.ini")

gz_file = config["config"]["gz_file"]
db_file = config["config"]["db_file"]

# Check if the database file already exists
if os.path.exists(db_file):
    print(f"Database file already exists: {db_file}")
    sys.exit(1)  # Exit with non-zero code (treat as error)

# Connect to the database and create a cursor
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Begin a transaction
conn.execute("BEGIN")

# Create the table
cursor.execute("""
CREATE TABLE accession (
    tax_id TEXT,
    gene_id TEXT,
    status TEXT,
    rna_nucl_accession TEXT,
    rna_nucl_gi TEXT,
    protein_accession TEXT,
    protein_gi TEXT,
    genomic_nucl_accession TEXT,
    genomic_nucl_gi TEXT,
    start_position TEXT,
    end_position TEXT,
    orientation TEXT,
    assembly TEXT,
    mature_peptide_accession TEXT,
    mature_peptide_gi TEXT,
    symbol TEXT
)
""")

# Create an index on the protein_accession column
cursor.execute("CREATE INDEX IF NOT EXISTS idx_protein_accession ON accession(protein_accession)")

# Read and insert data from the gzipped file
with gzip.open(gz_file, "rt") as gz_file:
    for line in gz_file:
        if line.startswith("#"):
            continue
        fields = line.strip().split("\t")
        if len(fields) == 16:
            cursor.execute("INSERT INTO accession VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", fields)

# Commit the transaction
conn.commit()