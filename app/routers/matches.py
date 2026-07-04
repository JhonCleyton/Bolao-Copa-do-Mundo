from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models import Match, MatchStatus, GroupStanding
from app.schemas import MatchResponse, MatchCreate, MatchUpdateScore
from app.auth import get_current_user, get_current_admin
from app.utils.timezone import get_brasilia_now

router = APIRouter()


@router.get("/", response_model=List[MatchResponse])
def list_matches(
    status: Optional[MatchStatus] = None,
    round_number: Optional[int] = None,
    group: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Match)
    
    if status:
        query = query.filter(Match.status == status)
    if round_number:
        query = query.filter(Match.round_number == round_number)
    if group:
        query = query.filter(Match.group == group)
    
    matches = query.order_by(Match.match_date).all()
    return matches


@router.get("/live", response_model=List[MatchResponse])
def get_live_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).filter(Match.status == MatchStatus.LIVE).all()
    return matches


@router.get("/today", response_model=List[MatchResponse])
def get_todays_matches(db: Session = Depends(get_db)):
    now = get_brasilia_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    matches = db.query(Match).filter(
        Match.match_date.between(today_start, today_end)
    ).order_by(Match.match_date).all()
    
    return matches


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.post("/", response_model=MatchResponse)
def create_match(
    match_data: MatchCreate,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    match = Match(**match_data.dict())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.put("/{match_id}/score", response_model=MatchResponse)
def update_score(
    match_id: int,
    score_data: MatchUpdateScore,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Detectar se o jogo está sendo "reaberto" (de finished para outro status)
    was_finished = match.status == MatchStatus.FINISHED
    is_reopening = was_finished and score_data.status != MatchStatus.FINISHED
    
    if is_reopening:
        print(f"[REOPEN] Match {match_id} being reopened from finished to {score_data.status}")
        print(f"[REOPEN] Resetting prediction points and recalculating rankings...")
        
        from app.routers.rankings import calculate_round_ranking_internal, calculate_general_ranking_internal
        from app.models import Prediction
        
        # Zerar pontos de todas as previsões deste jogo
        predictions = db.query(Prediction).filter(Prediction.match_id == match_id).all()
        total_points_removed = 0
        for pred in predictions:
            total_points_removed += pred.points_earned
            pred.points_earned = 0
            pred.points_winner = 0
            pred.points_score_a = 0
            pred.points_score_b = 0
            pred.points_exact = 0
        
        # Flush para garantir que as mudanças vão para o banco
        db.flush()
        print(f"[REOPEN] Reset {len(predictions)} predictions, removed {total_points_removed} total points")
        
        # Expirar todos os objetos para forçar re-leitura do banco
        db.expire_all()
        
        # Verificar se os pontos foram realmente zerados
        verify = db.query(Prediction).filter(Prediction.match_id == match_id).first()
        if verify:
            print(f"[REOPEN] Verify: prediction {verify.id} now has {verify.points_earned} points")
        
        # Recalcular rankings
        if match.round_number:
            round_count = calculate_round_ranking_internal(match.round_number, db)
            print(f"[REOPEN] Round {match.round_number} ranking recalculated ({round_count} users)")
        
        general_count = calculate_general_ranking_internal(db)
        print(f"[REOPEN] General ranking recalculated ({general_count} users)")
        
        # Commit final (os recálculos já fazem commit interno, mas garantimos aqui)
        db.commit()
    
    # Atualizar dados do jogo
    match.score_a = score_data.score_a
    match.score_b = score_data.score_b
    match.status = score_data.status
    match.penalty_winner = score_data.penalty_winner
    
    db.commit()
    db.refresh(match)
    
    # Se o jogo foi finalizado, calcular pontos e atualizar standings
    print(f"[DEBUG] Match {match_id} status update: {score_data.status}")
    
    if score_data.status == MatchStatus.FINISHED:
        print(f"[DEBUG] Match {match_id} finished - calculating points and rankings")
        from app.services.points_calculator import calculate_points
        from app.services.standings_service import auto_update_standings_on_match_finish
        from app.routers.rankings import calculate_round_ranking_internal, calculate_general_ranking_internal
        from app.models import Prediction
        
        predictions = db.query(Prediction).filter(Prediction.match_id == match_id).all()
        print(f"[DEBUG] Found {len(predictions)} predictions for match {match_id}")
        
        for pred in predictions:
            total, winner, score_a, score_b, exact = calculate_points(match, pred)
            print(f"[DEBUG] Prediction {pred.id}: user={pred.user_id}, points={total}")
            pred.points_earned = total
            pred.points_winner = winner
            pred.points_score_a = score_a
            pred.points_score_b = score_b
            pred.points_exact = exact
        
        db.commit()
        
        # Auto-update group standings and knockout matches
        auto_update_standings_on_match_finish(db, match)
        
        # Auto-update rankings for the round and general
        if match.round_number:
            print(f"[DEBUG] Calculating round ranking for round {match.round_number}")
            round_count = calculate_round_ranking_internal(match.round_number, db)
            print(f"[DEBUG] Round ranking calculated: {round_count} users")
        
        print(f"[DEBUG] Calculating general ranking")
        general_count = calculate_general_ranking_internal(db)
        print(f"[DEBUG] General ranking calculated: {general_count} users")
    
    return match


class LiveScoreUpdate(BaseModel):
    score_a: int
    score_b: int

@router.post("/{match_id}/live-update")
def update_live_score(
    match_id: int,
    data: LiveScoreUpdate,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update live match score"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.status != MatchStatus.LIVE:
        match.status = MatchStatus.LIVE
    
    match.score_a = data.score_a
    match.score_b = data.score_b
    db.commit()
    db.refresh(match)
    
    return {
        "message": "Placar atualizado ao vivo!",
        "match_id": match_id,
        "score_a": data.score_a,
        "score_b": data.score_b,
        "status": match.status.value
    }


@router.get("/standings/{group}")
def get_group_standings(group: str, db: Session = Depends(get_db)):
    """Get standings for a specific group"""
    standings = db.query(GroupStanding).filter(
        GroupStanding.group == group.upper()
    ).order_by(GroupStanding.position).all()
    
    return {
        "group": group.upper(),
        "standings": standings
    }


@router.get("/standings/")
def get_all_standings(db: Session = Depends(get_db)):
    """Get all group standings"""
    from sqlalchemy import func
    
    standings = db.query(
        GroupStanding.group,
        func.count(GroupStanding.id).label('teams')
    ).group_by(GroupStanding.group).all()
    
    result = {}
    for group, count in standings:
        if count > 0:
            result[group] = db.query(GroupStanding).filter(
                GroupStanding.group == group
            ).order_by(GroupStanding.position).all()
    
    return result


@router.post("/admin/refresh-standings")
def refresh_standings(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Manually refresh all group standings and knockout matches (admin)"""
    from app.services.standings_service import (
        update_all_group_standings,
        check_and_update_knockout_matches
    )
    
    update_all_group_standings(db)
    check_and_update_knockout_matches(db)
    
    return {"message": "Standings and knockout matches updated successfully"}
