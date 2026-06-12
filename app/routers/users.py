from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime

from app.database import get_db
from app.models import User, Payment
from app.schemas import UserResponse, PaymentCreate, PaymentResponse
from app.auth import get_current_user, get_password_hash, verify_password

router = APIRouter()


@router.get("/payments", response_model=List[PaymentResponse])
def get_my_payments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payments = db.query(Payment).filter(Payment.user_id == current_user.id).all()
    return payments


@router.get("/dashboard")
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Match, Prediction, MatchStatus, RoundRanking, GeneralRanking
    from datetime import datetime
    
    # Get predictions stats
    predictions = db.query(Prediction).filter(Prediction.user_id == current_user.id).all()
    total_predictions = len(predictions)
    correct_predictions = sum(1 for p in predictions if p.points_earned >= 2)
    exact_scores = sum(1 for p in predictions if p.points_exact > 0)
    total_points = sum(p.points_earned for p in predictions)
    
    # Get general ranking
    general_rank = db.query(GeneralRanking).filter(GeneralRanking.user_id == current_user.id).first()
    general_position = general_rank.position if general_rank else None
    
    # Get pending payments
    pending_payments = db.query(Payment).filter(
        Payment.user_id == current_user.id,
        Payment.paid == False
    ).all()
    
    # Get next matches (not started yet)
    now = datetime.utcnow()
    next_matches = db.query(Match).filter(
        Match.match_date > now,
        Match.status == MatchStatus.SCHEDULED
    ).order_by(Match.match_date).limit(5).all()
    
    # Get last predictions
    last_predictions = db.query(Prediction).filter(
        Prediction.user_id == current_user.id
    ).order_by(Prediction.created_at.desc()).limit(5).all()
    
    return {
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "registration_paid": current_user.registration_paid
        },
        "total_points": total_points,
        "general_position": general_position,
        "predictions_made": total_predictions,
        "predictions_correct": correct_predictions,
        "exact_scores": exact_scores,
        "pending_payments": [
            {
                "id": p.id,
                "type": p.type,
                "round_number": p.round_number,
                "amount": p.amount,
                "paid": p.paid
            }
            for p in pending_payments
        ],
        "next_matches": [
            {
                "id": m.id,
                "team_a": m.team_a,
                "team_b": m.team_b,
                "match_date": m.match_date.isoformat() if m.match_date else None,
                "city": m.city,
                "round_number": m.round_number
            }
            for m in next_matches
        ],
        "last_predictions": [
            {
                "id": p.id,
                "predicted_score_a": p.predicted_score_a,
                "predicted_score_b": p.predicted_score_b,
                "points_earned": p.points_earned,
                "match": {
                    "team_a": p.match.team_a,
                    "team_b": p.match.team_b
                }
            }
            for p in last_predictions
        ]
    }


@router.put("/profile")
def update_profile(
    full_name: str = None,
    phone: str = None,
    bio: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    if full_name:
        current_user.full_name = full_name
    if phone:
        current_user.phone = phone
    if bio is not None:
        current_user.bio = bio
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Profile updated successfully", "user": current_user}


@router.post("/change-password")
def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload profile avatar"""
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if avatar.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, GIF and WebP allowed."
        )
    
    # Create avatars directory if not exists
    avatars_dir = "static/avatars"
    os.makedirs(avatars_dir, exist_ok=True)
    
    # Generate unique filename
    ext = avatar.filename.split('.')[-1]
    filename = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}.{ext}"
    file_path = os.path.join(avatars_dir, filename)
    
    # Delete old avatar if exists
    if current_user.avatar:
        old_path = current_user.avatar.replace('/static/', 'static/')
        if os.path.exists(old_path):
            os.remove(old_path)
    
    # Save new avatar
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(avatar.file, buffer)
    
    # Update user avatar path
    current_user.avatar = f"/static/avatars/{filename}"
    db.commit()
    
    return {"message": "Avatar uploaded successfully", "avatar_url": current_user.avatar}
