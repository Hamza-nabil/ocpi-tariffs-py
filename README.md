# OCPI Tariffs

![CI](https://github.com/Hamza-nabil/ocpi-tariffs-py/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A specific, robust Python implementation of the **OCPI 2.2.1 Tariff** module. This package provides a calculation engine to compute the cost of Charging Data Records (CDRs) against complex OCPI Tariffs, handling:

*   **Tariff Dimensions**: Time, Energy, Parking Time, Flat Fees.
*   **Restrictions**: Start/End time, Day of week, Min/Max duration (supported by timezone-aware logic).
*   **Step Size**: Correct handling of rounding rules for Time, Parking, and Energy.
*   **Mixed Tariffs**: "Layered" or fallback tariff logic.

## Installation

```bash
pip install ocpi-tariffs
```

*(Note: Once published to PyPI. For now, install via git or local path)*

```bash
pip install git+ssh://git@github.com/Hamza-nabil/ocpi-tariffs-py.git
```

## Usage

### Basic Calculation

```python
from decimal import Decimal
from datetime import datetime
from ocpi_tariffs.v2_2_1.models import Cdr, Tariff, CdrLocation, GeoLocation, ChargingPeriod, CdrDimension, CdrDimensionType
from ocpi_tariffs.v2_2_1.tariff_calculator import calculate_cdr_cost

# 1. Define a Tariff
tariff_data = {
    "id": "tariff-1",
    "currency": "EUR",
    "elements": [
        {
            "price_components": [
                {"type": "ENERGY", "price": "0.50", "step_size": 1}
            ]
        }
    ],
    "last_updated": "2024-01-01T00:00:00Z"
}
tariff = Tariff(**tariff_data)

# 2. Define a CDR (Charging Session)
cdr_data = {
    "id": "cdr-1",
    "start_date_time": "2024-01-01T12:00:00Z",
    "end_date_time": "2024-01-01T13:00:00Z",
    "currency": "EUR",
    "cdr_location": {
        "id": "loc-1",
        "country": "NLD", # Important for Timezone restrictions
        "coordinates": {"latitude": "52.3", "longitude": "4.9"}
    },
    "charging_periods": [
        {
            "start_date_time": "2024-01-01T12:00:00Z",
            "dimensions": [
                {"type": "ENERGY", "volume": "10.0"} # 10 kWh
            ]
        }
    ],
    "total_energy": "10.0",
    "total_time": "1.0",
    "last_updated": "2024-01-01T13:00:00Z"
}
cdr = Cdr(**cdr_data)

# 3. Calculate Cost
price = calculate_cdr_cost(cdr, tariff)

print(f"Total Cost: {price.excl_vat} {tariff.currency}")
# Output: Total Cost: 5.00 EUR (10 kWh * 0.50)
```

## Development

This project uses `ruff` for linting and `mypy` for type checking.

1.  **Install dependencies**:
    ```bash
    pip install -e .
    pip install ruff mypy pytest types-python-dateutil
    ```

2.  **Run Tests**:
    ```bash
    pytest
    ```

3.  **Run Linting & Type Checking**:
    ```bash
    ruff check .
    ruff format --check .
    mypy .
    ```

## License

MIT
