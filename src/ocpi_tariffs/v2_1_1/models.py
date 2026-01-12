from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import AfterValidator, BaseModel, Field, model_validator

from ocpi_tariffs.core.enums import (
    CdrDimensionType,
    DayOfWeek,
    RoundingGranularity,
    RoundingRule,
    TariffDimensionType,
)
from ocpi_tariffs.core.utils import (
    apply_rounding,
    apply_step_size_flags,
    is_in_time_range,
    is_within_range,
)

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self  # 3.10


class Rounding(BaseModel):
    round_granularity: RoundingGranularity
    round_rule: RoundingRule


class PriceComponent(BaseModel):
    type: TariffDimensionType
    price: float
    step_size: int

    # Specific properties added by Gireve
    price_round: Rounding = Field(
        default_factory=lambda: Rounding(
            round_granularity=RoundingGranularity.THOUSANDTH,
            round_rule=RoundingRule.ROUND_NEAR,
        )
    )
    step_round: Rounding = Field(
        default_factory=lambda: Rounding(
            round_granularity=RoundingGranularity.UNIT,
            round_rule=RoundingRule.ROUND_UP,
        )
    )
    exact_price_component: Optional[bool] = None


class TariffRestrictions(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_kwh: Optional[float] = None
    max_kwh: Optional[float] = None
    min_power: Optional[float] = None
    max_power: Optional[float] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None

    # Durations for charging time in second
    min_charge_duration: Optional[int] = None
    max_charge_duration: Optional[int] = None

    # Duration for parking time in seconds
    min_parking_duration: Optional[int] = None
    max_parking_duration: Optional[int] = None

    # Duration for session time in seconds
    min_session_duration: Optional[int] = None
    max_session_duration: Optional[int] = None

    day_of_week: Optional[List[DayOfWeek]] = None

    def is_valid_at_start_date_time(self, start_date_time: datetime) -> bool:
        """
        Checks if this restriction is valid at `start_date_time`.
        The time based restrictions are treated as exclusive comparisons.
        """
        # Validate start_time and end_time
        if self.start_time and self.end_time:
            start_time = datetime.strptime(self.start_time, "%H:%M").time()
            end_time = datetime.strptime(self.end_time, "%H:%M").time()

            if not is_in_time_range(start_time, end_time, start_date_time.time()):
                return False

        # Validate start_date and end_date
        if self.start_date and self.end_date:
            start_date = datetime.strptime(self.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date, "%Y-%m-%d").date()
            if not (start_date <= start_date_time.date() < end_date):
                return False

        # Validate day_of_week
        if self.day_of_week:
            # Convert to uppercase for comparison
            day_name = start_date_time.strftime("%A").upper()
            if day_name not in self.day_of_week:
                return False

        return True

    def _is_valid_at_duration(
        self, duration_hours: float, min_seconds: float, max_seconds: float
    ) -> bool:
        """Check if a duration (in hours) falls within a specified range (in seconds)."""
        duration_seconds = duration_hours * 3600  # Convert hours to seconds
        return is_within_range(duration_seconds, min_seconds, max_seconds)

    def is_valid_at_session_duration(self, duration: float) -> bool:
        return self._is_valid_at_duration(
            duration, self.min_session_duration, self.max_session_duration
        )

    def is_valid_at_charge_duration(self, duration_hours: float) -> bool:
        return self._is_valid_at_duration(
            duration_hours, self.min_charge_duration, self.max_charge_duration
        )

    def is_valid_at_parking_duration(self, duration: float) -> bool:
        return self._is_valid_at_duration(
            duration, self.min_parking_duration, self.max_parking_duration
        )

    def is_valid_at_energy(self, energy: float):
        return is_within_range(energy, self.min_kwh, self.max_kwh)


class TariffElement(BaseModel):
    price_components: List[PriceComponent]
    restrictions: Optional[TariffRestrictions] = None

    @model_validator(mode="after")
    def process_restrictions(self) -> Self:
        """
        Process and set tariff restrictions based on price component types.
        """
        if not self.restrictions:
            return self

        # Process each price component using enum values
        for component in self.price_components:
            match component.type:
                case TariffDimensionType.TIME:
                    self.restrictions.min_charge_duration = (
                        self.restrictions.min_duration
                    )
                    self.restrictions.max_charge_duration = (
                        self.restrictions.max_duration
                    )
                case TariffDimensionType.PARKING_TIME:
                    self.restrictions.min_parking_duration = (
                        self.restrictions.min_duration
                    )
                    self.restrictions.max_parking_duration = (
                        self.restrictions.max_duration
                    )
                case TariffDimensionType.SESSION_TIME:
                    self.restrictions.min_session_duration = (
                        self.restrictions.min_duration
                    )
                    self.restrictions.max_session_duration = (
                        self.restrictions.max_duration
                    )

        return self

    def is_active(self, state) -> bool:
        if self.restrictions is None:
            return True
        return (
            self.restrictions.is_valid_at_start_date_time(state.start_date_time)
            and self.restrictions.is_valid_at_energy(state.energy)
            and self.restrictions.is_valid_at_session_duration(state.charging_time + state.parking_time)
            and self.restrictions.is_valid_at_charge_duration(state.charging_time)
            and self.restrictions.is_valid_at_parking_duration(state.parking_time)
        )


class PriceComponents(BaseModel):
    flat: Optional[PriceComponent] = None
    energy: Optional[PriceComponent] = None
    parking: Optional[PriceComponent] = None
    time: Optional[PriceComponent] = None

    def has_all_components(self) -> bool:
        return all([self.flat, self.energy, self.parking, self.time])


class Tariff(BaseModel):
    id: str
    currency: str
    # tariff_alt_text: List[DisplayText] = []
    tariff_alt_url: Optional[str] = None
    elements: List[TariffElement]
    # energy_mix: Optional[EnergyMix]
    #last_updated: datetime

    def active_components(self, state) -> PriceComponents:
        components = PriceComponents()
        for tariff_element in self.elements:
            if not tariff_element.is_active(state):
                continue

            for price_component in tariff_element.price_components:
                if components.flat is None and price_component.type == TariffDimensionType.FLAT:
                    components.flat = price_component
                elif components.energy is None and price_component.type == TariffDimensionType.ENERGY:
                    components.energy = price_component
                elif components.parking is None and price_component.type == TariffDimensionType.PARKING_TIME:
                    components.parking = price_component
                elif components.time is None and price_component.type == TariffDimensionType.TIME:
                    components.time = price_component
                elif components.time is None and components.parking is None and price_component.type == TariffDimensionType.SESSION_TIME:
                    components.parking = price_component
                    components.time = price_component

                if components.has_all_components():
                    break

        return components


class CdrDimension(BaseModel):
    type: CdrDimensionType
    volume: float
    billed_volume: float = 0
    total_cost: float = 0
    apply_step_size: bool = False

    def get_billed_volume(self, component: PriceComponent, total_volume : float):
        if not self.apply_step_size:
            return self.volume

        if self.type in [CdrDimensionType.TIME, CdrDimensionType.PARKING_TIME]:
            factor = 3600
        elif self.type == CdrDimensionType.ENERGY:
            factor = 1000
        else:
             factor = 1 # Default or error?

        volume_step_size = ((self.volume + total_volume) * factor) / component.step_size
        rounded_volume_step_size = apply_rounding(
            volume_step_size,
            component.step_round.round_granularity,
            component.step_round.round_rule,
        )
        billed_volume = (rounded_volume_step_size * component.step_size / factor) - total_volume

        return billed_volume

    def cost(self, components: PriceComponents, state) -> float:
        if self.type == CdrDimensionType.ENERGY:
            component = components.energy
            total_volume = state.energy
        elif self.type == CdrDimensionType.PARKING_TIME:
            component = components.parking
            total_volume = state.parking_time
        elif self.type == CdrDimensionType.TIME:
            component = components.time
            total_volume = state.charging_time
        else:
            component = None
            total_volume = 0


        if component is None:
            # logging.debug(f"No costs for Tariff Dimension : {self.type}")
            return 0

        self.billed_volume = self.get_billed_volume(component, total_volume)

        self.total_cost = apply_rounding(
            component.price * self.billed_volume,
            component.price_round.round_granularity,
            component.price_round.round_rule,
        )
        return self.total_cost


class ChargingPeriod(BaseModel):
    start_date_time: datetime
    dimensions: List[CdrDimension]


class Cdr(BaseModel):
    id: str
    meter_id: Optional[str] = None
    currency: str
    # tariffs: List[Tariff] = []
    charging_periods: Annotated[
        List[ChargingPeriod], AfterValidator(apply_step_size_flags)
    ]
    total_cost: Optional[float] = None
    total_energy: Optional[float] = None
    total_time: Optional[float] = None
    total_parking_time: Optional[float] = None
