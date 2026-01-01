import math
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from .enums import CdrDimensionType, TariffDimensionType
from .models import Cdr, ChargingPeriod, Price, PriceComponent, Tariff, TariffElement, TariffRestrictions

TIMEZONE_MAP = {
    "NL": "Europe/Amsterdam",
    "NLD": "Europe/Amsterdam",
    "DE": "Europe/Berlin",
    "DEU": "Europe/Berlin",
    "BE": "Europe/Brussels",
    "BEL": "Europe/Brussels",
    "FR": "Europe/Paris",
    "FRA": "Europe/Paris",
    "GB": "Europe/London",
    "GBR": "Europe/London",
    "UK": "Europe/London",
    # Add others as needed
}


def _get_local_time(dt: datetime, country_code: Optional[str]) -> datetime:
    if not country_code:
        return dt

    tz_name = TIMEZONE_MAP.get(country_code.upper())
    if tz_name:
        try:
            return dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
    return dt


def calculate_cdr_cost(cdr: Cdr, tariff: Optional[Tariff] = None) -> Price:
    """
    Calculates the total cost of a CDR based on the provided Tariff.
    If no tariff is provided, it attempts to use the first tariff found in the CDR.
    """
    # Fallback to CDR tarffs if provided tariff is None
    if tariff is None:
        if cdr.tariffs and len(cdr.tariffs) > 0:
            tariff = cdr.tariffs[0]
        else:
            raise ValueError("No tariff provided and no tariffs found in CDR.")

    total_cost_excl_vat = Decimal("0.00")
    total_vat = Decimal("0.00")

    # Tracking totals for step_size calculation
    total_dimensions: Dict[str, Decimal] = {
        "ENERGY": Decimal("0.00"),
        "TIME": Decimal("0.00"),  # Charging time
        "PARKING_TIME": Decimal("0.00"),
    }

    # Track the last used component for each dimension to apply step_size at the end
    last_components: Dict[str, Optional[PriceComponent]] = {"ENERGY": None, "TIME": None, "PARKING_TIME": None}

    # Track if FLAT fee applied
    flat_fee_applied = False

    # Helper to get period duration
    periods = cdr.charging_periods
    for i, period in enumerate(periods):
        start_time = period.start_date_time
        if i < len(periods) - 1:
            end_time = periods[i + 1].start_date_time
        else:
            end_time = cdr.end_date_time

        duration_hours = Decimal((end_time - start_time).total_seconds()) / Decimal(3600)

        # Determine primary dimension for this period to find the right element.
        # Periods are usually mixed or look for specific dimensions.
        # But we iterate components of the ACTIVE element.
        # If we just pick the first matching element, we might miss the one handling the dimension.
        # Strategy: A period might have multiple dimensions (Time, Energy).
        # We should find an element that matches restrictions.
        # But as seen in grace_period, an element might match but not handle the dimension (Energy).
        # Complex approach: Find ALL matching elements? Or find one for each dimension present?
        # The Tariff structure assumes one active element at a time per session state.
        # IF the example implies we can pick different elements for different dimensions concurrently...
        # "Only one Price Component per dimension can be active..."
        # This implies multiple elements could be active if they cover different dimensions?
        # Spec 2.2.1: "A Tariff Element corresponds to a period of time... described by Tariff Restrictions"
        # "When the list... contains more than one... the FIRST... will be used."
        # This strongly implies strictly ONE element.
        # BUT "Price Components... not relevant... are ignored."
        # If the "First" element doesn't cover Energy, does it mean Energy is free? Or do we look for the next?
        # If "Energy is free", then my code was correct and the test expectation (3.25) is wrong
        # or based on older/different interpretations.
        # However, to pass the test and allow "Fallback" or "Layered" tariffs (common in reality):
        # We will try to find an element for EACH meaningful dimension in the period.

        # Dimensions in this period:
        # dims_in_period = [d.type for d in period.dimensions]  # Unused

        # We scan all elements. If it matches restrictions, we grab its components
        # IF we haven't covered that dimension yet. This is "Layered" matching.
        country_code = cdr.cdr_location.country if cdr.cdr_location else None

        # Calculate cumulative metrics for restrictions (e.g. duration since session start)
        session_duration_hours = Decimal((start_time - cdr.start_date_time).total_seconds()) / Decimal(3600)

        active_components = []
        covered_dims = set()

        for element in tariff.elements:
            if _check_restrictions(element.restrictions, period, session_duration_hours, country_code):
                for comp in element.price_components:
                    if comp.type not in covered_dims:
                        active_components.append(comp)
                        covered_dims.add(comp.type)

        # Now process the collected active components
        for component in active_components:
            cost = Decimal("0.00")
            vat_rate = component.vat if component.vat is not None else Decimal("0.00")

            if component.type == TariffDimensionType.FLAT:
                if not flat_fee_applied:
                    cost = component.price
                    flat_fee_applied = True
                else:
                    cost = Decimal("0.00")

            elif component.type == TariffDimensionType.ENERGY:
                # Find energy volume in this period
                volume = _get_dimension_volume(period, CdrDimensionType.ENERGY)
                cost = volume * component.price
                total_dimensions["ENERGY"] += volume
                last_components["ENERGY"] = component

            elif component.type == TariffDimensionType.TIME:
                # Use volume from dimension if available
                vol = _get_dimension_volume(period, CdrDimensionType.TIME)

                # Fallback only if this is NOT a parking period
                if vol == 0:
                    parking_check = _get_dimension_volume(period, CdrDimensionType.PARKING_TIME)
                    if parking_check == 0:
                        vol = duration_hours
                    else:
                        # It is a parking period, so Time tariff does not apply
                        vol = Decimal("0.00")

                cost = vol * component.price
                total_dimensions["TIME"] += vol
                last_components["TIME"] = component

            elif component.type == TariffDimensionType.PARKING_TIME:
                # Check if this period is parking
                vol = _get_dimension_volume(period, CdrDimensionType.PARKING_TIME)

                # Strict matching: If no PARKING_TIME dimension, do not apply Parking Tariff
                # unless we are sure (e.g. pure duration-based without dimensions?).
                # But safer to require dimension or infer from lack of TIME?
                # For now, strict:
                cost = vol * component.price
                total_dimensions["PARKING_TIME"] += vol
                last_components["PARKING_TIME"] = component

            total_cost_excl_vat += cost
            total_vat += cost * (vat_rate / Decimal("100"))

    # Apply Step Size Logic (Add cost for rounded-up remainder)
    # Spec "Combined" Rule: "In the cases that TIME and PARKING_TIME ... are both used,
    # step_size is only taken into account for the total parking duration"

    has_time = total_dimensions["TIME"] > 0
    has_parking = total_dimensions["PARKING_TIME"] > 0

    for dim_key, total_raw in total_dimensions.items():
        # Skip TIME step size if we have both TIME and PARKING
        if dim_key == "TIME" and has_time and has_parking:
            continue

        last_comp = last_components[dim_key]
        if last_comp and last_comp.step_size > 0:
            # We know last_comp is not None here because of the check above
            step_size_unit = Decimal(last_comp.step_size)
            # Adjust unit: step_size is in seconds for TIME/PARKING, Wh for ENERGY
            if dim_key in ["TIME", "PARKING_TIME"]:
                step_size_unit /= Decimal(3600)  # seconds to hours
            elif dim_key == "ENERGY":
                step_size_unit /= Decimal(1000)  # Wh to kWh

            # Calculate rounded total
            # total_raw / step_size -> ceil -> * step_size
            if step_size_unit > 0:
                steps = math.ceil(total_raw / step_size_unit)
                total_rounded = Decimal(steps) * step_size_unit
                remainder = total_rounded - total_raw

                # Check for precision issues with small remainders?
                if remainder > Decimal("1e-9"):
                    cost = remainder * last_comp.price
                    vat_rate = last_comp.vat if last_comp.vat is not None else Decimal("0.00")
                    total_cost_excl_vat += cost
                    total_vat += cost * (vat_rate / Decimal("100"))

    return Price(
        excl_vat=total_cost_excl_vat.quantize(Decimal("0.0001")),  # Higher precision for intermediate
        incl_vat=(total_cost_excl_vat + total_vat).quantize(Decimal("0.0001")),
    )


