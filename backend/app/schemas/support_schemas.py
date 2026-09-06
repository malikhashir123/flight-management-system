from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from backend.app.models.enums import ApprovalStatus

class CustomerSupportInquiryRequest(BaseModel):
    booking_reference: Optional[str] = Field(default=None, description="Booking PNR e.g. FMS-8291A")
    customer_email: str = Field(min_length=5, max_length=255)
    query: str = Field(min_length=5, max_length=2000)

class SupportDraftResponse(BaseModel):
    id: str
    booking_id: Optional[str]
    customer_email: str
    customer_query: str
    rag_drafted_answer: str
    approval_status: ApprovalStatus
    created_at: datetime

class HumanApprovalActionRequest(BaseModel):
    action: str = Field(description="'APPROVE' or 'REJECT'")
    notes: Optional[str] = None
