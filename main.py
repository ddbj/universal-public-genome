import argparse
import sys
import json
import re
import urllib.parse
from Bio.SeqFeature import FeatureLocation

def insdc_to_faldo(insdc_id, id_base_url, context_url):
    """
    Convert ID containing INSDC Location notation to FALDO JSON-LD
    """

    # TODO: Implement under the assumption that the number of layers is variable.
    if "join(complement(" in insdc_id:
        # Complement-and-Join
        # example: join(complement(4918..5163),complement(2691..4571))
        match = re.match(r"(.+):join\(complement\((\d+)\.\.(\d+)\),complement\((\d+)\.\.(\d+)\)\)", insdc_id)
        if match:
            accession, start1, end1, start2, end2 = match.groups()
            faldo_json = {
                "@context": f"{context_url}",
                "id": f"{id_base_url}{insdc_id}",
                "faldo:location": {
                    "type": "faldo:BagOfRegions",
                    "faldo:member": [
                        {
                            "type": "faldo:Region",
                            "faldo:begin": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(start1),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:end": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(end1),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:strand": "faldo:NegativeStrand"
                        },
                        {
                            "type": "faldo:Region",
                            "faldo:begin": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(start2),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:end": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(end2),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:strand": "faldo:NegativeStrand"
                        }
                    ]
                }
            }
            return json.dumps(faldo_json, indent=2)
    elif "complement(join(" in insdc_id:
        # Joined-Complemented-Regions
        # example: complement(join(2691..4571,4918..5163))
        match = re.match(r"(.+):complement\(join\((\d+)\.\.(\d+),(\d+)\.\.(\d+)\)\)", insdc_id)
        if match:
            accession, start1, end1, start2, end2 = match.groups()
            faldo_json = {
                "@context": f"{context_url}",
                "id": f"{id_base_url}{insdc_id}",
                "faldo:location": {
                    "type": "faldo:ListOfRegions",
                    "faldo:strand": "faldo:NegativeStrand",
                    "faldo:member": [
                        {
                            "type": "faldo:Region",
                            "faldo:begin": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(start1),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:end": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(end1),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:order": 1
                        },
                        {
                            "type": "faldo:Region",
                            "faldo:begin": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(start2),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:end": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(end2),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:order": 2
                        }
                    ]
                }
            }
            return json.dumps(faldo_json, indent=2)
    elif "join(" in insdc_id and ":" in insdc_id:
        # Join-with-Remote-Reference
        # example: join(1..100,J00194.1:100..202)
        match = re.match(r"(.+):join\((\d+)\.\.(\d+),([\w\.]+):(\d+)\.\.(\d+)\)", insdc_id)
        if match:
            accession, start1, end1, ref2, start2, end2 = match.groups()
            ref2 = re.sub(r"\.\d+$", "", ref2)  # Remove version information (e.g. .1)
            faldo_json = {
                "@context": f"{context_url}",
                "id": f"{id_base_url}{insdc_id}",
                "faldo:location": {
                    "type": "faldo:ListOfRegions",
                    "faldo:member": [
                        {
                            "type": "faldo:Region",
                            "faldo:begin": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(start1),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:end": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(end1),
                                "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                            },
                            "faldo:order": 1
                        },
                        {
                            "type": "faldo:Region",
                            "faldo:begin": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(start2),
                                "faldo:reference": f"insdc:{ref2}"
                            },
                            "faldo:end": {
                                "type": "faldo:ExactPosition",
                                "faldo:position": int(end2),
                                "faldo:reference": f"insdc:{ref2}"
                            },
                            "faldo:order": 2
                        }
                    ]
                }
            }
            return json.dumps(faldo_json, indent=2)        

    match = re.match(r"(.+):([<>]?\d+|\d+)\.(\d+)", insdc_id)
    if match:
        # Uncertain-Location
        # example: 102.110
        accession, start, end = match.groups()
        start_pos, end_pos = int(start), int(end)
        faldo_json = {
            "@context": f"{context_url}",
            "id": f"{id_base_url}{insdc_id}",
            "faldo:location": {
                "type": "faldo:InRangePosition",
                "faldo:begin": {
                    "type": "faldo:Position",
                    "faldo:position": start_pos,
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                },
                "faldo:end": {
                    "type": "faldo:Position",
                    "faldo:position": end_pos,
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                }
            }
        }
        return json.dumps(faldo_json, indent=2)

    match = re.match(r"(.+):([<>]?\d+)\^([<>]?\d+)", insdc_id)
    if match:
        # Between-Bases
        # example: 123^124
        accession, before, after = match.groups()
        faldo_json = {
            "@context": f"{context_url}",
            "id": f"{id_base_url}{insdc_id}",
            "faldo:location": {
                "type": "faldo:InBetweenPosition",
                "faldo:before": {
                    "faldo:position": int(before),
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                },
                "faldo:after": {
                    "faldo:position": int(after),
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                }
            }
        }
        return json.dumps(faldo_json, indent=2)

    match = re.match(r"(.+):join\((.+)\)", insdc_id)
    if match:
        # Joined-Regions
        # join(12..78,134..202)
        accession, regions = match.groups()
        region_list = []
        for idx, region in enumerate(regions.split(','), start=1):
            sub_match = re.match(r"([<>]?\d+)\.\.([<>]?\d+)", region)
            if sub_match:
                start, end = sub_match.groups()
                region_list.append({
                    "type": "faldo:Region",
                    "faldo:begin": {
                        "type": "faldo:ExactPosition",
                        "faldo:position": int(start),
                        "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                    },
                    "faldo:end": {
                        "type": "faldo:ExactPosition",
                        "faldo:position": int(end),
                        "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                    },
                    "faldo:order": idx
                })
        
        faldo_json = {
            "@context": f"{context_url}",
            "id": f"{id_base_url}{insdc_id}",
            "faldo:location": {
                "type": "faldo:ListOfRegions",
                "faldo:member": region_list
            }
        }
        return json.dumps(faldo_json, indent=2)

    match = re.match(r"(.+):complement\((\d+)\.\.(\d+)\)", insdc_id)
    if match:
        # Complemented-Region
        # example: complement(34..126)
        accession, start, end = match.groups()
        faldo_json = {
            "@context": f"{context_url}",
            "id": f"{id_base_url}{insdc_id}",
            "faldo:location": {
                "type": "faldo:Region",
                "faldo:begin": {
                    "type": "faldo:ExactPosition",
                    "faldo:position": int(start),
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                },
                "faldo:end": {
                    "type": "faldo:ExactPosition",
                    "faldo:position": int(end),
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                },
                "faldo:strand": "faldo:NegativeStrand"
            }
        }
        return json.dumps(faldo_json, indent=2)

    match = re.match(r"(.+):(.+):(\d+)\.\.(\d+)", insdc_id)
    if match:
        # Remote-Reference
        # example: J00194.1:100..202
        accession, ref_accession, start, end = match.groups()
        ref_accession = re.sub(r"\.\d+$", "", ref_accession)  # Remove version information (e.g. .1)
        faldo_json = {
            "@context": f"{context_url}",
            "id": f"{id_base_url}{insdc_id}",
            "faldo:location": {
                "type": "faldo:Region",
                "faldo:begin": {
                    "type": "faldo:ExactPosition",
                    "faldo:position": int(start),
                    "faldo:reference": f"insdc:{ref_accession}"
                },
                "faldo:end": {
                    "type": "faldo:ExactPosition",
                    "faldo:position": int(end),
                    "faldo:reference": f"insdc:{ref_accession}"
                }
            }
        }
        return json.dumps(faldo_json, indent=2)

    match = re.match(r"(.+):([<>]?\d+)(\.\.([<>]?\d+))?", insdc_id)
    if match:
        accession, start, _, end = match.groups()
        
        if end is None:
            # Single-Base
            # example：467
            position = int(start)
            location = FeatureLocation(position - 1, position)
            faldo_json = {
                "@context": f"{context_url}",
                "id": f"{id_base_url}{insdc_id}",
                "faldo:location": {
                    "type": "faldo:ExactPosition",
                    "faldo:position": int(location.start) + 1,
                    "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                }
            }
        elif "<" in start or ">" in end:
            # Unknown-Start-Range
            # example: <345..500
            start_pos = int(start.lstrip("<")) if "<" in start else int(start)
            end_pos = int(end.lstrip(">")) if ">" in end else int(end)
            location = FeatureLocation(start_pos - 1, end_pos)
            faldo_json = {
                "@context": f"{context_url}",
                "id": f"{id_base_url}{insdc_id}",
                "faldo:location": {
                    "type": "faldo:Region",
                    "faldo:begin": {
                        "type": "faldo:FuzzyPosition" if "<" in start else "faldo:ExactPosition",
                        "faldo:position": start_pos,
                        "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                    },
                    "faldo:end": {
                        "type": "faldo:FuzzyPosition" if ">" in end else "faldo:ExactPosition",
                        "faldo:position": end_pos,
                        "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                    }
                }
            }
        else:
            # Base-Range
            # example: 340..565
            start, end = int(start), int(end)
            location = FeatureLocation(start - 1, end)
            faldo_json = {
                "@context": f"{context_url}",
                "id": f"{id_base_url}{insdc_id}",
                "faldo:location": {
                    "type": "faldo:Region",
                    "faldo:begin": {
                        "type": "faldo:ExactPosition",
                        "faldo:position": int(location.start) + 1,
                        "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                    },
                    "faldo:end": {
                        "type": "faldo:ExactPosition",
                        "faldo:position": int(location.end),
                        "faldo:reference": f"insdc:{accession.split('-')[-1]}"
                    }
                }
            }
        return json.dumps(faldo_json, indent=2)
    
    return "Error: Invalid INSDC ID format."

def faldo_to_insdc(faldo_json, id_base_url):
    """
    Convert FALDO JSON-LD to ID containing INSDC Location notation
    """
    try:
        faldo_data = json.loads(faldo_json)
        id_url = faldo_data.get("id", "")
        
        if not id_url:
            return "Error: Invalid FALDO JSON-LD format."

        parsed_id_url = urllib.parse.urlparse(id_url)
        insdc_id = parsed_id_url.path[1:]    # Remove the first slash
        return f"{insdc_id}"

    except json.JSONDecodeError:
        return "Error: Invalid JSON input."

def main():
    parser = argparse.ArgumentParser(description="INSDC ID ⇔ FALDO JSON-LD Converter")
    parser.add_argument("-i", "--input", nargs="?", default=None, help="ID or FALDO JSON-LD to be converted")
    parser.add_argument("--context-url", type=str, default="http://example.org/context/faldo.jsonld", help="URL of context")
    parser.add_argument("--id-base-url", type=str, default="http://example.org/", help="Base URL for ID")
    args = parser.parse_args()
    
    # If no input value is specified
    if args.input is None:
        input_value = sys.stdin.read().strip()  # Read from standard input
    else:
        input_value = args.input.strip()
    
    id_base_url = args.id_base_url.strip()
    # Add if it does not end in '/'.
    id_base_url = id_base_url if id_base_url.endswith('/') else id_base_url + '/'
    context_url = args.context_url.strip()

    if input_value.startswith("{"):
        result = faldo_to_insdc(input_value, id_base_url)
    else:
        result = insdc_to_faldo(input_value, id_base_url, context_url)
    
    print(result)

if __name__ == "__main__":
    main()
