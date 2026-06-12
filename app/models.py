from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class PVPBetType(str, enum.Enum):
    MATCH = "match"  # Aposta em uma partida específica
    ROUND = "round"  # Aposta em uma rodada inteira
    CHAMPIONSHIP = "championship"  # Aposta no campeonato inteiro


class PVPBetStatus(str, enum.Enum):
    PENDING = "pending"  # Aguardando aceitação
    ACCEPTED = "accepted"  # Desafiado aceitou
    REJECTED = "rejected"  # Desafiado recusou
    CANCELLED = "cancelled"  # Desafiante cancelou
    COMPLETED = "completed"  # Aposta finalizada
    EXPIRED = "expired"  # Expirou antes da aceitação


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


class Stage(str, enum.Enum):
    GROUP_STAGE = "group_stage"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL = "final"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    phone = Column(String)
    avatar = Column(String, nullable=True)  # Path to avatar image
    bio = Column(String, nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    email_verification_code = Column(String, nullable=True)
    phone_verification_code = Column(String, nullable=True)
    registration_paid = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    predictions = relationship("Prediction", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    round_rankings = relationship("RoundRanking", back_populates="user")


class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    match_number = Column(Integer, unique=True)
    group = Column(String, nullable=True)
    stage = Column(Enum(Stage), default=Stage.GROUP_STAGE)
    team_a = Column(String)
    team_b = Column(String)
    team_a_code = Column(String)
    team_b_code = Column(String)
    match_date = Column(DateTime)
    local_time = Column(String)
    brasilia_time = Column(String)
    city = Column(String)
    stadium = Column(String)
    status = Column(Enum(MatchStatus), default=MatchStatus.SCHEDULED)
    score_a = Column(Integer, nullable=True)
    score_b = Column(Integer, nullable=True)
    round_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    predictions = relationship("Prediction", back_populates="match")


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    match_id = Column(Integer, ForeignKey("matches.id"))
    predicted_score_a = Column(Integer)
    predicted_score_b = Column(Integer)
    points_earned = Column(Integer, default=0)
    points_winner = Column(Integer, default=0)
    points_score_a = Column(Integer, default=0)
    points_score_b = Column(Integer, default=0)
    points_exact = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)  # registration, round
    round_number = Column(Integer, nullable=True)
    amount = Column(Float)
    paid = Column(Boolean, default=False)
    payment_date = Column(DateTime, nullable=True)
    transaction_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="payments")


class RoundRanking(Base):
    __tablename__ = "round_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    round_number = Column(Integer)
    total_points = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    exact_scores = Column(Integer, default=0)
    position = Column(Integer, nullable=True)
    prize_won = Column(Float, default=0)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="round_rankings")


class GeneralRanking(Base):
    __tablename__ = "general_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_points = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    exact_scores = Column(Integer, default=0)
    position = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class GroupStanding(Base):
    """Automatic group standings table - updated when matches finish"""
    __tablename__ = "group_standings"
    
    id = Column(Integer, primary_key=True, index=True)
    group = Column(String, index=True)  # A, B, C, D, E, F, G, H, I, J, K, L
    team = Column(String)
    team_code = Column(String)
    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_difference = Column(Integer, default=0)
    points = Column(Integer, default=0)
    position = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PrizeConfiguration(Base):
    """Configuration for round prizes and winners"""
    __tablename__ = "prize_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer, unique=True)  # 0 = general ranking final
    total_prize = Column(Float, default=100.0)  # Total prize for the round
    num_winners = Column(Integer, default=1)  # Number of winners (1, 2, 3, etc.)
    # Prize distribution as JSON: {"1": 50, "2": 30, "3": 20} = percentages
    distribution = Column(String, default='{"1": 100}')  # Default: 1 winner gets 100%
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RoundNotification(Base):
    """Track which round notifications have been sent"""
    __tablename__ = "round_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    round_number = Column(Integer)
    notification_type = Column(String)  # 'start' or 'end'
    sent_at = Column(DateTime, default=datetime.utcnow)
    total_users_notified = Column(Integer, default=0)


class CarouselImage(Base):
    """Carousel images for landing page"""
    __tablename__ = "carousel_images"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    subtitle = Column(String, nullable=True)
    image_url = Column(String)  # URL or path to image
    button_text = Column(String, nullable=True)
    button_link = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduledMessage(Base):
    """Manual messages sent or scheduled by admin"""
    __tablename__ = "scheduled_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)  # internal title/description
    subject = Column(String)  # email subject / WhatsApp header
    message = Column(String)  # message body
    channel = Column(String)  # email, whatsapp, both
    target_type = Column(String)  # all, active, user
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)  # null = send immediately
    sent_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending, sent, failed, cancelled
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    recurrence = Column(String, nullable=True)  # null, daily, weekly, monthly
    next_run = Column(DateTime, nullable=True)  # for recurring messages
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class LandingPageConfig(Base):
    """Landing page configuration"""
    __tablename__ = "landing_page_config"
    
    id = Column(Integer, primary_key=True, index=True)
    hero_title = Column(String, default="Bolão Copa 2026")
    hero_subtitle = Column(String, default="O Maior Bolão do Brasil")
    hero_description = Column(String, default="Participe do bolão mais emocionante da Copa do Mundo 2026. Palpites, rankings e prêmios!")
    primary_color = Column(String, default="#1e3c72")
    secondary_color = Column(String, default="#2a5298")
    accent_color = Column(String, default="#ffc107")
    show_countdown = Column(Boolean, default=True)
    show_prize_section = Column(Boolean, default=True)
    show_features = Column(Boolean, default=True)
    show_testimonials = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PVPBet(Base):
    """Apostas PVP (Player vs Player) entre usuários"""
    __tablename__ = "pvp_bets"

    id = Column(Integer, primary_key=True, index=True)
    challenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenged_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Tipo de aposta
    bet_type = Column(Enum(PVPBetType), nullable=False)

    # Referências (dependendo do tipo)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    round_number = Column(Integer, nullable=True)

    # Detalhes da aposta
    prize_description = Column(String, nullable=False)  # ex: "Coca-Cola", "R$ 50,00"
    prize_value = Column(Float, default=0)  # Valor monetário se houver
    rules_description = Column(String, nullable=True)  # Regras adicionais

    # Status
    status = Column(Enum(PVPBetStatus), default=PVPBetStatus.PENDING)

    # Pontuações calculadas após finalização
    challenger_points = Column(Integer, nullable=True)
    challenged_points = Column(Integer, nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Datas
    expires_at = Column(DateTime, nullable=True)  # Expiração do desafio
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    challenger = relationship("User", foreign_keys=[challenger_id], backref="pvp_challenges_sent")
    challenged = relationship("User", foreign_keys=[challenged_id], backref="pvp_challenges_received")
    winner = relationship("User", foreign_keys=[winner_id])
    match = relationship("Match")
