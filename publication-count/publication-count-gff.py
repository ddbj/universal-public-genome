import os
import argparse
import subprocess
import zipfile
import requests
import configparser
import shutil
import logging
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
    Set up a logger for error logging to 'logs/publication-count-gff/error.log'.
    Returns:
        logging.Logger: Configured logger instance.
    """

    log_dir = "logs/publication-count-gff"
    log_file = os.path.join(log_dir, "error.log")

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("error_logger")
    logger.setLevel(logging.ERROR)
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def execute_sparql_query(endpoint_url, sparql_template, protein_id):
    """
    Execute a SPARQL query by substituting the ncbigene value in the template.

    Args:
        endpoint_url (str): The URL of the SPARQL endpoint.
        sparql_template (Template): The SPARQL query template.
        protein_id (str): Protein ID to substitute into the query.

    Returns:
        requests.Response: The HTTP response from the SPARQL endpoint.
    """
    sparql = sparql_template.substitute(protein_id=protein_id)
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
    with open(os.path.join(script_dir, "publication-count.rq"), "r", encoding="utf-8") as f:
        sparql_template = Template(f.read())
    return sparql_template

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

def get_publication_count(endpoint_url, sparql_template, protein_id, logger, field_name):
    """
    Query SPARQL endpoint and extract publication count for a given gene.

    Args:
        endpoint_url (str): URL of the SPARQL endpoint.
        sparql_template (Template): SPARQL query template.
        protein_id (str): Protein ID to query.
        logger (logging.Logger): Logger for error messages.
        field_name (str): Field name in the SPARQL response JSON.

    Returns:
        str: Count value or '.' if the query fails.
    """
    response = execute_sparql_query(endpoint_url, sparql_template, protein_id)
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

def process_gbff_and_output_gff(config, logger, sparql_template, accession):
    """
    Parse .gbff file and create GFF files with publication counts per gene.

    Args:
        config (ConfigParser): Parsed configuration object.
        logger (logging.Logger): Logger for error messages.
        sparql_template (Template): SPARQL template for PubChem.
        accession (str): Assembly accession ID.
    """
    cfg = config["config"]
    working_dir = cfg["working_dir"]
    dataset_file = f"{working_dir}/{cfg['ncbi_dataset_zip_file']}"
    gbff_file = f"ncbi_dataset/data/{accession}/genomic.gbff"
    output_gff_file = f"{accession}_output.gff"

    with zipfile.ZipFile(dataset_file, "r") as zf:

        # Count total lines
        with zf.open(gbff_file) as f:
            total_lines = sum(1 for _ in TextIOWrapper(f, encoding="utf-8"))

        # Count total records
        with zf.open(gbff_file) as f:
            gbff_text = TextIOWrapper(f, encoding="utf-8")
            total_records = sum(1 for _ in SeqIO.parse(gbff_text, "genbank"))

        # Real processing with three-level progress display
        with zf.open(gbff_file) as gbff_raw, \
             zf.open(gbff_file) as gbff_raw_lines, \
             open(f"{working_dir}/{output_gff_file}", "w") as gff_pubchem:

            gbff_text = TextIOWrapper(gbff_raw, encoding="utf-8")        # For SeqIO
            gbff_lines = TextIOWrapper(gbff_raw_lines, encoding="utf-8") # For line count

            gff_pubchem.write("##gff-version 3\n")

            current_line = 0
            current_record = 0

            for record in SeqIO.parse(gbff_text, "genbank"):
                current_record += 1

                # Count lines until end of this record ("//")
                for line in gbff_lines:
                    current_line += 1
                    if line.startswith("//"):
                        break

                feature_count = len(record.features)

                # PRINT: Line / Record / Feature (three-level progress display)
                def print_progress(feature_index, feature_total):
                    print(
                        f"\r"
                        f"[Line {current_line:7d} / {total_lines:7d}] "
                        f"[Record {current_record:4d} / {total_records:4d}] "
                        f"[Feature {feature_index:6d} / {feature_total:6d}]  "
                        f"{record.id}",
                        end="",
                        flush=True
                    )

                cds_counter = 0
                for j, feature in enumerate(record.features, start=1):
                    print_progress(j, feature_count)

                    if feature.type == "source":
                        start = int(feature.location.start) + 1
                        end = int(feature.location.end)
                        gff_pubchem.write(f"##sequence-region {record.id} {start} {end}\n")
                        feature_id = f"{record.id}_region"
                        attributes = f"ID={feature_id}"
                        region_line = [record.id, "Reference", "region", start, end, ".", "+", ".", attributes]
                        gff_pubchem.write("\t".join(map(str, region_line)) + "\n")
                        continue

                    if feature.type != "CDS":
                        continue

                    cds_counter += 1
                    protein_id = feature.qualifiers.get("protein_id", ["N/A"])[0]
                    start = int(feature.location.start) + 1
                    end = int(feature.location.end)
                    strand = "+" if feature.location.strand == 1 else "-" if feature.location.strand == -1 else "."
                    feature_id = f"{record.id}_CDS_{cds_counter}"
                    attributes = f"ID={feature_id};protein_id={protein_id}"

                    try:
                        score = get_publication_count(
                            "https://rdfportal.org/sib/sparql",
                            sparql_template,
                            protein_id,
                            logger,
                            "ref_count"
                        )
                        score = score if score is not None else "0"
                    except Exception as e:
                        logger.error(f"Failed to retrieve score for {protein_id}: {e}")
                        score = "0"

                    cds_line = [record.id, "Reference", "Gene", start, end, score, strand, ".", attributes]
                    gff_pubchem.write("\t".join(map(str, cds_line)) + "\n")

                print()  # line break after each record

    print(f"\nGFF file output is complete. Path: {os.path.join(working_dir, output_gff_file)}")

def main():
    """
    Main function to load config, parse arguments, download data,
    and process .gbff to generate GFF files with publication counts.
    """
    config, script_dir = load_config()
    logger = setup_logger()
    datasets_tool_path = shutil.which("datasets") or config["config"]["datasets_tool_path"]
    working_dir = config["config"]["working_dir"]

    # Configure the parser to receive Assembly Accession input
    parser = argparse.ArgumentParser(description="Create literature frequency information for each genome")
    parser.add_argument("-i", "--input", dest="assembly_accession", help="Assembly Accession", required=True)
    args = parser.parse_args()
    accession = args.assembly_accession

    # Download ncbi_dataset.zip
    download_genome_zip(datasets_tool_path, accession, working_dir)

    # Load SPARQL templates
    sparql_template= get_sparql_templates(script_dir)

    # Process gbff and output GFF
    process_gbff_and_output_gff(config, logger, sparql_template, accession)

if __name__ == "__main__":
    main()