# OCPI Tariffs

![CI](https://github.com/Hamza-nabil/ocpi-tariffs-py/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A production-ready Python implementation of the **OCPI 2.2.1 Tariff** module. This package provides a robust calculation engine to compute the cost of Charging Data Records (CDRs) against complex OCPI Tariffs.

It is designed to handle real-world complexities such as:
*   **Tariff Dimensions**: Exact calculation for Time, Energy, Parking Time, and Flat Fees.
*   **Restrictions**: Validation of Start/End time, Day of week, and Min/Max duration restrictions.
*   **Timezones**: Automatic handling of "Local Time" restrictions using Country Code mapping (e.g., `NLD` -> `Europe/Amsterdam`).
*   **Step Size**: Precise implementation of OCPI "step size" rounding rules (e.g., 5-minute increments).

## Methodology

The calculation engine follows a strict interpretation of the OCPI 2.2.1 specification, processing a CDR and a Tariff to produce a final Cost.

### 1. Chronological Processing
The engine processes the CDR's `charging_periods` chronologically. For each period:
1.  **Duration Calculation**: The duration is derived from the gap between the current period's `start_date_time` and the next period's start.
2.  **Local Time Resolution**: The period's start time is converted to the Charging Location's local time (derived from `cdr_location.country`) to accurately evaluate time-based restrictions (e.g., "08:00 - 18:00").

### 2. Tariff Element Selection
For each period, the engine searches for an **Active Tariff Element**:
*   It iterates through the Tariff's `elements`.
*   It checks the `restrictions` of each element against the session state (Current Local Time, Session Duration, Day of Week).
*   The first matching Element is selected.

### 3. Price Component Application
Once an element is active, its `price_components` are applied to the period's dimensions:
*   **FLAT**: Applied once per session (the first time a matching Flat component is encountered).
*   **ENERGY**: `period.volume` (kWh) × `price`.
*   **TIME**: `period.duration` (hours) × `price`.
*   **PARKING_TIME**: Applied if the CDR explicitly logs parking time or if logic determines the session is in a parking state.

### 4. Step Size Smoothing
To ensure billing accuracy according to tariff rules:
*   Raw usage (seconds or Wh) is aggregated per dimension.
*   **Step Size Logic**: At the end of the calculation (or where specified), the total duration/energy is rounded *up* to the nearest `step_size` multiple.
*   *Note*: As per OCPI rules, if both TIME and PARKING_TIME are present, step size logic usually prioritizes the total parking duration for the parking component.

## Installation

```bash
pip install ocpi-tariffs
```

*(Note: Once published to PyPI. For now, install via git)*

```bash
pip install git+ssh://git@github.com/Hamza-nabil/ocpi-tariffs-py.git
```

## Usage

### Basic Calculation

```python
from decimal import Decimal
from datetime import datetime
from ocpi_tariffs.v2_2_1.models import Cdr, Tariff
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
        "country": "NLD", # Essential for correct Timezone calculation
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
# Output: Total Cost: 5.00 EUR
```

## Development

This project uses `ruff` for linting and `mypy` for strong typing.

1.  **Install dependencies**:
    ```bash
    pip install -e .
    pip install ruff mypy pytest types-python-dateutil
    ```

2.  **Run Tests**:
    ```bash
    pytest
    ```

3.  **Code Check**:
    ```bash
    ruff check .
    mypy .
    ```

## License

MIT
