from pydantic import BaseModel, Field
from backend.app.models.enums import UserRole, LoyaltyTier

class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(min_length=6, max_length=64)
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole = Field(default=UserRole.PASSENGER)
    loyalty_tier: LoyaltyTier = Field(default=LoyaltyTier.NONE)

class UserLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str
    loyalty_tier: str

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    loyalty_tier: str