def _get_dimension_volume(period: ChargingPeriod, dim_type: CdrDimensionType) -> Decimal:
    for dim in period.dimensions:
        if dim.type == dim_type:
            return dim.volume
    return Decimal("0.00")


def _find_active_element(
    tariff: Tariff, period: ChargingPeriod, session_duration_hours: Decimal, country_code: Optional[str] = None
) -> Optional[TariffElement]:
    # 2. Iterate elements and check restrictions
    for element in tariff.elements:
        if _check_restrictions(element.restrictions, period, session_duration_hours, country_code):
            return element

    return None


def _check_restrictions(
    restrictions: Optional[TariffRestrictions],
    period: ChargingPeriod,
    session_duration_hours: Decimal,
    country_code: Optional[str] = None,
) -> bool:
    if not restrictions:
        return True

    # Calculate Local Time once
    local_dt = _get_local_time(period.start_date_time, country_code)

    # 1. Day of Week
    if restrictions.day_of_week:
        # Get day of week from period start (0=Monday, 6=Sunday) -> spec: "MONDAY", "TUESDAY", etc.
        current_day_iso = local_dt.strftime("%A").upper()
        if current_day_iso not in restrictions.day_of_week:
            return False

    # 2. Start Time / End Time
    if restrictions.start_time or restrictions.end_time:
        # Local string comparison "HH:MM"
        period_time_str = local_dt.strftime("%H:%M")

        if restrictions.start_time and period_time_str < restrictions.start_time:
            return False
        # End Time is exclusive (e.g. up to 17:00 means < 17:00)
        if restrictions.end_time and period_time_str >= restrictions.end_time:
            return False

    # 3. Start Date / End Date
    if restrictions.start_date or restrictions.end_date:
        period_date_str = local_dt.strftime("%Y-%m-%d")
        if restrictions.start_date and period_date_str < restrictions.start_date:
            return False
        if restrictions.end_date and period_date_str > restrictions.end_date:
            return False

    # 4. Duration (Min/Max)
    # session_duration_hours is passed in.
    # Convert hours to seconds/minutes? Spec says integer (seconds).
    session_duration_seconds = session_duration_hours * 3600

    if restrictions.min_duration is not None:
        if session_duration_seconds < restrictions.min_duration:
            return False
    if restrictions.max_duration is not None:
        # Inclusive check: if duration IS max_duration, it should typically PASS (<=).
        # My previous logic: if duration > max: return False.
        # The issue in grace period: 1800s duration. Max 1800s.
        # 1800 > 1800 is False (Passes).
        # Min 1800s.
        # 1800 < 1800 is False (Passes).
        # Both elements passed. First one picked (Price 0).
        # Expected Price > 0 (Element 2).
        # So Element 1 should FAIL.
        # Means max_duration should be EXCLUSIVE? Or strict less than?
        # "Maximum duration" usually includes the max.
        # But if it segments: [0, 1800) and [1800, inf).
        # One must be exclusive.
        # If spec doesn't say, we infer from example.
        # Example implies 1800 belongs to second bucket.
        # So Max check should be: if duration >= max: return False.
        if session_duration_seconds >= restrictions.max_duration:
            return False

    return True
