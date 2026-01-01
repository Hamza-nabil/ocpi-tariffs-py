import pytest
from decimal import Decimal
from datetime import datetime
from ocpi_tariffs.v2_2_1.models import Cdr, Tariff, TariffElement, PriceComponent, Price, ChargingPeriod, CdrDimension, TariffRestrictions
from ocpi_tariffs.v2_2_1.enums import TariffDimensionType, CdrDimensionType
from ocpi_tariffs.v2_2_1.tariff_calculator import calculate_cdr_cost

def test_cdr_example_simple_time_tariff():
    """
    Based on docs/examples/cdr_example.json
    Tariff: 2.00 per hour, step_size 300 (5 min).
    Session: 1.973 hours.
    Expected: 4.00 EUR (excl VAT)
    """
    
    tariff = Tariff(
        id="12",
        currency="EUR",
        elements=[
            TariffElement(
                price_components=[
                    PriceComponent(
                        type=TariffDimensionType.TIME,
                        price=Decimal("2.00"),
                        vat=Decimal("10.0"),
                        step_size=300
                    )
                ]
            )
        ],
        last_updated=datetime(2015, 2, 2, 14, 15, 1)
    )
    
    cdr = Cdr(
        id="12345",
        start_date_time=datetime(2015, 6, 29, 21, 39, 9),
        end_date_time=datetime(2015, 6, 29, 23, 37, 32), # Duration matches 1.973h roughly?
        # 23:37:32 - 21:39:09 = 1h 58m 23s = 3600 + 3480 + 23 = 7103s
        # 7103 / 3600 = 1.97305
        currency="EUR",
        tariffs=[tariff],
        charging_periods=[
            ChargingPeriod(
                start_date_time=datetime(2015, 6, 29, 21, 39, 9),
                dimensions=[
                    CdrDimension(type=CdrDimensionType.TIME, volume=Decimal("1.973"))
                ],
                tariff_id="12"
            )
            # Note: The Calculator uses calculated duration from start_time/end_time difference.
            # 1.973h is approx what we get.
        ],
        total_energy=Decimal("15.342"),
        total_time=Decimal("1.973"),
        last_updated=datetime(2015, 6, 29, 22, 1, 13)
    )
    
    cost = calculate_cdr_cost(cdr, tariff)
    
    assert cost.excl_vat == Decimal("4.00")
    assert cost.incl_vat == Decimal("4.40")

def test_simple_energy_tariff_with_step_size():
    """
    Based on spec text: 4.3 kWh + 1.1 kWh, step size 0.5 kWh.
    Total: 5.4 -> 5.5 kWh.
    Price: 0.20 and 0.27.
    """
    # ... This requires two periods with different prices.
    pass

def test_complex_tariff_restrictions():
    # TODO: Implement complex example from spec
    pass
