from abc import ABC, abstractmethod
from const import POSITION, EXACT_POSITION, REGION, LIST_OF_REGIONS, INBETWEEN_POSITION, FUZZY_POSITION, INRANGE_POSITION, NEGATIVE_STRAND

# Base class for all location nodes
class LocationNode(ABC):
    @abstractmethod
    def __str__(self):
        pass

# Represents a single position, e.g., "467"
class SinglePositionNode(LocationNode):
    def __init__(self, position: int):
        self.position = position

    def __str__(self):
        return str(self.position)

# Represents a position between two bases, like "123^124"
# This means the position lies between base 123 and 124
class InBetweenNode(LocationNode):
    def __init__(self, left: int, right: int):
        self.left = left
        self.right = right

    def __str__(self):
        return f"{self.left}^{self.right}"

# Represents a position within a range like "102.110"
# This indicates the exact position is unknown, but lies between 102 and 110
class InRangeNode(LocationNode):
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def __str__(self):
        return f"{self.start}.{self.end}"

# Represents a fuzzy range like "<345..500", "1..>888", or "<1..>888"
# This indicates that the start and/or end positions are not exactly known
# It also doubles as a case without Fuzzy like 123..456
class FuzzyRangeNode(LocationNode):
    def __init__(self, start: int, end: int, is_fuzzy_start: bool = False, is_fuzzy_end: bool = False):
        self.start = start
        self.end = end
        self.is_fuzzy_start = is_fuzzy_start
        self.is_fuzzy_end = is_fuzzy_end

    def __str__(self):
        start_str = f"<{self.start}" if self.is_fuzzy_start else str(self.start)
        end_str = f">{self.end}" if self.is_fuzzy_end else str(self.end)
        return f"{start_str}..{end_str}"

# Represents a join() function, which joins multiple locations
class JoinNode(LocationNode):
    def __init__(self, children: list[LocationNode]):
        self.children = children  # List of LocationNode instances

    def __str__(self):
        return f"join({','.join(str(c) for c in self.children)})"

# Represents a order() function, which joins multiple locations
class OrderNode(LocationNode):
    def __init__(self, children: list[LocationNode]):
        self.children = children  # List of LocationNode instances

    def __str__(self):
        return f"order({','.join(str(c) for c in self.children)})" 

# Represents a complement() function, which reverses the strand
class ComplementNode(LocationNode):
    def __init__(self, child: LocationNode):
        self.child = child  # A single LocationNode

    def __str__(self):
        return f"complement({str(self.child)})"

# Represents a range on a remote reference sequence, e.g., "J00194.1:100..202"
class RemoteRangeNode(LocationNode):
    def __init__(self, accession: str, start: int, end: int):
        self.accession = accession
        self.start = start
        self.end = end

    def __str__(self):
        return f"{self.accession}:{self.start}..{self.end}"

def split_top_level(s: str) -> list[str]:
    """
    Split a comma-separated list at the top level,
    ignoring commas that are nested inside parentheses.

    Example:
        input: "123..456,complement(789..900),join(1000..1100,1200..1300)"
        output: ["123..456", "complement(789..900)", "join(1000..1100,1200..1300)"]
    """
    parts = []
    bracket_level = 0
    current = []

    for char in s:
        if char == ',' and bracket_level == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            # Track nesting depth
            if char == '(':
                bracket_level += 1
            elif char == ')':
                bracket_level -= 1
            current.append(char)

    if current:
        parts.append(''.join(current).strip())

    return parts

import re

def parse_insdc_location(s: str) -> LocationNode:
    """
    Parse an INSDC location string into an abstract syntax tree (AST)
    composed of LocationNode instances. Supports nested join() and complement().

    Examples:
        "123..456"
        "complement(123..456)"
        "join(1..100,complement(200..300),join(400..500,600..700))"
    """

    # Case: single base position (e.g., "467")
    match = re.match(r"^(\d+)$", s)
    if match:
        return SinglePositionNode(int(match.group(1)))

    # Case: in-between position, like "123^124"
    match = re.match(r"^(\d+)\^(\d+)$", s)
    if match:
        left, right = match.groups()
        return InBetweenNode(int(left), int(right))

    # Case: in-range position, like "102.110"
    match = re.match(r"^(\d+)\.(\d+)$", s)
    if match:
        start, end = match.groups()
        return InRangeNode(int(start), int(end))

    # Case: fuzzy range (e.g., <345..500, 1..>888, <1..>888)
    # Matches optional "<" or ">" on either side of the range
    match = re.match(r"^(<)?(\d+)\.\.(>?)?(\d+)$", s)
    if match:
        fuzzy_start_flag, start, fuzzy_end_flag, end = match.groups()
        return FuzzyRangeNode(
            int(start),
            int(end),
            is_fuzzy_start=bool(fuzzy_start_flag),
            is_fuzzy_end=bool(fuzzy_end_flag)
        )

    # Case: remote range with accession (e.g., "J00194.1:100..202")
    match = re.match(r"^([A-Z0-9_.]+):(\d+)\.\.(\d+)$", s)
    if match:
        accession, start, end = match.groups()
        return RemoteRangeNode(accession, int(start), int(end))

    s = s.strip()

    # Case: complement(...) → recursively parse the inside
    if s.startswith("complement(") and s.endswith(")"):
        inner = s[len("complement("):-1]
        return ComplementNode(parse_insdc_location(inner))

    # Case: join(...) → split arguments at top level and parse each
    elif s.startswith("join(") and s.endswith(")"):
        inner = s[len("join("):-1]
        parts = split_top_level(inner)
        return JoinNode([parse_insdc_location(part) for part in parts])

    # Case: order(...) → split arguments at top level and parse each
    elif s.startswith("order(") and s.endswith(")"):
        inner = s[len("order("):-1]
        parts = split_top_level(inner)
        return OrderNode([parse_insdc_location(part) for part in parts])

    else:
        # Unsupported or invalid input
        raise ValueError(f"Unsupported or invalid INSDC location: {s}")

