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

# pubchem SPARQL endpoint
endpoint_url_pubchem = "https://rdfportal.org/pubchem/sparql"

sparql_path_pubchem = os.path.join(script_dir, "publication-count-pubchem.rq")
with open(sparql_path_pubchem, "r", encoding="utf-8") as f:
    sparql_template_pubchem = Template(f.read())

# pubtator SPARQL endpoint
endpoint_url_pubtator = "https://rdfportal.org/ncbi/sparql"

sparql_path_pubtator = os.path.join(script_dir, "publication-count-pubtator.rq")
with open(sparql_path_pubtator, "r", encoding="utf-8") as f:
    sparql_template_pubtator = Template(f.read())

print("Obtaining counts of publications that mention genes...")

# Parse .gbff in ZIP file with Biopython
with zipfile.ZipFile(dataset_file, "r") as zf:
    with zf.open(gbff_file) as gbff_raw:
        gbff_text = TextIOWrapper(gbff_raw, encoding="utf-8")
        output_gff_records = []
        cnt=0 
        for record in SeqIO.parse(gbff_text, "genbank"):
            for feature in record.features:
                if feature.type == "CDS":
                    # String representation of Location (e.g., join(123..456,789..999), complement(...)) etc.)
                    location_str = str(feature.location)

                    # Get protein_id (may not exist)
                    protein_id = feature.qualifiers.get("protein_id", ["N/A"])[0]

                    # print(f"Location: {location_str}")
                    # print(f"Protein ID: {protein_id}")

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
                        # print(f"NCBI Gene ID: {ncbigene}")
                    else:
                        # print(f"NCBI Gene ID: N/A")
                        # print("------------------------------------------")
                        continue                        
                    
                    # Retrieve data from PubChem cooccurrence via SPARQL ==================
                    # Set parameter for SPARQL query
                    sparql = sparql_template_pubchem.substitute(ncbigene=ncbigene)
                    # sparql = sparql_template_pubchem.substitute(ncbigene="100125779")

                    # Set request parameter and header
                    params = {
                        "query": sparql
                    }
                    headers = {
                        "Accept": "application/sparql-results+json"
                    }

                    # Executed with a GET request
                    response_pubchem = requests.get(endpoint_url_pubchem, params=params, headers=headers)

                    # Display results retrieved in JSON
                    ref_count_pubchem = 0
                    if response_pubchem.status_code == 200:
                        bindings = response_pubchem.json()["results"]["bindings"]

                        # if not bindings:
                        #     print("No SPARQL results found.")
                        # else:
                        if bindings:
                            for binding in bindings:
                                # print(f"NCBI Gene URL: {binding["ncbigene"]["value"]}")
                                # print(f"Ref Count: {binding["ref_count"]["value"]}")
                                ref_count_pubchem = int(binding["ref_count"]["value"])
                    else:
                        print(f"Error: {response_pubchem.status_code}")
                        print(response_pubchem.text)
                    # =====================================================================

                    # Retrieve data from PubTator Central via SPARQL ======================
                    sparql = sparql_template_pubtator.substitute(ncbigene=ncbigene)
                    # sparql = sparql_template_pubtator.substitute(ncbigene="26131688")

                    # Set request parameter and header
                    params = {
                        "query": sparql
                    }
                    headers = {
                        "Accept": "application/sparql-results+json"
                    }

                    # Executed with a GET request
                    response_pubtator = requests.get(endpoint_url_pubtator, params=params, headers=headers)


                    # Display results retrieved in JSON
                    ref_count_pubtator = 0
                    if response_pubtator.status_code == 200:
                        bindings = response_pubtator.json()["results"]["bindings"]
                        # if not bindings:
                        #     print("No SPARQL results found.")
                        # else:
                        if bindings:
                            for binding in bindings:
                                # print(f"NCBI Gene URL: {binding["geneId"]["value"]}")
                                # print(f"Ref Count: {binding["refCount"]["value"]}")
                                ref_count_pubtator = int(binding["refCount"]["value"])
                    else:
                        print(f"Error: {response_pubtator.status_code}")
                        print(response_pubtator.text)

                    if ref_count_pubchem + ref_count_pubtator == 0:
                        ref_count = "."
                    else:
                        ref_count = ref_count_pubchem + ref_count_pubtator
                    # =====================================================================

                    # Data preparation for GFF file output (contents tentative) ===========
                    start = int(feature.location.start) + 1  # GFF is 1-based
                    end = int(feature.location.end)
                    strand = "+" if feature.strand >= 0 else "-"
                    # gene_symbol = feature.qualifiers.get("gene", [""])[0]
                    attributes = f"ID={ncbigene};protein_id={protein_id}"
                    output_gff_records.append({
                        "seqid": record.id,
                        "source": "RefSeq",
                        "type": "gene",
                        "start": start,
                        "end": end,
                        "score": ref_count,
                        "strand": strand,
                        "phase": ".",
                        "attributes": attributes,
                    })
                    # =====================================================================


                    # print("------------------------------------------")

            # TODO: Delete in the official version.
            # FOR DEVELOPMENT ===========================================================================================
            # Limit to 10 records for easier development checks
            cnt+=1
            if cnt > 10:
                break
            # ===========================================================================================================

conn.close()

print("Writing results to GFF file...")

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
