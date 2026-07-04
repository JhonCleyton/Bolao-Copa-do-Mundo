from pydantic import BaseModel, EmailStr, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums
class UserStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


class PVPBetType(str, Enum):
    MATCH = "match"
    ROUND = "round"
    CHAMPIONSHIP = "championship"


class PVPBetStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserVerifyEmail(BaseModel):
    email: EmailStr
    code: str


class UserVerifyPhone(BaseModel):
    phone: str
    code: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    status: UserStatus
    email_verified: bool
    phone_verified: bool
    registration_paid: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


class UserInDB(UserResponse):
    password_hash: str


# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Match Schemas
class MatchBase(BaseModel):
    match_number: int
    group: Optional[str] = None
    team_a: str
    team_b: str
    team_a_code: str
    team_b_code: str
    match_date: datetime
    local_time: str
    brasilia_time: str
    city: str
    stadium: str
    round_number: int = 1


class MatchCreate(MatchBase):
    pass


class MatchUpdateScore(BaseModel):
    score_a: int
    score_b: int
    status: MatchStatus
    penalty_winner: Optional[str] = None  # "A" ou "B" - vencedor nos penaltis


class MatchResponse(MatchBase):
    id: int
    stage: Optional[str] = None
    status: MatchStatus
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    penalty_winner: Optional[str] = None
    prediction_deadline: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_serializer('match_date', 'created_at', 'prediction_deadline')
    def serialize_datetime(self, dt: datetime) -> str:
        # Retorna formato ISO sem 'Z' para indicar horário local (Brasília)
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


# Prediction Schemas
class PredictionBase(BaseModel):
    match_id: int
    predicted_score_a: int = Field(..., ge=0, le=20)
    predicted_score_b: int = Field(..., ge=0, le=20)


class PredictionCreate(PredictionBase):
    pass


class PredictionResponse(PredictionBase):
    id: int
    user_id: int
    points_earned: int
    points_winner: int
    points_score_a: int
    points_score_b: int
    points_exact: int
    created_at: datetime
    match: Optional[MatchResponse] = None
    
    class Config:
        from_attributes = True
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


# Ranking Schemas
class RoundRankingResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    round_number: int
    total_points: int
    correct_predictions: int
    exact_scores: int
    position: Optional[int]
    prize_won: float
    calculated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_serializer('calculated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


class GeneralRankingResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    total_points: int
    correct_predictions: int
    exact_scores: int
    position: Optional[int]
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_serializer('updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


# Payment Schemas
class PaymentBase(BaseModel):
    type: str  # registration, round
    round_number: Optional[int] = None
    amount: float


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: int
    user_id: int
    paid: bool
    payment_date: Optional[datetime]
    transaction_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_serializer('payment_date', 'created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


# Notification Schemas
class NotificationSend(BaseModel):
    user_id: Optional[int] = None  # None = all users
    type: str  # email, whatsapp, both
    subject: str
    message: str


# Dashboard Schemas
class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_matches: int
    finished_matches: int
    total_predictions: int
    total_prizes: float


class UserDashboard(BaseModel):
    user: UserResponse
    total_points: int
    general_position: Optional[int]
    predictions_made: int
    predictions_correct: int
    exact_scores: int
    pending_payments: List[PaymentResponse]
    next_matches: List[MatchResponse]
    last_predictions: List[PredictionResponse]


# PVP Bet Schemas
class PVPBetCreate(BaseModel):
    challenged_id: int
    bet_type: PVPBetType
    match_id: Optional[int] = None
    round_number: Optional[int] = None
    prize_description: str = Field(..., min_length=1, max_length=200)
    prize_value: float = 0
    rules_description: Optional[str] = Field(None, max_length=500)
    expires_hours: int = Field(default=24, ge=1, le=168)  # Expira em 1 a 168 horas


class PVPBetAction(BaseModel):
    action: str  # accept, reject


class PVPBetResponse(BaseModel):
    id: int
    challenger_id: int
    challenger_name: str
    challenged_id: int
    challenged_name: str
    bet_type: PVPBetType
    match_id: Optional[int]
    round_number: Optional[int]
    prize_description: str
    prize_value: float
    rules_description: Optional[str]
    status: PVPBetStatus
    challenger_points: Optional[int]
    challenged_points: Optional[int]
    winner_id: Optional[int]
    winner_name: Optional[str]
    expires_at: Optional[datetime]
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    match: Optional[MatchResponse] = None

    class Config:
        from_attributes = True
    
    @field_serializer('expires_at', 'accepted_at', 'completed_at', 'created_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return dt.strftime('%Y-%m-%dT%H:%M:%S')


class PVPRankingResponse(BaseModel):
    user_id: int
    user_name: str
    total_bets: int
    bets_won: int
    bets_lost: int
    win_rate: float
    total_prizes_won: str

    class Config:
        from_attributes = True


class PVPChallengeNotification(BaseModel):
    bet_id: int
    challenger_name: str
    challenged_phone: str
    prize_description: str
    bet_type: PVPBetType
    match_details: Optional[str] = None
    round_number: Optional[int] = None
