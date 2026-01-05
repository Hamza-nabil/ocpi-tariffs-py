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

    # Detect version based on path
    if "v2_1_1" in cdr_path:
        from ocpi_tariffs.v2_1_1.models import Cdr, Tariff
        from ocpi_tariffs.v2_1_1.tariff_calculator import calculate_cdr_cost
    else:
        from ocpi_tariffs.v2_2_1.models import Cdr, Tariff
        from ocpi_tariffs.v2_2_1.tariff_calculator import calculate_cdr_cost

    # Instantiate models
    cdr = Cdr(**cdr_data)
    tariff: Optional[Tariff] = None
    if tariff_data is not None:
        tariff = Tariff(**tariff_data)
    
    # Calculate and verify
    if tariff:
        calculated_cost = calculate_cdr_cost(cdr=cdr, tariff=tariff)
        expected_cost = cdr.total_cost

        # v2.1.1 calculated_cost returns float, v2.2.1 returns Price object.
        # This is a discrepancy!
        # v2.2.1 `calculate_cdr_cost` returns `Price` model (excl_vat, incl_vat).
        # v2.1.1 `pricer.calculate_total_cost()` (and my wrapper) returns `float` (total cost).
        # I need to standardize the wrapper in v2.1.1 to return a similar structure OR adapt the test.
        # The test previously handled v2.1.1 and v2.2.1 differently.
        # v2.1.1: `assert calculated_cost == expected_cost` (floats)
        # v2.2.1: `matches_excl = ...` (Price objects)
        
        # If I want strict standardization, v2.1.1 wrapper should return a Price-like object or at least the test should handle the difference.
        # Let's inspect what `calculated_cost` is. 
        # For v2.1.1 it is a float.
        # For v2.2.1 it is a Price object.
        
        # Standard way:
        if isinstance(calculated_cost, (int, float)):
             # v2.1.1 case (or simple float return)
             assert abs(calculated_cost - expected_cost) <= 0.02, f"Expected {expected_cost}, got {calculated_cost}"
        else:
            # v2.2.1 Price object case
            # Helper to compare decimals with tolerance
            def loose_equal(a: Optional[Decimal], b: Optional[Decimal]) -> bool:
                if a is None and b is None:
                    return True
                if a is None or b is None:
                    return False
                return abs(a - b) <= Decimal("0.02")

            if calculated_cost != expected_cost:
                matches_excl = loose_equal(calculated_cost.excl_vat, expected_cost.excl_vat)
                matches_incl = loose_equal(calculated_cost.incl_vat, expected_cost.incl_vat)

                if matches_excl and matches_incl:
                    return

                assert calculated_cost == expected_cost, f"Expected {expected_cost}, got {calculated_cost}"


if __name__ == "__main__":
    # debug print number of files in test_data
    print("Number of files in test_data: ", len([str(p) for p in Path("test_data").rglob("cdr*.json")]))
    pytest.main()
