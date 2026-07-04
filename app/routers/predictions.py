from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Prediction, Match, MatchStatus, Payment, User
from app.schemas import PredictionCreate, PredictionResponse
from app.auth import get_current_user
from app.services.points_calculator import get_points_breakdown
from app.utils.timezone import get_brasilia_now

router = APIRouter()


PREDICTION_DEADLINE_MINUTES = 10  # Minutes before match when predictions are locked

def check_can_predict(db: Session, user_id: int, match: Match):
    """Check if user can make prediction (paid and before match with deadline)"""
    now = get_brasilia_now()
    
    # Admin pode sobrescrever o prazo via match.prediction_deadline
    # Se houver prazo customizado, ele tem prioridade absoluta
    if match.prediction_deadline is not None:
        if now >= match.prediction_deadline:
            return False, "Palpites encerrados: prazo definido pelo administrador expirou"
        # Se ainda está dentro do prazo extendido, permite palpitar
        # (mesmo que o jogo já tenha começado ou esteja ao vivo)
        pass  # Continua para verificar pagamento
    else:
        # Sem prazo customizado - usar regras normais
        # Check if match finished
        if match.status == MatchStatus.FINISHED:
            return False, "Este jogo já foi finalizado"
        
        # Check default deadline (10 min before match)
        deadline = match.match_date - timedelta(minutes=PREDICTION_DEADLINE_MINUTES)
        if now >= deadline:
            return False, "Palpites encerrados: faltam menos de 10 minutos para o jogo"
        
        # Check if match already started (ao vivo)
        if now >= match.match_date:
            return False, "Palpites encerrados: o jogo já começou"
    
    # Check if user paid for registration
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.registration_paid:
        return False, "Pagamento da inscrição pendente"
    
    # Check if user paid for this round
    payment = db.query(Payment).filter(
        Payment.user_id == user_id,
        Payment.type == "round",
        Payment.round_number == match.round_number,
        Payment.paid == True
    ).first()
    
    if not payment:
        return False, f"Pagamento da rodada {match.round_number} pendente"
    
    return True, None


def get_prediction_deadline(match: Match) -> datetime:
    """Get the prediction deadline (override or 10 minutes before match)"""
    if match.prediction_deadline is not None:
        return match.prediction_deadline
    return match.match_date - timedelta(minutes=PREDICTION_DEADLINE_MINUTES)


@router.get("/", response_model=List[PredictionResponse])
def get_my_predictions(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = db.query(Prediction).filter(
        Prediction.user_id == current_user.id
    ).order_by(Prediction.created_at.desc()).all()
    return predictions


@router.get("/match/{match_id}", response_model=Optional[PredictionResponse])
def get_prediction_for_match(
    match_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prediction = db.query(Prediction).filter(
        Prediction.user_id == current_user.id,
        Prediction.match_id == match_id
    ).first()
    
    return prediction


@router.post("/", response_model=PredictionResponse)
def create_prediction(
    prediction_data: PredictionCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if match exists
    match = db.query(Match).filter(Match.id == prediction_data.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Check if user can predict
    can_predict, reason = check_can_predict(db, current_user.id, match)
    if not can_predict:
        raise HTTPException(
            status_code=403,
            detail=reason
        )
    
    # Check if prediction already exists
    existing = db.query(Prediction).filter(
        Prediction.user_id == current_user.id,
        Prediction.match_id == prediction_data.match_id
    ).first()
    
    if existing:
        # Update existing
        existing.predicted_score_a = prediction_data.predicted_score_a
        existing.predicted_score_b = prediction_data.predicted_score_b
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new
    prediction = Prediction(
        user_id=current_user.id,
        match_id=prediction_data.match_id,
        predicted_score_a=prediction_data.predicted_score_a,
        predicted_score_b=prediction_data.predicted_score_b
    )
    
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


@router.put("/{prediction_id}", response_model=PredictionResponse)
def update_prediction(
    prediction_id: int,
    prediction_data: PredictionCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.user_id == current_user.id
    ).first()
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    # Check if match already started
    match = db.query(Match).filter(Match.id == prediction.match_id).first()
    can_predict, reason = check_can_predict(db, current_user.id, match)
    if not can_predict:
        raise HTTPException(
            status_code=403,
            detail=reason
        )
    
    prediction.predicted_score_a = prediction_data.predicted_score_a
    prediction.predicted_score_b = prediction_data.predicted_score_b
    
    db.commit()
    db.refresh(prediction)
    return prediction


@router.get("/{prediction_id}/points")
def get_prediction_points(
    prediction_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.user_id == current_user.id
    ).first()
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    match = db.query(Match).filter(Match.id == prediction.match_id).first()
    
    if match.status != MatchStatus.FINISHED:
        return {"message": "Match not finished yet", "points": 0}
    
    breakdown = get_points_breakdown(match, prediction)
    
    return {
        "prediction": prediction,
        "match_result": f"{match.team_a} {match.score_a} x {match.score_b} {match.team_b}",
        "points_breakdown": breakdown
    }


@router.get("/transparency/match/{match_id}")
def get_match_predictions_transparency(
    match_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all predictions for a match (transparency - public endpoint)
    Shows user names and their predictions for transparency and anti-fraud
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get all predictions for this match with user info
    predictions = db.query(Prediction, User).join(
        User, Prediction.user_id == User.id
    ).filter(
        Prediction.match_id == match_id
    ).all()
    
    # If match is finished, show points too
    show_points = match.status == MatchStatus.FINISHED
    
    result = []
    for pred, user in predictions:
        data = {
            "user_name": user.full_name,
            "user_id": user.id,
            "predicted_score_a": pred.predicted_score_a,
            "predicted_score_b": pred.predicted_score_b,
            "prediction_time": pred.created_at
        }
        if show_points:
            data["points_earned"] = pred.points_earned
        result.append(data)
    
    return {
        "match": {
            "id": match.id,
            "team_a": match.team_a,
            "team_b": match.team_b,
            "score_a": match.score_a,
            "score_b": match.score_b,
            "status": match.status.value,
            "match_date": match.match_date
        },
        "predictions": result,
        "total_predictions": len(result)
    }


@router.get("/transparency/round/{round_number}")
def get_round_predictions_transparency(
    round_number: int,
    db: Session = Depends(get_db)
):
    """
    Get all predictions for all matches in a round (transparency)
    """
    from app.models import Match
    
    matches = db.query(Match).filter(
        Match.round_number == round_number
    ).all()
    
    result = {}
    for match in matches:
        predictions = db.query(Prediction, User).join(
            User, Prediction.user_id == User.id
        ).filter(Prediction.match_id == match.id).all()
        
        show_points = match.status == MatchStatus.FINISHED
        
        result[match.id] = {
            "match": f"{match.team_a} x {match.team_b}",
            "predictions": [
                {
                    "user_name": user.full_name,
                    "predicted_score_a": pred.predicted_score_a,
                    "predicted_score_b": pred.predicted_score_b,
                    **({"points": pred.points_earned} if show_points else {})
                }
                for pred, user in predictions
            ]
        }
    
    return {
        "round": round_number,
        "matches": result
    }
