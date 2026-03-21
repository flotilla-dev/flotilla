from pydantic import BaseModel, Field
from datetime import datetime


class ResumeTokenPayload(BaseModel):
    thread_id: str = Field(..., description="ID of the thread that was supspended")
    phase_id: str = Field(..., description="ID of the phase that was suspended")
    suspend_entry_id: str = Field(..., description="The ID of the SuspendEntry that created the token")
    issued_at: datetime = Field(..., description="Timestamp when the token was issued")
    expires_at: datetime = Field(..., description="Time when the token expires")
