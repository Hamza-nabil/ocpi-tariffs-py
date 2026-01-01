from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from .enums import TariffDimensionType, CdrDimensionType, AuthMethod

class Price(BaseModel):
    excl_vat: Decimal
    incl_vat: Optional[Decimal] = None

class PriceComponent(BaseModel):
    type: TariffDimensionType
    price: Decimal
    vat: Optional[Decimal] = None
    step_size: int

class TariffRestrictions(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_kwh: Optional[Decimal] = None
    max_kwh: Optional[Decimal] = None
    min_current: Optional[Decimal] = None
    max_current: Optional[Decimal] = None
    min_power: Optional[Decimal] = None
    max_power: Optional[Decimal] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    day_of_week: Optional[List[str]] = None
    reservation: Optional[str] = None # RESERVATION, RESERVATION_EXPIRES

class TariffElement(BaseModel):
    price_components: List[PriceComponent]
    restrictions: Optional[TariffRestrictions] = None

class Tariff(BaseModel):
    id: str
    currency: str
    elements: List[TariffElement]
    min_price: Optional[Price] = None
    max_price: Optional[Price] = None
    start_date_time: Optional[datetime] = None
    end_date_time: Optional[datetime] = None
    last_updated: datetime

class CdrDimension(BaseModel):
    type: CdrDimensionType
    volume: Decimal

class ChargingPeriod(BaseModel):
    start_date_time: datetime
    dimensions: List[CdrDimension]
    tariff_id: Optional[str] = None

class Cdr(BaseModel):
    id: Optional[str] = Field(default_factory=str)
    start_date_time: datetime
    end_date_time: datetime
    currency: str
    tariffs: List[Tariff] = Field(default_factory=list)
    charging_periods: List[ChargingPeriod]
    total_cost: Optional[Price] = None
    total_energy: Decimal
    total_time: Decimal # hours
    total_parking_time: Optional[Decimal] = None # hours
    last_updated: datetime
