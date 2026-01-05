import math
from datetime import time
from typing import Optional

from ocpi_tariffs.core.enums import (
    CdrDimensionType,
    RoundingGranularity,
    RoundingRule,
)


def is_within_range(value: float, min_val: Optional[float], max_val: Optional[float]) -> bool:
    if min_val is not None and value < min_val:
        return False
    if max_val is not None and value >= max_val:
        return False
    return True


def is_in_time_range(start_time: time, end_time: time, check_time: time) -> bool:
    if start_time < end_time:
        return start_time <= check_time < end_time
    else:  # crosses midnight
        return check_time >= start_time or check_time < end_time


def apply_step_size_flags(charging_periods):
    # TODO: if flagged parking time , then no flag for time
    is_energy_flagged = False
    is_time_flagged = False

    for period in charging_periods[::-1]:
        for dim in period.dimensions:
            if dim.type == CdrDimensionType.ENERGY and not is_energy_flagged:
                dim.apply_step_size = True
                is_energy_flagged = True
            elif (
                dim.type == CdrDimensionType.TIME
                or dim.type == CdrDimensionType.PARKING_TIME
            ) and not is_time_flagged:
                dim.apply_step_size = True
                is_time_flagged = True

        # Stop once we've flagged both TIME and ENERGY
        if is_time_flagged and is_energy_flagged:
            break

    return charging_periods


def apply_rounding(
    volume: float, granularity: RoundingGranularity, round_rule: RoundingRule
):
    # Map granularity to decimal places
    granularity_map = {
        RoundingGranularity.UNIT: 0,
        RoundingGranularity.TENTH: 1,
        RoundingGranularity.HUNDREDTH: 2,
        RoundingGranularity.THOUSANDTH: 3,
    }

    # Get the number of decimals based on granularity
    decimals = granularity_map.get(granularity)
    if decimals is None:
        raise ValueError("Invalid granularity")

    # Scale factor to shift the decimal point
    scale = 10**decimals

    # Apply rounding rule
    if round_rule == RoundingRule.ROUND_UP:
        return math.ceil(volume * scale) / scale
    elif round_rule == RoundingRule.ROUND_DOWN:
        return math.floor(volume * scale) / scale
    elif round_rule == RoundingRule.ROUND_NEAR:
        return round(volume, decimals)
    else:
        raise ValueError("Invalid round rule")
