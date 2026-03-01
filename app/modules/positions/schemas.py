from pydantic import BaseModel


class PositionRead(BaseModel):
    id: int
    user_id: str
    symbol: str
    size: float
    entry_price: float

    class Config:
        from_attributes = True
