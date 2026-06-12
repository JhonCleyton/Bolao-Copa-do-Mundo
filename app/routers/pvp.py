from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import User, Match, Prediction, PVPBet, PVPBetType, PVPBetStatus
from app.schemas import (
    PVPBetCreate, PVPBetResponse, PVPBetAction,
    PVPRankingResponse, PVPChallengeNotification
)
from app.auth import get_current_user
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()


def _format_bet_response(bet: PVPBet, db: Session) -> dict:
    """Format PVP bet for response"""
    challenger = db.query(User).filter(User.id == bet.challenger_id).first()
    challenged = db.query(User).filter(User.id == bet.challenged_id).first()
    winner = db.query(User).filter(User.id == bet.winner_id).first() if bet.winner_id else None

    match = None
    if bet.match_id:
        match_obj = db.query(Match).filter(Match.id == bet.match_id).first()
        if match_obj:
            match = {
                "id": match_obj.id,
                "match_number": match_obj.match_number,
                "team_a": match_obj.team_a,
                "team_b": match_obj.team_b,
                "team_a_code": match_obj.team_a_code,
                "team_b_code": match_obj.team_b_code,
                "match_date": match_obj.match_date,
                "status": match_obj.status,
                "score_a": match_obj.score_a,
                "score_b": match_obj.score_b,
                "round_number": match_obj.round_number
            }

    return {
        "id": bet.id,
        "challenger_id": bet.challenger_id,
        "challenger_name": challenger.full_name if challenger else "Unknown",
        "challenged_id": bet.challenged_id,
        "challenged_name": challenged.full_name if challenged else "Unknown",
        "bet_type": bet.bet_type.value if hasattr(bet.bet_type, 'value') else bet.bet_type,
        "match_id": bet.match_id,
        "round_number": bet.round_number,
        "prize_description": bet.prize_description,
        "prize_value": bet.prize_value,
        "rules_description": bet.rules_description,
        "status": bet.status.value if hasattr(bet.status, 'value') else bet.status,
        "challenger_points": bet.challenger_points,
        "challenged_points": bet.challenged_points,
        "winner_id": bet.winner_id,
        "winner_name": winner.full_name if winner else None,
        "expires_at": bet.expires_at,
        "accepted_at": bet.accepted_at,
        "completed_at": bet.completed_at,
        "created_at": bet.created_at,
        "match": match
    }


