import os
import argparse
import subprocess
import zipfile
import sqlite3
import requests
import configparser
import shutil
import logging
import tempfile
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

# Configure logger
logger = logging.getLogger("error_logger")
logger.setLevel(logging.ERROR)

# Configure error log file
if not logger.handlers:
    file_handler = logging.FileHandler("error.log", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

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
    with zf.open(gbff_file) as gbff_raw, open("output_pubchem.gff", "w") as gff_pubchem, open("output_pubtator.gff", "w") as gff_pubtator:
        gbff_text = TextIOWrapper(gbff_raw, encoding="utf-8")

        # Write GFF3 version header
        gff_pubchem.write("##gff-version 3\n")
        gff_pubtator.write("##gff-version 3\n")

        for i, record in enumerate(SeqIO.parse(gbff_text, "genbank"), start=1):
            print(f"\rProcessing record #{i}" + " " * 30, flush=True)
            total_features = len(record.features)
            cds_counter = 0
            min_start = float("inf")
            max_end = float("-inf")

            # Write GFF body to a temporary file
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp_gff_pubchem, tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp_gff_pubtator:
                for j, feature in enumerate(record.features, start=1):
                    print(f"\r  → feature {j}/{total_features} in record", end="", flush=True)
                    if feature.type == "CDS":
                        cds_counter += 1
                        feature_id = f"{record.id}_{feature.type}_{cds_counter}"

                        # String representation of Location (e.g., join(123..456,789..999), complement(...)) etc.)
                        location_str = str(feature.location)
                        
                        # Get protein_id (may not exist)
                        protein_id = feature.qualifiers.get("protein_id", ["N/A"])[0]

                        start = int(feature.location.start) + 1  # GFF is 1-based
                        end = int(feature.location.end)
                        strand = "+" if feature.location.strand >= 0 else "-"
                        attributes = f"ID={feature_id};protein_id={protein_id}"

                        # Execute SQL to get ncbigene conditional on protein_id
                        cur.execute(sql, (protein_id,))
                        row = cur.fetchone()
                        if row is not None:
                            ncbigene = row["gene_id"]
                            attributes += f";ncbigene={ncbigene}"
                        else:
                            # Output to GFF file and go to next feature
                            gff_fields = [
                                record.id,        # seqid
                                "Reference",      # source
                                "gene",           # type
                                start,
                                end,
                                ".",              # score
                                strand,
                                ".",              # phase
                                attributes        # attributes
                            ]

                            tmp_gff_pubchem.write("\t".join(map(str, gff_fields)) + "\n")
                            tmp_gff_pubtator.write("\t".join(map(str, gff_fields)) + "\n")

                            min_start = min(min_start, start)
                            max_end = max(max_end, end)

                            continue
                        
                        # PubChem =============================================================
                        # Set parameter for SPARQL query
                        sparql = sparql_template_pubchem.substitute(ncbigene=ncbigene)
                        # sparql = sparql_template_pubchem.substitute(ncbigene="100125779")

                        # Set request parameter and header
                        params = {"query": sparql}
                        headers = {"Accept": "application/sparql-results+json"}

                        # Executed with a GET request
                        response_pubchem = requests.get(endpoint_url_pubchem, params=params, headers=headers)

                        # Extract results from SPARQL response
                        ref_count_pubchem = "0"
                        if response_pubchem.status_code == 200:
                            bindings = response_pubchem.json()["results"]["bindings"]
                            if bindings:
                                for binding in bindings:
                                    ref_count_pubchem = binding["ref_count"]["value"]
                        else:
                            # In case of error, output a "." to distinguish it from 0
                            ref_count_pubchem = "."
                            logger.error("SPARQL request failed: status_code=%d\nresponse_text=%s",
                                        response_pubchem.status_code, response_pubchem.text)

                        gff_fields = [
                            record.id,          # seqid
                            "Reference",        # source
                            "gene",             # type
                            start,
                            end,
                            ref_count_pubchem,  # score
                            strand,
                            ".",                # phase
                            attributes          # attributes
                        ]
                        tmp_gff_pubchem.write("\t".join(map(str, gff_fields)) + "\n")
                        # =====================================================================

                        # PubTator ============================================================
                        sparql = sparql_template_pubtator.substitute(ncbigene=ncbigene)
                        # sparql = sparql_template_pubtator.substitute(ncbigene="26131688")

                        # Set request parameter and header
                        params = {"query": sparql}
                        headers = {"Accept": "application/sparql-results+json"}

                        # Executed with a GET request
                        response_pubtator = requests.get(endpoint_url_pubtator, params=params, headers=headers)

                        # Extract results from SPARQL response
                        ref_count_pubtator = "0"
                        if response_pubtator.status_code == 200:
                            bindings = response_pubtator.json()["results"]["bindings"]
                            if bindings:
                                for binding in bindings:
                                    ref_count_pubtator = binding["refCount"]["value"]
                        else:
                            # In case of error, output a "." to distinguish it from 0
                            ref_count_pubtator = "."
                            logger.error("SPARQL request failed: status_code=%d\nresponse_text=%s",
                                        response_pubtator.status_code, response_pubtator.text)

                        gff_fields = [
                            record.id,          # seqid
                            "Reference",        # source
                            "gene",             # type
                            start,
                            end,
                            ref_count_pubtator, # score
                            strand,
                            ".",                # phase
                            attributes          # attributes
                        ]
                        tmp_gff_pubtator.write("\t".join(map(str, gff_fields)) + "\n")
                        # =====================================================================

                # Track min/max positions for sequence-region
                min_start = min(min_start, start)
                max_end = max(max_end, end)

                # Write sequence-region header line
                if min_start < float("inf") and max_end > float("-inf"):
                    gff_pubchem.write(f"##sequence-region {record.id} {min_start} {max_end}\n")
                    gff_pubtator.write(f"##sequence-region {record.id} {min_start} {max_end}\n")

                # Rewind and write the content of the temporary file to the final output
                tmp_gff_pubchem.seek(0)
                gff_pubchem.writelines(tmp_gff_pubchem.readlines())
                tmp_gff_pubtator.seek(0)
                gff_pubtator.writelines(tmp_gff_pubtator.readlines())

            # FOR DEVELOPMENT ===========================================================================================
            # Limit to 10 records for easier development checks
            # if i > 10:
            #     break
            # ===========================================================================================================

conn.close()

print()
print(f"Pubchem GFF file output is complete. Path: {os.path.join(working_dir, "output_pubchem.gff")}")
print(f"Pubtator GFF file output is complete. Path: {os.path.join(working_dir, "output_pubtator.gff")}")
