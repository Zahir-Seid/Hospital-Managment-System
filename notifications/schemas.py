from pydantic import BaseModel
from datetime import datetime

class NotificationCreate(BaseModel):
    recipient_id: int
    message: str

class NotificationOut(BaseModel):
    id: int
    recipient: str
    message: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
