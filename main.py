import argparse
import os
import sys
import json
from parser import parse_insdc_location, location_node_to_faldo, wrap_faldo
from const import POSITION, EXACT_POSITION, REGION, LIST_OF_REGIONS, INBETWEEN_POSITION, FUZZY_POSITION, INRANGE_POSITION, NEGATIVE_STRAND

def insdc_to_faldo(insdc_id: str, id_base_url: str, context_url: str) -> dict:
    """
    Convert INSDC ID with location notation into FALDO JSON-LD.
    """
    try:
        # Split into accession and location string
        if ':' not in insdc_id:
            raise ValueError("Missing ':' in INSDC ID")

        prefix, location_str = insdc_id.split(":", 1)
        accession = prefix.split("-")[-1]

        # Parse INSDC Location into AST
        ast = parse_insdc_location(location_str)

        # Convert AST to FALDO JSON
        location_json = location_node_to_faldo(ast, accession)

        # Wrap as full JSON-LD
        full_id = prefix + ":" + location_str
        return wrap_faldo(location_json, full_id, id_base_url, context_url)

    except Exception as e:
        raise RuntimeError(f"Failed to convert INSDC ID to FALDO: {e}")

def faldo_to_insdc(location, sequence=None):
    location_type = location.get("type")
    
    if location_type == POSITION:
        pos = location["position"]
        return str(pos)

    elif location_type == EXACT_POSITION:
        ref = location.get("reference", "")
        pos = location["position"]
        if sequence and ref == f"insdc:{sequence}":
            return str(pos)  # same sequence, omit prefix
        else:
            return f"{ref.replace('insdc:', '')}:{pos}"

    # Remote reference region and general Region
    elif location_type == REGION:
        begin = location["begin"]
        end = location["end"]
        begin_ref = begin.get("reference")
        end_ref = end.get("reference")

        if begin_ref != end_ref:
            raise ValueError("begin and end references are different, cannot convert to INSDC safely")

        # Fuzzy judgment (discriminate from structure)
        if begin["type"] == FUZZY_POSITION and end["type"] == FUZZY_POSITION:
            return f"<{begin['position']}..>{end['position']}"
        elif begin["type"] == FUZZY_POSITION:
            return f"<{begin['position']}..{end['position']}"
        elif end["type"] == FUZZY_POSITION:
            return f"{begin['position']}..>{end['position']}"
        
        # Normal or remote reference range
        if begin_ref == f"insdc:{sequence}":
            begin_str = faldo_to_insdc(begin, sequence)
            end_str = faldo_to_insdc(end, sequence)
            
            strand = location.get("strand")
            if strand == NEGATIVE_STRAND:
                return f"complement({begin['position']}..{end['position']})"
            else:
                return f"{begin_str}..{end_str}"

        else:
            return f"{begin_ref.replace('insdc:', '')}:{begin['position']}..{end['position']}"

    elif location_type == LIST_OF_REGIONS:
        members = location.get("member", [])
        sorted_members = sorted(members, key=lambda m: m.get("order", 0))
        inner = f"join({','.join(faldo_to_insdc(m, sequence) for m in sorted_members)})"

        strand = location.get("strand")
        if strand == NEGATIVE_STRAND:
            return f"complement({inner})"
        return inner

    elif location_type == INBETWEEN_POSITION:
        before = location["before"]["position"]
        after = location["after"]["position"]
        left = min(before, after)
        right = max(before, after)
        return f"{left}^{right}"

    elif location_type == INRANGE_POSITION:
        begin = faldo_to_insdc(location["begin"], sequence)
        end = faldo_to_insdc(location["end"], sequence)
        return f"{begin}.{end}"

    return ""

def faldo_to_insdc_wrapper(faldo_json):
    full_id = faldo_json["id"].split("/")[-1]
    assembly_sequence = full_id.split(":")[:-1][0]  # Get the assembly and sequence parts in the ID
    sequence = assembly_sequence.split('-')[-1]
    insdc_location = faldo_to_insdc(faldo_json["location"], sequence=sequence)
    return f"{assembly_sequence}:{insdc_location}"

def read_input_data(input_arg):
    has_stdin = not sys.stdin.isatty()

    if input_arg:
        if os.path.isfile(input_arg):
            with open(input_arg, 'r', encoding='utf-8') as f:
                return f.read()
        return input_arg
    elif has_stdin:
        return sys.stdin.read()
    else:
        # If there is no input, an error is generated and the system terminates.
        sys.stderr.write("Error: No input provided. Use -i option or provide input via stdin.\n")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="INSDC ID ⇔ FALDO JSON-LD Converter")
    parser.add_argument("-i", "--input", help="Input value or file path (fallback to stdin if omitted)")
    parser.add_argument("--context-url", type=str, default="http://example.org/context/faldo.jsonld", help="URL of context")
    parser.add_argument("--id-base-url", type=str, default="http://example.org/", help="Base URL for ID")
    args = parser.parse_args()
    
    input_value = read_input_data(args.input)

    id_base_url = args.id_base_url.strip()
    # Add if it does not end in '/'.
    id_base_url = id_base_url if id_base_url.endswith('/') else id_base_url + '/'
    context_url = args.context_url.strip()

    if input_value.startswith("{"):
        result = faldo_to_insdc_wrapper(json.loads(input_value))
        print(result)
    else:
        result = insdc_to_faldo(input_value, id_base_url, context_url)
        formatted_data = json.dumps(result, indent=2)
        print(formatted_data)
    
if __name__ == "__main__":
    main()