# Function to create a position object (strand support)
# def make_position(pos, accession, strand=None):
def make_position_exact(pos, accession):
    pos_obj = {
        "type": EXACT_POSITION,
        "position": pos,
        "reference": f"insdc:{accession}"
    }
    return pos_obj


def location_node_to_faldo(node: LocationNode, accession: str, strand=None) -> dict:
    """
    Recursively convert a LocationNode (AST) into a FALDO JSON-LD structure.
    
    Args:
        node (LocationNode): Root of the location tree (e.g., ComplementNode, JoinNode)
        accession (str): INSDC accession to use as reference
        strand: For reverse strand, “NegativeStrand” is specified.
    
    Returns:
        dict: A FALDO JSON-LD fragment representing the location
    """
    if isinstance(node, SinglePositionNode):
        return make_position_exact(node.position, accession)

    elif isinstance(node, InBetweenNode):
        # Helper to wrap a type position with no type using FALDO's extension
        def make_position_nonetype(pos, accession):
            obj = {
                "position": pos,
                "reference": f"insdc:{accession}"
            }
            return obj

        # FALDO InBetweenPosition: has 'after' and 'before' references
        return {
            "type": INBETWEEN_POSITION,
            "after": make_position_nonetype(node.left, accession),
            "before": make_position_nonetype(node.right, accession)
        }

    elif isinstance(node, InRangeNode):
        # Helper to wrap a type position with no type using FALDO's extension
        def make_position(pos, accession):
            obj = {
                "type": POSITION,
                "position": pos,
                "reference": f"insdc:{accession}"
            }
            return obj

        # FALDO InRangePosition: unknown position within a known interval
        return {
            "type": INRANGE_POSITION,
            "begin": make_position(node.start, accession),
            "end": make_position(node.end, accession)
        }

    elif isinstance(node, FuzzyRangeNode):
        # Helper to wrap a fuzzy position using FALDO's extension
        def make_position_fuzzy(pos):
            obj = {
                "type": FUZZY_POSITION,
                "position": pos,
                "reference": f"insdc:{accession}"
            }
            return obj

        begin = make_position_fuzzy(node.start) if node.is_fuzzy_start else make_position_exact(node.start, accession)
        end = make_position_fuzzy(node.end) if node.is_fuzzy_end else make_position_exact(node.end, accession)

        return {
            "type": REGION,
            "begin": begin,
            "end": end,
            **({"strand": strand} if strand else {})
        }

    elif isinstance(node, ComplementNode):
        return location_node_to_faldo(node.child, accession, strand=NEGATIVE_STRAND)

    elif isinstance(node, (JoinNode, OrderNode)):
        return {
            "type": LIST_OF_REGIONS,
            **({"strand": strand} if strand else {}),
            "member": [
                {
                    **location_node_to_faldo(member, accession),
                    "order": idx + 1
                } for idx, member in enumerate(node.children)
            ]
        }

    elif isinstance(node, RemoteRangeNode):
        # Remote ranges use a different accession in their reference
        return {
            "type": REGION,
            "begin": make_position_exact(node.start, node.accession),
            "end": make_position_exact(node.end, node.accession)
        }

    else:
        raise TypeError(f"Unsupported LocationNode type: {type(node)}")
    
def wrap_faldo(location_json: dict, full_id: str, id_base_url: str, context_url: str) -> dict:
    """
    Wrap the FALDO location into a complete JSON-LD object.

    Args:
        location_json (dict): The internal location structure
        full_id (str): The full ID string (e.g., GCA000000000-J00000:complement(...))
        id_base_url (str): Base URL to prepend for "id"
        context_url (str): URL for @context

    Returns:
        dict: Full JSON-LD document
    """
    return {
        "@context": context_url,
        "id": f"{id_base_url}{full_id}",
        "location": location_json
    }
