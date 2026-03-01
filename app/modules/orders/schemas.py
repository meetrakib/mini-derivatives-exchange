from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    symbol: str = Field(default="BTC-PERP", max_length=64)
    side: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(..., pattern="^(limit|market)$")
    price: float | None = Field(None, gt=0)
    quantity: float = Field(..., gt=0)


class OrderRead(BaseModel):
    id: int
    user_id: str
    symbol: str
    side: str
    order_type: str
    price: float | None
    quantity: float
    filled_quantity: float
    status: str

    class Config:
        from_attributes = True


class OrderBookLevel(BaseModel):
    price: float
    quantity: float


class OrderBookRead(BaseModel):
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
