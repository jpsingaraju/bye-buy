from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class PollingStatusResponse(BaseModel):
    running: bool
    cycle_count: int = 0
    last_poll_at: Optional[datetime] = None
    errors: list[str] = []
