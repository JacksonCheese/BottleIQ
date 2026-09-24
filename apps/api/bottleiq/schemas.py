from datetime import date, datetime
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
    window: int = 60

    @field_validator("window")
    @classmethod
    def supported_window(cls, value: int) -> int:
        if value not in (30, 60, 90):
            raise ValueError("Demand window must be 30, 60, or 90 days")
        return value

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


class IncomingInput(BaseModel):
    store_id: str
    product_id: str
    quantity_units: int = Field(ge=1, le=1_000_000)
    expected_at: date
    reference: str | None = Field(default=None, max_length=100)


class IncomingUpdate(BaseModel):
    status: Literal["resolved"]


class ReceiptInput(BaseModel):
    quantity_units: int = Field(ge=1, le=1_000_000)


class ReceiptView(BaseModel):
    id: str
    quantity_units: int
    received_at: datetime
    recorded_by_user_id: str


class IncomingView(BaseModel):
    id: str
    store_id: str
    product_id: str
    quantity_units: int
    expected_at: date
    reference: str | None
    status: Literal["open", "resolved"]
    received_units: int = 0
    remaining_units: int = 0
    last_received_at: datetime | None = None
    receipts: list[ReceiptView] = Field(default_factory=list)


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
    incoming_units: int
    inventory_position: int
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


class StoreView(BaseModel):
    id: str
    name: str
    timezone: str


class VendorView(BaseModel):
    id: str
    name: str
    default_lead_time_days: int
    minimum_order_amount: float | None


class RejectedRow(BaseModel):
    row: int
    message: str


class ImportJobView(BaseModel):
    id: str
    filename: str
    import_type: str
    status: str
    row_count: int
    rows_imported: int
    rows_rejected: int
    rows_duplicate: int
    error_summary: list[RejectedRow]
    created_at: datetime


class OrderLineView(BaseModel):
    product_id: str
    sku: str
    product_name: str
    cases: int
    units: int
    units_per_case: int
    unit_cost: float
    line_total: float
    explanation: str


class OrderView(BaseModel):
    id: str
    store_id: str
    vendor_id: str
    vendor_name: str
    generated_at: datetime
    status: str
    version: int
    estimated_total_cost: float
    minimum_order_amount: float | None
    below_minimum: bool
    lines: list[OrderLineView]


class CategoryValue(BaseModel):
    name: str
    value: float


class DashboardView(BaseModel):
    inventory_value: float
    slow_value: float
    dead_value: float
    stockout_risks: int
    recommended_reorders: int
    order_cost: float
    missing_cost_count: int
    categories: list[CategoryValue]
    statuses: dict[str, int]
    attention: list[Alert]
    top_profit: list[Metrics]
    cash_tied_up: list[Metrics]
    actions: list[Metrics]
    product_count: int
    latest_snapshot: date | None
