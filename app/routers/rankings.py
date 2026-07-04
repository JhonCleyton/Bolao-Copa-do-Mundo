from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import func, case

from app.database import get_db
from app.models import RoundRanking, GeneralRanking, User, Prediction, Match
from app.auth import get_current_user
from app.services.email_service import email_service
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()


def get_first_two_names(full_name: str) -> str:
    """Return only first and second name, or just first if only one exists"""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return parts[0] if parts else ""


@router.get("/rounds")
def get_available_rounds(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get all rounds that have matches, with proper stage labels"""
    STAGE_LABELS = {
        'group_stage': '{n}ª Rodada',
        'round_of_32': 'Fase de 32',
        'round_of_16': 'Oitavas de Final',
        'quarter_final': 'Quartas de Final',
        'semi_final': 'Semifinais',
        'third_place': '3º Lugar / Final',
        'final': '3º Lugar / Final',
    }

    all_rounds = db.query(Match.round_number, Match.stage)\
        .distinct()\
        .order_by(Match.round_number)\
        .all()

    seen = set()
    result = []
    for round_number, stage in all_rounds:
        if round_number in seen:
            continue
        seen.add(round_number)
        stage_val = stage.value if stage and hasattr(stage, 'value') else (stage or '')
        template = STAGE_LABELS.get(stage_val, 'Rodada {n}')
        result.append({
            'round_number': round_number,
            'stage': stage_val,
            'label': template.replace('{n}', str(round_number)),
        })

    return result


@router.get("/round/{round_number}")
def get_round_ranking(
    round_number: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get ranking for a specific round"""
    from app.models import Match
    
    # Count finished matches in this round for max points calculation
    finished_matches = db.query(Match).filter(
        Match.round_number == round_number,
        Match.status == 'finished'
    ).count()
    max_possible_points = finished_matches * 8  # 8 points max per match
    
    rankings = db.query(RoundRanking, User).join(
        User, RoundRanking.user_id == User.id
    ).filter(
        RoundRanking.round_number == round_number
    ).order_by(RoundRanking.position).all()
    
    result = []
    for ranking, user in rankings:
        # Calculate aproveitamento (performance percentage)
        aproveitamento = 0
        if max_possible_points > 0 and ranking.total_points > 0:
            aproveitamento = round((ranking.total_points / max_possible_points) * 100, 1)
        
        result.append({
            "id": ranking.id,
            "user_id": ranking.user_id,
            "user_name": get_first_two_names(user.full_name),
            "round_number": ranking.round_number,
            "total_points": ranking.total_points,
            "correct_predictions": ranking.correct_predictions,
            "exact_scores": ranking.exact_scores,
            "position": ranking.position,
            "prize_won": ranking.prize_won,
            "aproveitamento": aproveitamento,
            "matches_finished": finished_matches
        })
    
    return {
        "round": round_number,
        "max_possible_points": max_possible_points,
        "matches_finished": finished_matches,
        "rankings": result
    }


@router.get("/general")
def get_general_ranking(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get general ranking with user names"""
    from app.models import Match
    
    # Count all finished matches for max points calculation
    finished_matches = db.query(Match).filter(
        Match.status == 'finished'
    ).count()
    max_possible_points = finished_matches * 8  # 8 points max per match
    
    rankings = db.query(GeneralRanking, User).join(
        User, GeneralRanking.user_id == User.id
    ).order_by(GeneralRanking.position).all()
    
    result = []
    for ranking, user in rankings:
        # Calculate aproveitamento (performance percentage)
        aproveitamento = 0
        if max_possible_points > 0 and ranking.total_points > 0:
            aproveitamento = round((ranking.total_points / max_possible_points) * 100, 1)
        
        result.append({
            "id": ranking.id,
            "user_id": ranking.user_id,
            "user_name": get_first_two_names(user.full_name),
            "total_points": ranking.total_points,
            "correct_predictions": ranking.correct_predictions,
            "exact_scores": ranking.exact_scores,
            "position": ranking.position,
            "updated_at": ranking.updated_at,
            "aproveitamento": aproveitamento,
            "matches_finished": finished_matches
        })
    
    return {
        "max_possible_points": max_possible_points,
        "matches_finished": finished_matches,
        "rankings": result
    }


@router.get("/me/round/{round_number}")
def get_my_round_ranking(
    round_number: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current user's ranking for a specific round"""
    from app.models import Match
    
    # Count finished matches in this round
    finished_matches = db.query(Match).filter(
        Match.round_number == round_number,
        Match.status == 'finished'
    ).count()
    max_possible_points = finished_matches * 8
    
    ranking = db.query(RoundRanking).filter(
        RoundRanking.user_id == current_user.id,
        RoundRanking.round_number == round_number
    ).first()
    
    if not ranking:
        return {
            "round": round_number,
            "total_points": 0,
            "position": None,
            "aproveitamento": 0,
            "matches_finished": finished_matches,
            "message": "No ranking available for this round yet"
        }
    
    # Calculate aproveitamento
    aproveitamento = 0
    if max_possible_points > 0 and ranking.total_points > 0:
        aproveitamento = round((ranking.total_points / max_possible_points) * 100, 1)
    
    return {
        "id": ranking.id,
        "user_id": ranking.user_id,
        "round_number": ranking.round_number,
        "total_points": ranking.total_points,
        "correct_predictions": ranking.correct_predictions,
        "exact_scores": ranking.exact_scores,
        "position": ranking.position,
        "prize_won": ranking.prize_won,
        "aproveitamento": aproveitamento,
        "matches_finished": finished_matches
    }


@router.get("/me/general")
def get_my_general_ranking(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current user's general ranking"""
    from app.models import Match
    
    # Count all finished matches
    finished_matches = db.query(Match).filter(
        Match.status == 'finished'
    ).count()
    max_possible_points = finished_matches * 8
    
    ranking = db.query(GeneralRanking).filter(
        GeneralRanking.user_id == current_user.id
    ).first()
    
    if not ranking:
        # Calculate on the fly
        predictions = db.query(Prediction).filter(
            Prediction.user_id == current_user.id
        ).all()
        
        total_points = sum(p.points_earned for p in predictions)
        correct = sum(1 for p in predictions if p.points_earned >= 2)
        exact = sum(1 for p in predictions if p.points_exact > 0)
        
        # Calculate aproveitamento
        aproveitamento = 0
        if max_possible_points > 0 and total_points > 0:
            aproveitamento = round((total_points / max_possible_points) * 100, 1)
        
        return {
            "user_id": current_user.id,
            "total_points": total_points,
            "correct_predictions": correct,
            "exact_scores": exact,
            "position": None,
            "aproveitamento": aproveitamento,
            "matches_finished": finished_matches
        }
    
    # Calculate aproveitamento for existing ranking
    aproveitamento = 0
    if max_possible_points > 0 and ranking.total_points > 0:
        aproveitamento = round((ranking.total_points / max_possible_points) * 100, 1)
    
    return {
        "id": ranking.id,
        "user_id": ranking.user_id,
        "total_points": ranking.total_points,
        "correct_predictions": ranking.correct_predictions,
        "exact_scores": ranking.exact_scores,
        "position": ranking.position,
        "updated_at": ranking.updated_at,
        "aproveitamento": aproveitamento,
        "matches_finished": finished_matches
    }


# Admin endpoints for calculating rankings
from app.auth import get_current_admin


def calculate_round_ranking_internal(round_number: int, db: Session):
    """Internal function to calculate round rankings (used by scheduler)"""
    from app.models import Match
    
    # Get all active users
    all_users = db.query(User).filter(User.status == 'active').all()
    
    # Get matches in this round
    matches_in_round = db.query(Match).filter(
        Match.round_number == round_number
    ).all()
    
    match_ids = [m.id for m in matches_in_round]
    print(f"[RANK-CALC] Round {round_number}: {len(match_ids)} matches, {len(all_users)} users")
    
    # Calculate points per user (only for users with predictions)
    user_stats = db.query(
        Prediction.user_id,
        func.sum(Prediction.points_earned).label('total_points'),
        func.count(Prediction.id).label('total_predictions'),
        func.sum(case((Prediction.points_exact > 0, 1), else_=0)).label('exact_scores')
    ).filter(
        Prediction.match_id.in_(match_ids)
    ).group_by(Prediction.user_id).all()
    
    # Log top 3 users for debugging
    sorted_stats = sorted(user_stats, key=lambda x: x.total_points or 0, reverse=True)[:3]
    for stat in sorted_stats:
        print(f"[RANK-CALC] User {stat.user_id}: {stat.total_points} points")
    
    # Create dict for quick lookup
    stats_by_user = {stat.user_id: stat for stat in user_stats}
    
    # Clear old rankings for this round
    db.query(RoundRanking).filter(RoundRanking.round_number == round_number).delete()
    
    # Create rankings for ALL users
    rankings = []
    for user in all_users:
        stat = stats_by_user.get(user.id)
        
        if stat:
            # User has predictions in this round
            correct_preds = db.query(Prediction).filter(
                Prediction.user_id == user.id,
                Prediction.match_id.in_(match_ids),
                Prediction.points_earned >= 2
            ).count()
            
            ranking = RoundRanking(
                user_id=user.id,
                round_number=round_number,
                total_points=stat.total_points or 0,
                correct_predictions=correct_preds,
                exact_scores=stat.exact_scores or 0
            )
        else:
            # User has no predictions - all zeros
            ranking = RoundRanking(
                user_id=user.id,
                round_number=round_number,
                total_points=0,
                correct_predictions=0,
                exact_scores=0
            )
        
        rankings.append((ranking.total_points, ranking))
    
    # Sort and assign positions
    rankings.sort(key=lambda x: x[0], reverse=True)
    
    prize_pool = 100.0  # R$ 100 por rodada
    
    for i, (_, ranking) in enumerate(rankings):
        ranking.position = i + 1
        
        # Prize logic: 50% 1st, 30% 2nd, 20% 3rd
        if i == 0:
            ranking.prize_won = prize_pool * 0.5
        elif i == 1:
            ranking.prize_won = prize_pool * 0.3
        elif i == 2:
            ranking.prize_won = prize_pool * 0.2
        else:
            ranking.prize_won = 0
        
        db.add(ranking)
    
    db.commit()
    
    return len(rankings)


def calculate_general_ranking_internal(db: Session):
    """Internal function to calculate general ranking (used by match finish)"""
    # Get all active users
    all_users = db.query(User).filter(User.status == 'active').all()
    
    # Calculate points per user from predictions
    user_stats = db.query(
        Prediction.user_id,
        func.sum(Prediction.points_earned).label('total_points'),
        func.count(Prediction.id).label('total_predictions'),
        func.sum(case((Prediction.points_exact > 0, 1), else_=0)).label('exact_scores')
    ).group_by(Prediction.user_id).all()
    
    # Create dict for quick lookup
    stats_by_user = {stat.user_id: stat for stat in user_stats}
    
    # Clear old rankings
    db.query(GeneralRanking).delete()
    
    # Create rankings for ALL users (even without predictions)
    rankings = []
    for user in all_users:
        stat = stats_by_user.get(user.id)
        
        if stat:
            # User has predictions
            correct_preds = db.query(Prediction).filter(
                Prediction.user_id == user.id,
                Prediction.points_earned >= 2
            ).count()
            
            ranking = GeneralRanking(
                user_id=user.id,
                total_points=stat.total_points or 0,
                correct_predictions=correct_preds,
                exact_scores=stat.exact_scores or 0
            )
        else:
            # User has no predictions - all zeros
            ranking = GeneralRanking(
                user_id=user.id,
                total_points=0,
                correct_predictions=0,
                exact_scores=0
            )
        
        rankings.append((ranking.total_points, ranking))
    
    # Sort and assign positions
    rankings.sort(key=lambda x: x[0], reverse=True)
    
    for i, (_, ranking) in enumerate(rankings):
        ranking.position = i + 1
        db.add(ranking)
    
    db.commit()
    
    return len(rankings)


@router.post("/admin/calculate-round/{round_number}")
def calculate_round_ranking(
    round_number: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Calculate rankings for a round (admin only)"""
    
    count = calculate_round_ranking_internal(round_number, db)
    
    # Send notifications (only when triggered manually by admin)
    rankings = db.query(RoundRanking).filter(
        RoundRanking.round_number == round_number
    ).order_by(RoundRanking.position).all()
    
    for ranking in rankings:
        user = db.query(User).filter(User.id == ranking.user_id).first()
        if user:
            # Email notification
            email_service.send_round_notification(
                user.email,
                user.full_name,
                round_number,
                ranking.position,
                ranking.total_points,
                ranking.prize_won
            )
            
            # WhatsApp notification
            whatsapp_service.send_round_notification(
                user.phone,
                user.full_name,
                round_number,
                ranking.position,
                ranking.total_points,
                ranking.prize_won
            )
            
            # Winner notification for top 3
            if ranking.position <= 3 and ranking.prize_won > 0:
                email_service.send_winner_notification(
                    user.email,
                    user.full_name,
                    round_number,
                    ranking.position,
                    ranking.prize_won
                )
                
                whatsapp_service.send_winner_notification(
                    user.phone,
                    user.full_name,
                    round_number,
                    ranking.position,
                    ranking.prize_won
                )
    
    return {
        "message": f"Round {round_number} rankings calculated",
        "total_users": count
    }


@router.post("/admin/calculate-general")
def calculate_general_ranking(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Calculate general ranking (admin only)"""
    count = calculate_general_ranking_internal(db)
    
    return {
        "message": "General ranking calculated",
        "total_users": count
    }
