from pydantic import BaseModel, Field
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    receiver_id: int


class MessageResponse(BaseModel):
    id: int
    content: str
    sender_id: int
    receiver_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    reset_token: str
    new_password: str



