from pydantic import BaseModel, Field
from typing import Optional

class DepositRecord(BaseModel):
    bank_name: str
    country: Optional[str] = None
    currency: str
    product: Optional[str] = None
    rate_apr: float = Field(..., ge=0)
    link: Optional[str] = None
    source: Optional[str] = None
    fetched_at: Optional[str] = None
