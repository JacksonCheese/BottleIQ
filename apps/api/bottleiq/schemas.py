from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Signup(Credentials):
    name: str = Field(min_length=1, max_length=120)
    organization_name: str = Field(min_length=1, max_length=160)


class StoreInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    timezone: str = "America/Los_Angeles"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Use an IANA timezone such as America/Los_Angeles") from exc
        return value


class AnalysisOptions(BaseModel):
    window: Literal[30, 60, 90] = 60
    target_days: int = Field(default=21, ge=7, le=60)
    service_level: float = Field(default=0.95, ge=0.8, le=0.999)
    dead_days: int = Field(default=90, ge=30, le=365)
    slow_days: int = Field(default=90, ge=30, le=365)


class GenerateInput(AnalysisOptions):
    store_id: str


class OrderInput(GenerateInput):
    vendor_id: str


class OrderLineEdit(BaseModel):
    product_id: str
    cases: int = Field(ge=0, le=10000)


class OrderEdit(BaseModel):
    version: int = Field(ge=1)
    lines: list[OrderLineEdit] = Field(max_length=1000)


class ProductEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_vendor_id: str | None = None
    units_per_case: int = Field(ge=1, le=1000)
    category: str = Field(min_length=1, max_length=80)
    brand: str = Field(max_length=120)


class VendorInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    default_lead_time_days: int = Field(default=4, ge=0, le=90)
    minimum_order_amount: float | None = Field(default=None, ge=0, le=10000000)


class Metrics(BaseModel):
    product_id: str
    sku: str
    upc: str | None
    product_name: str
    brand: str
    category: str
    size: str
    vendor_id: str | None
    vendor_name: str | None
    units_per_case: int
    snapshot_at: date | None
    current_quantity: int
    unit_cost: float | None
    retail_price: float
    inventory_value: float | None
    margin: float | None
    sales_30: int
    sales_90: int
    revenue_90: float
    gross_profit: float | None
    average_daily_demand: float
    demand_std: float
    lead_time_days: int
    safety_stock: float
    reorder_point: float
    target_stock: float
    days_of_supply: float | None
    turnover: float | None
    gmroi: float | None
    inventory_average_estimated: bool
    sell_through: float
    dead: bool
    slow: bool
    stockout: bool
    abnormal_demand: bool
    abc: str = "C"
    status: str
    recommended_units: int
    recommended_cases: int
    estimated_cost: float | None
    explanation: str
    blockers: list[str]
    sales_history: list[dict]


class Alert(BaseModel):
    severity: str
    title: str
    description: str
    product_id: str
    product_name: str
    financial_impact: float | None
    recommended_action: str