@router.post("/challenge", response_model=PVPBetResponse)
def create_challenge(
    data: PVPBetCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new PVP challenge"""

    # Validate challenged user exists and is active
    challenged = db.query(User).filter(
        User.id == data.challenged_id,
        User.status == "active"
    ).first()

    if not challenged:
        raise HTTPException(status_code=404, detail="Usuário desafiado não encontrado ou inativo")

    # Cannot challenge yourself
    if data.challenged_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desafiar a si mesmo")

    # Validate bet type specific fields
    if data.bet_type == PVPBetType.MATCH and not data.match_id:
        raise HTTPException(status_code=400, detail="ID da partida é obrigatório para apostas em partida")

    if data.bet_type == PVPBetType.ROUND and not data.round_number:
        raise HTTPException(status_code=400, detail="Número da rodada é obrigatório para apostas em rodada")

    # Validate match exists if provided
    if data.match_id:
        match = db.query(Match).filter(Match.id == data.match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        if match.status == "finished":
            raise HTTPException(status_code=400, detail="Não pode apostar em partida já finalizada")

    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(hours=data.expires_hours)

    # Create the bet
    bet = PVPBet(
        challenger_id=current_user.id,
        challenged_id=data.challenged_id,
        bet_type=data.bet_type,
        match_id=data.match_id,
        round_number=data.round_number,
        prize_description=data.prize_description,
        prize_value=data.prize_value,
        rules_description=data.rules_description,
        status=PVPBetStatus.PENDING,
        expires_at=expires_at
    )

    db.add(bet)
    db.commit()
    db.refresh(bet)

    # Send WhatsApp notification to challenged user
    try:
        match_details = None
        if bet.match_id:
            match = db.query(Match).filter(Match.id == bet.match_id).first()
            if match:
                match_details = f"{match.team_a} x {match.team_b}"

        whatsapp_service.send_pvp_challenge(
            phone=challenged.phone,
            challenged_name=challenged.full_name,
            challenger_name=current_user.full_name,
            prize_description=bet.prize_description,
            bet_type=bet.bet_type.value if hasattr(bet.bet_type, 'value') else str(bet.bet_type),
            match_details=match_details,
            round_number=bet.round_number,
            bet_id=bet.id
        )
    except Exception as e:
        print(f"[PVP] Error sending WhatsApp notification: {e}")

    return _format_bet_response(bet, db)


@router.get("/received", response_model=List[PVPBetResponse])
def get_received_challenges(
    status: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get challenges received by current user"""
    query = db.query(PVPBet).filter(PVPBet.challenged_id == current_user.id)

    if status:
        query = query.filter(PVPBet.status == status)

    bets = query.order_by(desc(PVPBet.created_at)).all()
    return [_format_bet_response(bet, db) for bet in bets]


@router.get("/sent", response_model=List[PVPBetResponse])
def get_sent_challenges(
    status: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get challenges sent by current user"""
    query = db.query(PVPBet).filter(PVPBet.challenger_id == current_user.id)

    if status:
        query = query.filter(PVPBet.status == status)

    bets = query.order_by(desc(PVPBet.created_at)).all()
    return [_format_bet_response(bet, db) for bet in bets]


@router.get("/history", response_model=List[PVPBetResponse])
def get_bet_history(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all PVP bets involving current user (completed, accepted, etc.)"""
    bets = db.query(PVPBet).filter(
        or_(
            PVPBet.challenger_id == current_user.id,
            PVPBet.challenged_id == current_user.id
        )
    ).filter(
        PVPBet.status.in_(["accepted", "completed", "rejected", "cancelled"])
    ).order_by(desc(PVPBet.created_at)).all()

    return [_format_bet_response(bet, db) for bet in bets]


@router.get("/active", response_model=List[PVPBetResponse])
def get_active_bets(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active bets (accepted but not completed)"""
    bets = db.query(PVPBet).filter(
        or_(
            PVPBet.challenger_id == current_user.id,
            PVPBet.challenged_id == current_user.id
        )
    ).filter(PVPBet.status == "accepted").order_by(desc(PVPBet.accepted_at)).all()

    return [_format_bet_response(bet, db) for bet in bets]


@router.post("/{bet_id}/respond")
def respond_to_challenge(
    bet_id: int,
    data: PVPBetAction,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept or reject a challenge"""
    bet = db.query(PVPBet).filter(PVPBet.id == bet_id).first()

    if not bet:
        raise HTTPException(status_code=404, detail="Aposta não encontrada")

    if bet.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não foi desafiado nesta aposta")

    if bet.status != PVPBetStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Aposta já foi {bet.status}")

    # Check if expired
    if bet.expires_at and bet.expires_at < datetime.utcnow():
        bet.status = PVPBetStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Esta aposta expirou")

    if data.action == "accept":
        bet.status = PVPBetStatus.ACCEPTED
        bet.accepted_at = datetime.utcnow()

        # Notify challenger
        try:
            challenger = db.query(User).filter(User.id == bet.challenger_id).first()
            if challenger:
                whatsapp_service.send_pvp_accepted(
                    phone=challenger.phone,
                    challenger_name=challenger.full_name,
                    challenged_name=current_user.full_name,
                    prize_description=bet.prize_description
                )
        except Exception as e:
            print(f"[PVP] Error sending acceptance notification: {e}")

    elif data.action == "reject":
        bet.status = PVPBetStatus.REJECTED

        # Notify challenger
        try:
            challenger = db.query(User).filter(User.id == bet.challenger_id).first()
            if challenger:
                whatsapp_service.send_pvp_rejected(
                    phone=challenger.phone,
                    challenger_name=challenger.full_name,
                    challenged_name=current_user.full_name,
                    prize_description=bet.prize_description
                )
        except Exception as e:
            print(f"[PVP] Error sending rejection notification: {e}")

    else:
        raise HTTPException(status_code=400, detail="Ação inválida. Use 'accept' ou 'reject'")

    db.commit()
    db.refresh(bet)

    return {
        "message": f"Aposta {data.action == 'accept' and 'aceita' or 'recusada'} com sucesso",
        "bet": _format_bet_response(bet, db)
    }


@router.post("/{bet_id}/cancel")
def cancel_challenge(
    bet_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a challenge sent by current user"""
    bet = db.query(PVPBet).filter(PVPBet.id == bet_id).first()

    if not bet:
        raise HTTPException(status_code=404, detail="Aposta não encontrada")

    if bet.challenger_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode cancelar esta aposta")

    if bet.status != PVPBetStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Não pode cancelar aposta {bet.status}")

    bet.status = PVPBetStatus.CANCELLED
    db.commit()

    # Notify challenged user
    try:
        challenged = db.query(User).filter(User.id == bet.challenged_id).first()
        if challenged:
            whatsapp_service.send_pvp_cancelled(
                phone=challenged.phone,
                challenged_name=challenged.full_name,
                challenger_name=current_user.full_name,
                prize_description=bet.prize_description
            )
    except Exception as e:
        print(f"[PVP] Error sending cancellation notification: {e}")

    return {"message": "Desafio cancelado com sucesso"}


@router.get("/rankings/pvp", response_model=List[PVPRankingResponse])
def get_pvp_rankings(
    limit: int = 20,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get PVP rankings - top bettors"""

    # Query to calculate PVP stats per user
    results = db.query(
        User.id,
        User.full_name,
        func.count(PVPBet.id).label("total_bets"),
        func.sum(func.case([(PVPBet.winner_id == User.id, 1)], else_=0)).label("bets_won"),
        func.sum(func.case([(and_(PVPBet.winner_id != User.id, PVPBet.winner_id.isnot(None)), 1)], else_=0)).label("bets_lost")
    ).join(
        PVPBet,
        or_(
            User.id == PVPBet.challenger_id,
            User.id == PVPBet.challenged_id
        )
    ).filter(
        PVPBet.status == "completed"
    ).group_by(
        User.id,
        User.full_name
    ).order_by(
        desc("bets_won")
    ).limit(limit).all()

    rankings = []
    for row in results:
        total = row.total_bets or 0
        won = row.bets_won or 0
        lost = row.bets_lost or 0
        win_rate = (won / total * 100) if total > 0 else 0

        rankings.append({
            "user_id": row.id,
            "user_name": row.full_name,
            "total_bets": total,
            "bets_won": won,
            "bets_lost": lost,
            "win_rate": round(win_rate, 1),
            "total_prizes_won": "Consulte histórico"  # Could calculate actual prizes
        })

    return rankings


@router.get("/users/search")
def search_users_for_challenge(
    query: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users to challenge (exclude self and inactive users)"""
    users = db.query(User).filter(
        User.id != current_user.id,
        User.status == "active",
        or_(
            User.full_name.ilike(f"%{query}%"),
            User.email.ilike(f"%{query}%")
        )
    ).limit(10).all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone
        }
        for u in users
    ]


@router.get("/available-matches")
def get_available_matches(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get matches available for PVP betting (scheduled, not finished)"""
    matches = db.query(Match).filter(
        Match.status.in_(["scheduled", "live"])
    ).order_by(Match.match_date).all()

    return [
        {
            "id": m.id,
            "match_number": m.match_number,
            "team_a": m.team_a,
            "team_b": m.team_b,
            "team_a_code": m.team_a_code,
            "team_b_code": m.team_b_code,
            "match_date": m.match_date,
            "round_number": m.round_number,
            "group": m.group
        }
        for m in matches
    ]


@router.get("/available-rounds")
def get_available_rounds(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rounds available for PVP betting"""
    rounds = db.query(
        Match.round_number,
        func.count(Match.id).label("total_matches"),
        func.min(Match.match_date).label("start_date"),
        func.max(Match.match_date).label("end_date")
    ).filter(
        Match.round_number.isnot(None)
    ).group_by(
        Match.round_number
    ).order_by(
        Match.round_number
    ).all()

    return [
        {
            "round_number": r.round_number,
            "total_matches": r.total_matches,
            "start_date": r.start_date,
            "end_date": r.end_date
        }
        for r in rounds
    ]


@router.get("/{bet_id}", response_model=PVPBetResponse)
def get_bet_details(
    bet_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific bet"""
    bet = db.query(PVPBet).filter(PVPBet.id == bet_id).first()

    if not bet:
        raise HTTPException(status_code=404, detail="Aposta não encontrada")

    # Only involved users can see details
    if bet.challenger_id != current_user.id and bet.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta aposta")

    return _format_bet_response(bet, db)
