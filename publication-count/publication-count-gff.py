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

def load_config():
    """
    Load configuration values from 'config.ini' in the script directory.

    Returns:
        tuple: A tuple containing the configuration object and the script directory path.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.ini")
    config = configparser.ConfigParser()
    config.read(config_path)
    return config, script_dir

def setup_logger():
    """
    Set up a logger for error logging to 'error.log'.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger("error_logger")
    logger.setLevel(logging.ERROR)
    if not logger.handlers:
        file_handler = logging.FileHandler("error.log", encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def execute_sparql_query(endpoint_url, sparql_template, ncbigene):
    """
    Execute a SPARQL query by substituting the ncbigene value in the template.

    Args:
        endpoint_url (str): The URL of the SPARQL endpoint.
        sparql_template (Template): The SPARQL query template.
        ncbigene (str): The NCBI Gene ID to substitute into the query.

    Returns:
        requests.Response: The HTTP response from the SPARQL endpoint.
    """
    sparql = sparql_template.substitute(ncbigene=ncbigene)
    params = {"query": sparql}
    headers = {"Accept": "application/sparql-results+json"}
    return requests.get(endpoint_url, params=params, headers=headers)

def get_sparql_templates(script_dir):
    """
    Load SPARQL query templates for PubChem and PubTator.

    Args:
        script_dir (str): Path to the directory containing the script.

    Returns:
        tuple: A tuple containing two Template objects for PubChem and PubTator.
    """
    with open(os.path.join(script_dir, "publication-count-pubchem.rq"), "r", encoding="utf-8") as f:
        pubchem_template = Template(f.read())
    with open(os.path.join(script_dir, "publication-count-pubtator.rq"), "r", encoding="utf-8") as f:
        pubtator_template = Template(f.read())
    return pubchem_template, pubtator_template

def download_genome_zip(datasets_tool_path, accession, working_dir):
    """
    Download genome data from NCBI using the datasets command-line tool.

    Args:
        datasets_tool_path (str): Path to the datasets CLI tool.
        accession (str): NCBI Assembly accession ID.
        working_dir (str): Directory where the downloaded file should be saved.

    Raises:
        subprocess.CalledProcessError: If the datasets command fails.
    """
    cmd = [datasets_tool_path, "download", "genome", "accession", accession, "--include", "gbff"]
    subprocess.run(cmd, cwd=working_dir, check=True)

def get_publication_count(endpoint_url, sparql_template, ncbigene, logger, field_name):
    """
    Query SPARQL endpoint and extract publication count for a given gene.

    Args:
        endpoint_url (str): URL of the SPARQL endpoint.
        sparql_template (Template): SPARQL query template.
        ncbigene (str): Gene ID to query.
        logger (logging.Logger): Logger for error messages.
        field_name (str): Field name in the SPARQL response JSON.

    Returns:
        str: Count value or '.' if the query fails.
    """
    response = execute_sparql_query(endpoint_url, sparql_template, ncbigene)
    if response.status_code == 200:
        bindings = response.json()["results"]["bindings"]
        if bindings:
            for binding in bindings:
                return binding[field_name]["value"]
        return "0"
    else:
        logger.error("SPARQL request failed: status_code=%d\nresponse_text=%s",
                     response.status_code, response.text)
        return "."

def process_gbff_and_output_gff(config, logger, pubchem_template, pubtator_template, accession):
    """
    Parse .gbff file and create GFF files with publication counts per gene.

    Args:
        config (ConfigParser): Parsed configuration object.
        logger (logging.Logger): Logger for error messages.
        script_dir (str): Directory where the script resides.
        pubchem_template (Template): SPARQL template for PubChem.
        pubtator_template (Template): SPARQL template for PubTator.
        accession (str): Assembly accession ID.
    """
    db_file = config["config"]["db_file"]
    working_dir = config["config"]["working_dir"]
    dataset_file = f"{working_dir}/{config['config']['ncbi_dataset_zip_file']}"
    gbff_file = f"ncbi_dataset/data/{accession}/genomic.gbff"

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    sql = "SELECT gene_id FROM accession WHERE protein_accession = ?"

    # Parse .gbff in ZIP file with Biopython
    with zipfile.ZipFile(dataset_file, "r") as zf:
        with zf.open(gbff_file) as gbff_raw, \
             open("output_pubchem.gff", "w") as gff_pubchem, \
             open("output_pubtator.gff", "w") as gff_pubtator:

            gbff_text = TextIOWrapper(gbff_raw, encoding="utf-8")

            # Write GFF3 version header
            gff_pubchem.write("##gff-version 3\n")
            gff_pubtator.write("##gff-version 3\n")

            for i, record in enumerate(SeqIO.parse(gbff_text, "genbank"), start=1):
                print(f"\rProcessing record #{i}" + " " * 30, flush=True)
                min_start, max_end = float("inf"), float("-inf")

                # Write GFF body to a temporary file
                with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp_pubchem, \
                     tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp_pubtator:

                    cds_counter = 0
                    for j, feature in enumerate(record.features, start=1):
                        print(f"\r  → feature {j}/{len(record.features)}", end="", flush=True)
                        if feature.type != "CDS":
                            continue

                        cds_counter += 1

                        # Get protein_id (may not exist)
                        protein_id = feature.qualifiers.get("protein_id", ["N/A"])[0]
                        start, end = int(feature.location.start) + 1, int(feature.location.end)
                        strand = "+" if feature.location.strand >= 0 else "-"
                        feature_id = f"{record.id}_{feature.type}_{cds_counter}"
                        attributes = f"ID={feature_id};protein_id={protein_id}"

                        # Execute SQL to get ncbigene conditional on protein_id
                        cur.execute(sql, (protein_id,))
                        row = cur.fetchone()
                        if row:
                            ncbigene = row["gene_id"]
                            attributes += f";ncbigene={ncbigene}"
                            # SPARQL to PubChem
                            score_pubchem = get_publication_count("https://rdfportal.org/pubchem/sparql", pubchem_template, ncbigene, logger, "ref_count")
                            # SPARQL to PubTator
                            score_pubtator = get_publication_count("https://rdfportal.org/ncbi/sparql", pubtator_template, ncbigene, logger, "refCount")
                        else:
                            score_pubchem = score_pubtator = "."

                        # Output to GFF files
                        gff_line = [record.id, "Reference", "gene", start, end, score_pubchem, strand, ".", attributes]
                        tmp_pubchem.write("\t".join(map(str, gff_line)) + "\n")
                        gff_line[5] = score_pubtator
                        tmp_pubtator.write("\t".join(map(str, gff_line)) + "\n")

                        min_start = min(min_start, start)
                        max_end = max(max_end, end)

                    if min_start < float("inf") and max_end > float("-inf"):
                        gff_pubchem.write(f"##sequence-region {record.id} {min_start} {max_end}\n")
                        gff_pubtator.write(f"##sequence-region {record.id} {min_start} {max_end}\n")

                    tmp_pubchem.seek(0)
                    gff_pubchem.writelines(tmp_pubchem.readlines())
                    tmp_pubtator.seek(0)
                    gff_pubtator.writelines(tmp_pubtator.readlines())

    conn.close()

def main():
    """
    Main function to load config, parse arguments, download data,
    and process .gbff to generate GFF files with publication counts.
    """
    config, script_dir = load_config()
    logger = setup_logger()
    datasets_tool_path = shutil.which("datasets") or config["config"]["datasets_tool_path"]

    # Configure the parser to receive Assembly Accession input
    parser = argparse.ArgumentParser(description="Create literature frequency information for each genome")
    parser.add_argument("-i", "--input", dest="assembly_accession", help="Assembly Accession", required=True)
    args = parser.parse_args()

    # Download ncbi_dataset.zip
    download_genome_zip(datasets_tool_path, args.assembly_accession, config["config"]["working_dir"])

    # Load SPARQL templates
    pubchem_template, pubtator_template = get_sparql_templates(script_dir)

    # Process gbff and output GFF
    process_gbff_and_output_gff(config, logger, pubchem_template, pubtator_template, args.assembly_accession)

    print("\nPubchem GFF file output complete.")
    print("Pubtator GFF file output complete.")

if __name__ == "__main__":
    main()