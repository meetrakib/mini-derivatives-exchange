from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    display_name: str | None = Field(None, max_length=256)


class UserRead(BaseModel):
    user_id: str
    display_name: str | None = None

    class Config:
        from_attributes = True
