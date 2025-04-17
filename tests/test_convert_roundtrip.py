
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from main import insdc_to_faldo, faldo_to_insdc_wrapper

test_cases = [
    # pattern 1
    ("GCF_000968255.1-NZ_JZJK01000068:467"),
    # pattern 2
    ("GCF_000968255.1-NZ_JZJK01000068:340..565"),
    # pattern 3
    ("GCF_000968255.1-NZ_JZJK01000068:<345..500"),
    # pattern 4
    ("GCF_000968255.1-NZ_JZJK01000068:1..>888"),
    # pattern 5
    ("GCF_000968255.1-NZ_JZJK01000068:<1..>888"),
    # pattern 6
    ("GCF_000968255.1-NZ_JZJK01000068:102.110"),
    # pattern 7
    ("GCF_000968255.1-NZ_JZJK01000068:123^124"),
    # pattern 8
    ("GCF_000968255.1-NZ_JZJK01000068:join(12..78,134..202)"),
    # pattern 9
    ("GCF_000968255.1-NZ_JZJK01000068:complement(34..126)"),
    # pattern 10
    ("GCF_000968255.1-NZ_JZJK01000068:J00194.1:100..202"),
    # pattern 11
    ("GCF_000968255.1-NZ_JZJK01000068:complement(join(2691..4571,4918..5163))"),
    # pattern 12
    ("GCF_000968255.1-NZ_JZJK01000068:join(complement(4918..5163),complement(2691..4571))"),
    # pattern 13
    ("GCF_000968255.1-NZ_JZJK01000068:join(1..100,J00194.1:100..202)"),
    # pattern 14 (Same as Join?) TODO: Need to consider whether to restore "order" when converting FALDO → INSDC
    # ("GCF_000968255.1-NZ_JZJK01000068:order(1..2176,8407..11097)"),
    # pattern 15
    ("GCF_000968255.1-NZ_JZJK01000068:complement(join(123..456,complement(789..900),join(1000..1100,1200..1300)))"),
    # pattern 16
    ("GCF_000968255.1-NZ_JZJK01000068:complement(join(123..456,complement(join(789..900,complement(1001..1100))),join(complement(1200..1300),join(1400..1500,1600..1700))))")
]

@pytest.mark.parametrize("input_id", test_cases)
def test_convert_roundtrip(input_id):
    faldo = insdc_to_faldo(input_id, "http://example.org/", "http://example.org/context/faldo.jsonld")
    result = faldo_to_insdc_wrapper(faldo)
    assert result == input_id
