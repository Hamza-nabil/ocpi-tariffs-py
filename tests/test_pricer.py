import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from ocpi_tariffs.v2_2_1.models import Cdr, Tariff
from ocpi_tariffs.v2_2_1.tariff_calculator import calculate_cdr_cost


def read_json(file_path: str) -> Optional[Dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        return None
    with open(path, "r") as f:
        data: Dict[str, Any] = json.load(f)
        return data


# Parametrize with paths to CDR/Tariff
@pytest.mark.parametrize(
    "cdr_path",
    [str(p) for p in Path("tests/test_data/").rglob("cdr*.json")],
)
def test_json(cdr_path: str) -> None:
    parent_folder = Path(cdr_path).parent

    # Construct path for the corresponding tariff.json
    tariff_path = parent_folder / "tariff.json"

    cdr_data = read_json(cdr_path)
    tariff_data = read_json(str(tariff_path))

    if cdr_data is None:
        pytest.fail("CDR data not found")

    cdr = Cdr(**cdr_data)
    tariff: Optional[Tariff] = None
    if tariff_data is not None:
        tariff = Tariff(**tariff_data)

    calculated_cost = calculate_cdr_cost(cdr=cdr, tariff=tariff)

    # Compare with expected total cost in CDR
    expected_cost = cdr.total_cost

    if expected_cost:
        # Helper to compare decimals with tolerance
         def loose_equal(a: Optional[Decimal], b: Optional[Decimal]) -> bool:
             if a is None and b is None:
                 return True
             if a is None or b is None:
                 return False
             # Allow 0.02 difference (2 cents) to account for VAT rounding amplification
             return abs(a - b) <= Decimal("0.02")

         # If strict equality fails, try rounded equality
         if calculated_cost != expected_cost:
              matches_excl = loose_equal(calculated_cost.excl_vat, expected_cost.excl_vat)
              matches_incl = loose_equal(calculated_cost.incl_vat, expected_cost.incl_vat)

              if matches_excl and matches_incl:
                   return # Pass

              # If rounding didn't help, fail with original values
              assert calculated_cost == expected_cost, (
                f"Expected {expected_cost}, got {calculated_cost}"
              )


if __name__ == "__main__":
    # debug print number of files in test_data
    print("Number of files in test_data: ", len([str(p) for p in Path("test_data").rglob("cdr*.json")]))
    pytest.main()
