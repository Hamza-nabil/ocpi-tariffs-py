from datetime import datetime

from pydantic import BaseModel

from ocpi_tariffs.core.enums import CdrDimensionType
from ocpi_tariffs.core.utils import apply_rounding
from ocpi_tariffs.v2_1_1.models import Cdr, CdrDimension, Tariff


class State(BaseModel):
    parking_time: float = 0
    billed_parking_time: float = 0
    total_parking_cost: float = 0

    charging_time: float = 0
    billed_charging_time: float = 0
    total_charging_time_cost: float = 0

    energy: float = 0
    billed_energy: float = 0
    total_energy_cost: float = 0

    total_fixed_cost: float = 0

    total_cost: float = 0

    total_time: float = 0

    start_date_time: datetime = None

    def update_start_date_time(self, start_date_time: datetime):
        # Update start_date_time
        self.start_date_time = start_date_time

        return True
    
    def update_dimension(self, dimension: CdrDimension):
        # Update a single dimension based on its type
        if dimension.type == CdrDimensionType.ENERGY:
            self.energy += dimension.volume
            self.billed_energy += dimension.billed_volume
            self.total_energy_cost += dimension.total_cost
        elif dimension.type == CdrDimensionType.PARKING_TIME:
            self.parking_time += dimension.volume
            self.billed_parking_time += dimension.billed_volume
            self.total_parking_cost += dimension.total_cost
        elif dimension.type == CdrDimensionType.TIME:
            self.charging_time += dimension.volume
            self.billed_charging_time += dimension.billed_volume
            self.total_charging_time_cost += dimension.total_cost


class Pricer(BaseModel):
    cdr: Cdr
    tariff: Tariff

    def calculate_total_cost_details(self) -> State:
        has_flat_fee = False
        # Store information we need t use while charging
        state = State()
        for period in self.cdr.charging_periods:
            # update the state start time 
            state.update_start_date_time(period.start_date_time)
            active_components = self.tariff.active_components(state)

            # Make sure the FLAT is used only once for all the Session
            flat_component = active_components.flat
            if flat_component and not has_flat_fee:
                state.total_fixed_cost = apply_rounding(
                    flat_component.price,
                    flat_component.price_round.round_granularity,
                    flat_component.price_round.round_rule,
                )
                state.total_cost += state.total_fixed_cost
                has_flat_fee = True

            for dimension in period.dimensions:
                state.total_cost += dimension.cost(active_components, state)
                # update total energy and time
                state.update_dimension(dimension)

        return state

    def calculate_total_cost(self) -> float:
        """Calculate the total cost based on the tariff and CDR data."""
        state = self.calculate_total_cost_details()
        return state.total_cost


def calculate_cdr_cost(cdr: Cdr, tariff: Tariff) -> float:
    """
    Wrapper function to calculate CDR cost, matching the API style of v2.2.1.
    """
    pricer = Pricer(cdr=cdr, tariff=tariff)
    return pricer.calculate_total_cost()
