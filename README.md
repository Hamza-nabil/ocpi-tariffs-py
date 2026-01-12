# OCPI Tariffs

![CI](https://github.com/Hamza-nabil/ocpi-tariffs-py/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A production-ready Python implementation of the **OCPI Tariff** module, supporting both **v2.1.1** and **v2.2.1**. This package provides a robust calculation engine to compute the cost of Charging Data Records (CDRs) against complex OCPI Tariffs.

It is designed to handle real-world complexities such as:
*   **Tariff Dimensions**: Exact calculation for Time, Energy, Parking Time, and Flat Fees.
*   **Restrictions**: Validation of Start/End time, Day of week, and Min/Max duration restrictions.
*   **Timezones**: Automatic handling of "Local Time" restrictions using Country Code mapping (e.g., `NLD` -> `Europe/Amsterdam`).
*   **Step Size**: Precise implementation of OCPI "step size" rounding rules (e.g., 5-minute increments).

## Installation

```bash
pip install ocpi-tariffs
```

## Usage

This package provides a unified API for both OCPI versions.

### 1. OCPI 2.1.1

```python
from ocpi_tariffs.v2_1_1 import Cdr, Tariff, calculate_cdr_cost

# Load your data (dict)
cdr_data = {...} 
tariff_data = {...}

# Instantiate Models
cdr = Cdr(**cdr_data)
tariff = Tariff(**tariff_data)

# Calculate Cost
# Returns a float (Total Cost)
total_cost = calculate_cdr_cost(cdr, tariff)

print(f"Total Cost: {total_cost}")
```

### 2. OCPI 2.2.1

```python
from ocpi_tariffs.v2_2_1 import Cdr, Tariff, calculate_cdr_cost

# Load your data (dict)
cdr_data = {...}
tariff_data = {...}

# Instantiate Models
cdr = Cdr(**cdr_data)
tariff = Tariff(**tariff_data)

# Calculate Cost
# Returns a Price object (excl_vat, incl_vat)
price = calculate_cdr_cost(cdr, tariff)

print(f"Cost (Excl VAT): {price.excl_vat}")
print(f"Cost (Incl VAT): {price.incl_vat}")
```

## Methodology

The calculation engine follows a strict interpretation of the OCPI specifications.

### Key Logic
1.  **Chronological Processing**: The engine processes the CDR's `charging_periods` chronologically.
2.  **Element Selection**: For each period, it searches for the first active `TariffElement` based on restrictions (Time, Day, Duration, etc.).
3.  **Component Application**: Applies active price components (Energy, Time, Flat, etc.) to the period's usage.
4.  **Step Size**: Applies step size rounding rules (per-period for v2.1.1, aggregated for v2.2.1) to ensure billing accuracy.

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
