"""
Basic Usage Example for OCPI Tariffs Package.

This script demonstrates how to import and use the calculator for both
OCPI 2.1.1 and 2.2.1 versions using the unified API.
"""

from datetime import datetime

# --- OCPI 2.1.1 Example ---
print("--- OCPI 2.1.1 Calculation ---")
from ocpi_tariffs.v2_1_1 import Cdr as CdrV211
from ocpi_tariffs.v2_1_1 import Tariff as TariffV211
from ocpi_tariffs.v2_1_1 import calculate_cdr_cost as calculate_v211

# Sample Data
cdr_data_v211 = {
    "id": "cdr-211",
    "currency": "EUR",
    "charging_periods": [
        {
            "start_date_time": "2024-01-01T12:00:00Z",
            "dimensions": [{"type": "TIME", "volume": 1.0}]  # 1 hour
        }
    ]
}

tariff_data_v211 = {
    "id": "tariff-211",
    "currency": "EUR",
    "elements": [
        {
            "price_components": [
                {"type": "TIME", "price": 2.0, "step_size": 300} # 2.00 EUR/hour
            ]
        }
    ]
}

# Calculate
cost_v211 = calculate_v211(CdrV211(**cdr_data_v211), TariffV211(**tariff_data_v211))
print(f"Total Cost: {cost_v211} EUR\n")


# --- OCPI 2.2.1 Example ---
print("--- OCPI 2.2.1 Calculation ---")
from ocpi_tariffs.v2_2_1 import Cdr as CdrV221
from ocpi_tariffs.v2_2_1 import Tariff as TariffV221
from ocpi_tariffs.v2_2_1 import calculate_cdr_cost as calculate_v221

# Sample Data (Note: v2.2.1 requires more fields usually)
cdr_data_v221 = {
    "id": "cdr-221",
    "start_date_time": "2024-01-01T12:00:00Z",
    "end_date_time": "2024-01-01T13:00:00Z",
    "total_time": 1.0,
    "total_energy": 0.0,
    "currency": "EUR",
    "charging_periods": [
        {
            "start_date_time": "2024-01-01T12:00:00Z",
            "dimensions": [{"type": "TIME", "volume": 1.0}]
        }
    ],
    "last_updated": "2024-01-01T13:00:00Z",
    "cdr_location": {
        "id": "loc-1",
        "timestamp": "2024-01-01T12:00:00Z", # Required for v2.2.1 location
        "address": "Test Street 1",
        "city": "Test City",
        "country": "NLD",
        "coordinates": {"latitude": "52.3", "longitude": "4.9"}
    }
}

tariff_data_v221 = {
    "id": "tariff-221",
    "currency": "EUR",
    "elements": [
        {
            "price_components": [
                {"type": "TIME", "price": 2.0, "step_size": 300}
            ]
        }
    ],
    "last_updated": "2024-01-01T00:00:00Z"
}

# Calculate
price_v221 = calculate_v221(CdrV221(**cdr_data_v221), TariffV221(**tariff_data_v221))
print(f"Total Cost (Excl VAT): {price_v221.excl_vat} EUR")
print(f"Total Cost (Incl VAT): {price_v221.incl_vat} EUR")
