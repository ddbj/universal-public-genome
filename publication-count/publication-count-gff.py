import os
import argparse
import subprocess
import zipfile
import sqlite3
import requests
import configparser
import shutil
from string import Template
from io import TextIOWrapper
from Bio import SeqIO

# Get necessary configuration values from config.ini
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.ini")
config = configparser.ConfigParser()
config.read(config_path)
db_file = config["config"]["db_file"]
working_dir = config["config"]["working_dir"]
dataset_file = f"{working_dir}/{config["config"]["ncbi_dataset_zip_file"]}"

datasets_tool_path = shutil.which("datasets")
if not datasets_tool_path:
    # Use the path from config.ini if 'datasets' is not found in system PATH
    datasets_tool_path = config["config"]["datasets_tool_path"]

# Configure the parser to receive Assembly Accession input
parser = argparse.ArgumentParser(description="Create literature frequency information for each genome")
parser.add_argument(
    "-i", "--input",
    dest="assembly_accession",
    help="Assembly Accession",
    required=True
)
args = parser.parse_args()

# Execute command (download ncbi_dataset.zip in datasets)
cmd = [
        datasets_tool_path,
        "download",
        "genome",
        "accession",
        args.assembly_accession,
        "--include",
        "gbff"
    ]
subprocess.run(
    cmd,
    cwd=working_dir,
    check=True
)

# Path to the desired file in the ZIP
gbff_file = "ncbi_dataset/data/" + args.assembly_accession + "/genomic.gbff"

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

# SPARQL endpoint
endpoint_url = "https://rdfportal.org/pubchem/sparql"

sparql_template_path = os.path.join(script_dir, "publication-count.rq")
with open(sparql_template_path, "r", encoding="utf-8") as f:
    sparql_template = Template(f.read())

# Parse .gbff in ZIP file with Biopython
with zipfile.ZipFile(dataset_file, "r") as zf:
    with zf.open(gbff_file) as gbff_raw:
        gbff_text = TextIOWrapper(gbff_raw, encoding="utf-8")

        output_gff_records = []
        for record in SeqIO.parse(gbff_text, "genbank"):
            for feature in record.features:
                if feature.type == "CDS":
                    # String representation of Location (e.g., join(123..456,789..999), complement(...)) etc.)
                    location_str = str(feature.location)

                    # Get protein_id (may not exist)
                    protein_id = feature.qualifiers.get("protein_id", ["N/A"])[0]

                    print(f"Location: {location_str}")
                    print(f"Protein ID: {protein_id}")

                    # Changed to SQLite because it is time consuming
                    # cmd = "zcat < gene2accession.gz | grep " + protein_id
                    # result = subprocess.run(
                    #     cmd,
                    #     cwd=datasets_tool_path,
                    #     shell=True,
                    #     capture_output=True,
                    #     text=True
                    # )

                    # Execute SQL to get ncbigene conditional on protein_id
                    cur.execute(sql, (protein_id,))
                    row = cur.fetchone()
                    if row is not None:
                        ncbigene = row["gene_id"]
                        print(f"NCBI Gene ID: {ncbigene}")
                    else:
                        print(f"NCBI Gene ID: N/A")
                        print("------------------------------------------")
                        continue                        
                    
                    # Set parameter for SPARQL query
                    # TODO: Correct ncbigene to actual value
                    sparql = sparql_template.substitute(ncbigene=ncbigene)
                    # sparql = sparql_template.substitute(ncbigene="100125779")

                    # Set request parameter and header
                    params = {
                        "query": sparql
                    }
                    headers = {
                        "Accept": "application/sparql-results+json"
                    }

                    # Executed with a GET request
                    response = requests.get(endpoint_url, params=params, headers=headers)

                    # Display results retrieved in JSON
                    ref_count = "."
                    if response.status_code == 200:
                        bindings = response.json()["results"]["bindings"]

                        if not bindings:
                            print("No SPARQL results found.")
                        else:
                            for binding in bindings:
                                print(f"NCBI Gene URL: {binding["ncbigene"]["value"]}")
                                print(f"Ref Count: {binding["ref_count"]["value"]}")
                                ref_count = binding["ref_count"]["value"]
                    else:
                        print(f"Error: {response.status_code}")
                        print(response.text)

                    # Data preparation for GFF file output (contents tentative) ===========
                    start = int(feature.location.start) + 1  # GFF is 1-based
                    end = int(feature.location.end)
                    strand = "+" if feature.strand >= 0 else "-"
                    gene_symbol = feature.qualifiers.get("gene", [""])[0]
                    attributes = f"ID={ncbigene};Name={gene_symbol};protein_id={protein_id}"
                    output_gff_records.append({
                        "seqid": record.id,
                        "source": "Protein",
                        "type": "gene",
                        "start": start,
                        "end": end,
                        "score": ref_count,
                        "strand": strand,
                        "phase": 0,
                        "attributes": attributes,
                    })
                    # =====================================================================


                    print("------------------------------------------")

            # TODO: Delete in the official version.
            # FOR DEVELOPMENT ===========================================================================================
            # Only one record is processed to avoid overloading the SPARQL endpoint 
            break
            # ===========================================================================================================

conn.close()

# Output .gff (contents tentative) ====================================
output_gff_path = os.path.join(working_dir, "output.gff")
with open(output_gff_path, "w", encoding="utf-8") as gff:
    gff.write("##gff-version 3\n")
    for record in output_gff_records:
        gff.write("\t".join(map(str, [
            record["seqid"], 
            record["source"], 
            record["type"], 
            record["start"], 
            record["end"],
            record["score"], 
            record["strand"], 
            record["phase"], 
            record["attributes"]
        ])) + "\n")

print(f"GFF file output is complete. (content is tentative) Path: {output_gff_path}")
# =====================================================================
