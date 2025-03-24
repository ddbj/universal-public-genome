import json
import subprocess
import pytest
import pandas as pd

# Load a test case file
file_path = "test/test_case.xlsx"
df = pd.read_excel(file_path)

# CLI Execution Functions
def run_cli(input_value):
    """Execute CLI script and get output"""
    result = subprocess.run(
        ["python", "main.py", "--input", input_value],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

# Creating parameterized test cases
@pytest.mark.parametrize("insdc_id, expected_faldo, pattern_type, description", df.values)
def test_insdc_to_faldo(insdc_id, expected_faldo, pattern_type, description):
    """INSDC ID → FALDO JSON-LD conversion test"""
    expected_output = json.loads(expected_faldo)
    output_json = json.loads(run_cli(insdc_id))
    assert output_json == expected_output, f"Test failed for: {pattern_type} - {description}"

@pytest.mark.parametrize("expected_insdc, faldo_json, pattern_type, description", df.values)
def test_faldo_to_insdc(expected_insdc, faldo_json, pattern_type, description):
    """FALDO JSON-LD → INSDC ID conversion test"""
    output_text = run_cli(faldo_json)
    assert output_text == expected_insdc, f"Test failed for: {pattern_type} - {description}"

if __name__ == "__main__":
    pytest.main()