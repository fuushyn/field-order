from pydantic import BaseModel
from datetime import datetime


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rep_name: str
    rep_id: int


# Retailer
class RetailerOut(BaseModel):
    id: int
    name: str
    address: str
    contact_phone: str | None
    contact_email: str | None
    rep_id: int

    model_config = {"from_attributes": True}


# Product
class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    unit_price: float
    unit: str
    in_stock: bool

    model_config = {"from_attributes": True}


# Order
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    retailer_id: int
    items: list[OrderItemCreate]


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    retailer_id: int
    retailer_name: str = ""
    rep_id: int
    status: str
    total: float
    created_at: datetime
    items: list[OrderItemOut] = []

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str
