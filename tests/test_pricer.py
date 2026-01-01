import json
from pathlib import Path
import pytest
from ocpi_tariffs.v2_2_1.tariff_calculator import calculate_cdr_cost
from ocpi_tariffs.v2_2_1.models import Cdr, Tariff


def read_json(file_path):
    path = Path(file_path)
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


# Parametrize with paths to CDR/Tariff
@pytest.mark.parametrize(
    "cdr_path",
    [str(p) for p in Path("tests/test_data/").rglob("cdr*.json")],
)
def test_json(cdr_path):
    parent_folder = Path(cdr_path).parent

    # Construct path for the corresponding tariff.json
    tariff_path = parent_folder / "tariff.json"

    cdr_data = read_json(cdr_path)
    tariff_data = read_json(tariff_path)
    cdr = Cdr(**cdr_data)
    if tariff_data is None:
        tariff = None
    else:
        tariff = Tariff(**tariff_data)

    calculated_cost = calculate_cdr_cost(cdr=cdr, tariff=tariff)

    # Compare with expected total cost in CDR
    expected_cost = cdr.total_cost
    assert calculated_cost == expected_cost, (
        f"Expected {expected_cost}, got {calculated_cost}"
    )


if __name__ == "__main__":
    
    # debug print number of files in test_data
    print("Number of files in test_data: ", len([str(p) for p in Path("test_data").rglob("cdr*.json")]))
    pytest.main()
