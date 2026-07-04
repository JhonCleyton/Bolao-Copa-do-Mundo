from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import User, Match, Prediction, Payment, MatchStatus, CarouselImage, LandingPageConfig, UserStatus
from app.schemas import UserResponse, PaymentResponse, DashboardStats
from app.auth import get_current_admin
from app.utils.timezone import get_brasilia_now

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def get_admin_dashboard(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard stats"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "active").count()
    total_matches = db.query(Match).count()
    finished_matches = db.query(Match).filter(Match.status == MatchStatus.FINISHED).count()
    total_predictions = db.query(Prediction).count()
    total_prizes = db.query(Payment).filter(Payment.paid == True).with_entities(
        func.sum(Payment.amount)
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_matches": total_matches,
        "finished_matches": finished_matches,
        "total_predictions": total_predictions,
        "total_prizes": float(total_prizes)
    }


@router.get("/users", response_model=List[UserResponse])
def list_users(
    status: str = None,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all users"""
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    users = query.all()
    return users


@router.get("/users/{user_id}/payments")
def get_user_payments(
    user_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get payments for a specific user"""
    payments = db.query(Payment).filter(Payment.user_id == user_id).all()
    return payments


@router.get("/billing")
def get_billing_center(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get users with registration and round payment status for billing center"""
    users = db.query(User).order_by(User.full_name).all()
    rounds = [
        row[0] for row in db.query(Match.round_number)
        .filter(Match.round_number.isnot(None))
        .distinct()
        .order_by(Match.round_number)
        .all()
    ]
    payments = db.query(Payment).all()
    
    payments_by_user = {}
    for payment in payments:
        payments_by_user.setdefault(payment.user_id, []).append(payment)
    
    result_users = []
    for user in users:
        user_payments = payments_by_user.get(user.id, [])
        registration_payment = next((p for p in user_payments if p.type == "registration"), None)
        round_payments = {}
        
        for round_number in rounds:
            payment = next(
                (p for p in user_payments if p.type == "round" and p.round_number == round_number),
                None
            )
            round_payments[str(round_number)] = {
                "payment_id": payment.id if payment else None,
                "paid": bool(payment.paid) if payment else False,
                "amount": float(payment.amount) if payment and payment.amount is not None else 0,
                "payment_date": payment.payment_date if payment else None,
                "transaction_id": payment.transaction_id if payment else None
            }
        
        result_users.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status.value if hasattr(user.status, "value") else user.status,
            "registration_paid": bool(user.registration_paid),
            "registration_payment": {
                "payment_id": registration_payment.id if registration_payment else None,
                "paid": bool(registration_payment.paid) if registration_payment else bool(user.registration_paid),
                "amount": float(registration_payment.amount) if registration_payment and registration_payment.amount is not None else 0,
                "payment_date": registration_payment.payment_date if registration_payment else None,
                "transaction_id": registration_payment.transaction_id if registration_payment else None
            },
            "round_payments": round_payments
        })
    
    return {
        "rounds": rounds,
        "users": result_users
    }


@router.post("/billing/payment")
def save_billing_payment(
    user_id: int,
    payment_type: str,
    paid: bool,
    round_number: int = None,
    amount: float = 0,
    transaction_id: str = None,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create or update a registration/round payment and participation flags"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if payment_type not in ["registration", "round"]:
        raise HTTPException(status_code=400, detail="Invalid payment type")
    
    if payment_type == "round" and not round_number:
        raise HTTPException(status_code=400, detail="Round number required")
    
    query = db.query(Payment).filter(
        Payment.user_id == user_id,
        Payment.type == payment_type
    )
    
    if payment_type == "round":
        query = query.filter(Payment.round_number == round_number)
    
    payment = query.first()
    
    if not payment:
        payment = Payment(
            user_id=user_id,
            type=payment_type,
            round_number=round_number if payment_type == "round" else None
        )
        db.add(payment)
    
    payment.amount = amount
    payment.paid = paid
    payment.transaction_id = transaction_id
    payment.payment_date = datetime.utcnow() if paid else None
    
    if payment_type == "registration":
        user.registration_paid = paid
    
    db.commit()
    db.refresh(payment)
    
    return {
        "message": "Payment updated successfully",
        "payment": payment
    }


@router.post("/users/{user_id}/confirm-payment")
def confirm_payment(
    user_id: int,
    payment_type: str,  # registration or round
    round_number: int = None,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Confirm a payment for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if payment_type == "registration":
        user.registration_paid = True
        
        # Update or create registration payment record
        payment = db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.type == "registration"
        ).first()
        
        if not payment:
            payment = Payment(
                user_id=user_id,
                type="registration",
                amount=100.0,
                paid=True,
                payment_date=datetime.utcnow()
            )
            db.add(payment)
        else:
            payment.paid = True
            payment.payment_date = datetime.utcnow()
    
    elif payment_type == "round":
        if not round_number:
            raise HTTPException(status_code=400, detail="Round number required")
        
        # Update or create round payment
        payment = db.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.type == "round",
            Payment.round_number == round_number
        ).first()
        
        if not payment:
            payment = Payment(
                user_id=user_id,
                type="round",
                round_number=round_number,
                amount=10.0,
                paid=True,
                payment_date=datetime.utcnow()
            )
            db.add(payment)
        else:
            payment.paid = True
            payment.payment_date = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Payment confirmed successfully"}


from pydantic import BaseModel
from typing import Optional

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    is_admin: Optional[bool] = None
    email_verified: Optional[bool] = None
    phone_verified: Optional[bool] = None
    registration_paid: Optional[bool] = None


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update user details - admin can activate, verify, change status, etc."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-demotion
    if user.id == current_user.id and data.is_admin is False:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin status")
    
    updated = False
    
    if data.full_name is not None:
        user.full_name = data.full_name
        updated = True
    if data.email is not None:
        # Check if email is already used by another user
        existing = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = data.email
        updated = True
    if data.phone is not None:
        user.phone = data.phone
        updated = True
    if data.status is not None:
        try:
            user.status = UserStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")
        updated = True
    if data.is_admin is not None:
        user.is_admin = data.is_admin
        updated = True
    if data.email_verified is not None:
        user.email_verified = data.email_verified
        updated = True
    if data.phone_verified is not None:
        user.phone_verified = data.phone_verified
        updated = True
    if data.registration_paid is not None:
        user.registration_paid = data.registration_paid
        updated = True
    
    if updated:
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    
    return {
        "message": "User updated successfully",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status.value,
            "is_admin": user.is_admin,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
            "registration_paid": user.registration_paid
        }
    }


@router.get("/users/{user_id}/detail")
def get_user_detail(
    user_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get full user details for editing"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status.value,
        "is_admin": user.is_admin,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "registration_paid": user.registration_paid,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }


@router.get("/matches/pending")
def get_matches_without_predictions(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get matches and users who haven't made predictions"""
    from datetime import datetime, timedelta
    
    # Get upcoming matches
    now = get_brasilia_now()
    upcoming = db.query(Match).filter(
        Match.match_date > now,
        Match.status == MatchStatus.SCHEDULED
    ).all()
    
    result = []
    for match in upcoming:
        # Get users without predictions for this match
        users_with_predictions = db.query(Prediction.user_id).filter(
            Prediction.match_id == match.id
        ).subquery()
        
        users_without = db.query(User).filter(
            User.status == "active",
            User.registration_paid == True,
            ~User.id.in_(users_with_predictions)
        ).all()
        
        if users_without:
            result.append({
                "match": match,
                "users_without_prediction": users_without
            })
    
    return result


@router.post("/matches/seed")
def seed_matches(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Seed all World Cup 2026 matches"""
    from app.seed_data import matches_data
    
    # Check if matches already exist
    existing = db.query(Match).count()
    if existing > 0:
        return {"message": "Matches already seeded", "count": existing}
    
    for match_data in matches_data:
        match = Match(**match_data)
        db.add(match)
    
    db.commit()
    
    return {"message": "Matches seeded successfully", "count": len(matches_data)}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete admin user")
    
    # Delete related records
    db.query(Prediction).filter(Prediction.user_id == user_id).delete()
    db.query(Payment).filter(Payment.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    
    db.commit()
    return {"message": "User deleted successfully"}


# Prize Configuration Endpoints
from app.models import PrizeConfiguration
import json


@router.get("/prizes")
def get_prize_configurations(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all prize configurations"""
    prizes = db.query(PrizeConfiguration).all()
    return [
        {
            "id": p.id,
            "round_number": p.round_number,
            "total_prize": p.total_prize,
            "num_winners": p.num_winners,
            "distribution": json.loads(p.distribution),
            "is_active": p.is_active
        }
        for p in prizes
    ]


@router.post("/prizes")
def create_prize_configuration(
    round_number: int,
    total_prize: float = 100.0,
    num_winners: int = 1,
    distribution: str = '{"1": 100}',
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create or update prize configuration for a round"""
    # Validate distribution
    try:
        dist = json.loads(distribution)
        total = sum(dist.values())
        if total != 100:
            raise HTTPException(
                status_code=400,
                detail=f"Distribution must sum to 100%, got {total}%"
            )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid distribution JSON")
    
    # Check if exists
    existing = db.query(PrizeConfiguration).filter(
        PrizeConfiguration.round_number == round_number
    ).first()
    
    if existing:
        existing.total_prize = total_prize
        existing.num_winners = num_winners
        existing.distribution = distribution
        existing.is_active = True
    else:
        prize = PrizeConfiguration(
            round_number=round_number,
            total_prize=total_prize,
            num_winners=num_winners,
            distribution=distribution,
            is_active=True
        )
        db.add(prize)
    
    db.commit()
    return {"message": f"Prize configuration for round {round_number} saved"}


@router.put("/prizes/{prize_id}")
def update_prize_configuration(
    prize_id: int,
    total_prize: float = None,
    num_winners: int = None,
    distribution: str = None,
    is_active: bool = None,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update prize configuration"""
    prize = db.query(PrizeConfiguration).filter(PrizeConfiguration.id == prize_id).first()
    if not prize:
        raise HTTPException(status_code=404, detail="Prize configuration not found")
    
    if distribution:
        try:
            dist = json.loads(distribution)
            total = sum(dist.values())
            if total != 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"Distribution must sum to 100%, got {total}%"
                )
            prize.distribution = distribution
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid distribution JSON")
    
    if total_prize is not None:
        prize.total_prize = total_prize
    if num_winners is not None:
        prize.num_winners = num_winners
    if is_active is not None:
        prize.is_active = is_active
    
    db.commit()
    return {"message": "Prize configuration updated"}


@router.get("/stats")
def get_admin_stats(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive admin statistics"""
    from app.models import Prediction, Payment
    from sqlalchemy import func
    
    # User stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "active").count()
    paid_users = db.query(User).filter(User.registration_paid == True).count()
    
    # Financial stats
    total_revenue = db.query(Payment).filter(Payment.paid == True).with_entities(
        func.sum(Payment.amount)
    ).scalar() or 0
    
    pending_revenue = db.query(Payment).filter(Payment.paid == False).with_entities(
        func.sum(Payment.amount)
    ).scalar() or 0
    
    # Predictions stats
    total_predictions = db.query(Prediction).count()
    predictions_by_round = db.query(
        Match.round_number,
        func.count(Prediction.id).label('count')
    ).join(Prediction, Prediction.match_id == Match.id).group_by(Match.round_number).all()
    
    # Match stats
    total_matches = db.query(Match).count()
    finished_matches = db.query(Match).filter(Match.status == MatchStatus.FINISHED).count()
    live_matches = db.query(Match).filter(Match.status == MatchStatus.LIVE).count()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "paid": paid_users
        },
        "financial": {
            "total_revenue": float(total_revenue),
            "pending_revenue": float(pending_revenue),
            "prizes_paid": 0  # To be calculated
        },
        "predictions": {
            "total": total_predictions,
            "by_round": {f"round_{r}": c for r, c in predictions_by_round}
        },
        "matches": {
            "total": total_matches,
            "finished": finished_matches,
            "live": live_matches,
            "scheduled": total_matches - finished_matches - live_matches
        }
    }


# WhatsApp/Evolution API Management Endpoints
import os
from pydantic import BaseModel

# Load config from environment variables
EVOLUTION_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "bolao-copa-2026")
WHATSAPP_NUMBER = os.getenv("WHATSAPP_DIRETO", "")

class WhatsAppConfig(BaseModel):
    evolution_url: str
    instance_name: str
    api_key: str
    test_number: str = None


def get_evolution_headers():
    """Get headers for Evolution API requests"""
    headers = {"Content-Type": "application/json"}
    if EVOLUTION_API_KEY:
        headers["apikey"] = EVOLUTION_API_KEY
    return headers


@router.get("/whatsapp/config")
def get_whatsapp_config(
    current_user = Depends(get_current_admin)
):
    """Get WhatsApp/Evolution API configuration from environment"""
    return {
        "evolution_url": EVOLUTION_URL,
        "instance_name": EVOLUTION_INSTANCE,
        "api_key": "",  # Don't return API key for security
        "test_number": WHATSAPP_NUMBER
    }


@router.post("/whatsapp/config")
def save_whatsapp_config(
    config: WhatsAppConfig,
    current_user = Depends(get_current_admin)
):
    """Save WhatsApp/Evolution API configuration to .env file"""
    import re
    
    env_path = ".env"
    try:
        with open(env_path, "r") as f:
            content = f.read()
        
        # Update or add environment variables
        env_vars = {
            "EVOLUTION_API_URL": config.evolution_url,
            "EVOLUTION_INSTANCE": config.instance_name,
        }
        
        if config.api_key:
            env_vars["EVOLUTION_API_KEY"] = config.api_key
        
        for key, value in env_vars.items():
            pattern = f"^{key}=.*$"
            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
            else:
                content += f"\n{key}={value}"
        
        with open(env_path, "w") as f:
            f.write(content)
        
        # Update runtime variables
        global EVOLUTION_URL, EVOLUTION_INSTANCE, EVOLUTION_API_KEY
        EVOLUTION_URL = config.evolution_url
        EVOLUTION_INSTANCE = config.instance_name
        if config.api_key:
            EVOLUTION_API_KEY = config.api_key
        
        return {"message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@router.get("/whatsapp/status")
def get_whatsapp_status(
    current_user = Depends(get_current_admin)
):
    """Get WhatsApp connection status from Evolution API"""
    import requests
    
    if not EVOLUTION_URL:
        raise HTTPException(status_code=400, detail="Evolution API URL not configured. Please set EVOLUTION_API_URL in .env")
    
    try:
        # Try to get instance status from Evolution API
        response = requests.get(
            f"{EVOLUTION_URL}/instance/connectionState/{EVOLUTION_INSTANCE}",
            headers=get_evolution_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "connected": data.get("state") == "open",
                "connecting": data.get("state") in ["connecting", "qr"],
                "number": data.get("number"),
                "state": data.get("state")
            }
        else:
            return {"connected": False, "error": f"Instance not found (status: {response.status_code})"}
    except requests.RequestException as e:
        return {"connected": False, "error": str(e)}


@router.post("/whatsapp/connect")
def connect_whatsapp(
    current_user = Depends(get_current_admin)
):
    """Generate QR code for WhatsApp connection"""
    import requests
    
    if not EVOLUTION_URL:
        raise HTTPException(status_code=400, detail="Evolution API URL not configured")
    
    try:
        print(f"[WhatsApp] Connecting to Evolution at: {EVOLUTION_URL}")
        print(f"[WhatsApp] Instance name: {EVOLUTION_INSTANCE}")
        
        # First, create instance if not exists
        print(f"[WhatsApp] Creating instance...")
        create_response = requests.post(
            f"{EVOLUTION_URL}/instance/create",
            headers=get_evolution_headers(),
            json={
                "instanceName": EVOLUTION_INSTANCE,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS"
            },
            timeout=10
        )
        print(f"[WhatsApp] Create response: {create_response.status_code} - {create_response.text[:200]}")
        
        # Get QR code
        print(f"[WhatsApp] Getting QR code...")
        qr_response = requests.get(
            f"{EVOLUTION_URL}/instance/connect/{EVOLUTION_INSTANCE}",
            headers=get_evolution_headers(),
            timeout=30
        )
        print(f"[WhatsApp] QR response: {qr_response.status_code} - {qr_response.text[:200]}")
        
        if qr_response.status_code == 200:
            data = qr_response.json()
            # Evolution API returns QR in 'base64' or nested in 'qrcode.base64'
            qr_code = data.get('base64') or (data.get('qrcode', {}) or {}).get('base64', '')
            
            # If still no QR, try to get from instance state
            if not qr_code:
                try:
                    state_response = requests.get(
                        f"{EVOLUTION_URL}/instance/connectionState/{EVOLUTION_INSTANCE}",
                        headers=get_evolution_headers(),
                        timeout=10
                    )
                    if state_response.status_code == 200:
                        state_data = state_response.json()
                        instance_data = state_data.get('instance', {})
                        qr_code = instance_data.get('qrcode', '')
                except Exception as e:
                    print(f"[WhatsApp] Error getting state: {e}")
            
            return {
                "qr_code": qr_code,
                "pairing_code": data.get("pairingCode"),
                "message": data.get("message")
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {qr_response.text}")
    except requests.RequestException as e:
        print(f"[WhatsApp] Connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")


@router.post("/whatsapp/pairing")
def get_pairing_code(
    current_user = Depends(get_current_admin)
):
    """Get pairing code for WhatsApp connection"""
    import requests
    
    if not EVOLUTION_URL:
        raise HTTPException(status_code=400, detail="Evolution API URL not configured")
    
    try:
        # Request pairing code
        response = requests.get(
            f"{EVOLUTION_URL}/instance/pairCode/{EVOLUTION_INSTANCE}",
            headers=get_evolution_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"pairing_code": data.get("code")}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to generate pairing code: {response.text}")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")


@router.post("/whatsapp/disconnect")
def disconnect_whatsapp(
    current_user = Depends(get_current_admin)
):
    """Disconnect WhatsApp instance"""
    import requests
    
    if not EVOLUTION_URL:
        raise HTTPException(status_code=400, detail="Evolution API URL not configured")
    
    try:
        response = requests.delete(
            f"{EVOLUTION_URL}/instance/logout/{EVOLUTION_INSTANCE}",
            headers=get_evolution_headers(),
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return {"message": "WhatsApp disconnected successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to disconnect: {response.text}")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")


@router.post("/whatsapp/restart")
def restart_whatsapp_instance(
    current_user = Depends(get_current_admin)
):
    """Restart WhatsApp instance"""
    import requests
    
    if not EVOLUTION_URL:
        raise HTTPException(status_code=400, detail="Evolution API URL not configured")
    
    try:
        response = requests.post(
            f"{EVOLUTION_URL}/instance/restart/{EVOLUTION_INSTANCE}",
            headers=get_evolution_headers(),
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return {"message": "Instance restarted successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restart instance: {response.text}")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")


@router.post("/whatsapp/test")
def send_whatsapp_test(
    number: str,
    message: str,
    current_user = Depends(get_current_admin)
):
    """Send test WhatsApp message"""
    import requests
    
    if not EVOLUTION_URL:
        raise HTTPException(status_code=400, detail="Evolution API URL not configured")
    
    try:
        response = requests.post(
            f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}",
            headers=get_evolution_headers(),
            json={
                "number": number,
                "text": message,
                "options": {
                    "delay": 0,
                    "presence": "composing"
                }
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return {"message": "Test message sent successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to send message: {response.text}")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")


# Landing Page & Carousel Management Endpoints

@router.get("/landing-config")
def get_landing_config(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get landing page configuration"""
    config = db.query(LandingPageConfig).first()
    if not config:
        config = LandingPageConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/landing-config")
def update_landing_config(
    hero_title: str = None,
    hero_subtitle: str = None,
    hero_description: str = None,
    primary_color: str = None,
    secondary_color: str = None,
    accent_color: str = None,
    show_countdown: bool = None,
    show_prize_section: bool = None,
    show_features: bool = None,
    show_testimonials: bool = None,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update landing page configuration"""
    config = db.query(LandingPageConfig).first()
    if not config:
        config = LandingPageConfig()
        db.add(config)
    
    if hero_title is not None:
        config.hero_title = hero_title
    if hero_subtitle is not None:
        config.hero_subtitle = hero_subtitle
    if hero_description is not None:
        config.hero_description = hero_description
    if primary_color is not None:
        config.primary_color = primary_color
    if secondary_color is not None:
        config.secondary_color = secondary_color
    if accent_color is not None:
        config.accent_color = accent_color
    if show_countdown is not None:
        config.show_countdown = show_countdown
    if show_prize_section is not None:
        config.show_prize_section = show_prize_section
    if show_features is not None:
        config.show_features = show_features
    if show_testimonials is not None:
        config.show_testimonials = show_testimonials
    
    db.commit()
    db.refresh(config)
    return config


@router.get("/carousel")
def get_carousel_images(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all carousel images"""
    images = db.query(CarouselImage).order_by(CarouselImage.order).all()
    return images


@router.post("/carousel")
def add_carousel_image(
    image_url: str,
    title: str = None,
    subtitle: str = None,
    button_text: str = None,
    button_link: str = None,
    order: int = 0,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add new carousel image"""
    image = CarouselImage(
        image_url=image_url,
        title=title,
        subtitle=subtitle,
        button_text=button_text,
        button_link=button_link,
        order=order,
        is_active=True
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.put("/carousel/{image_id}")
def update_carousel_image(
    image_id: int,
    image_url: str = None,
    title: str = None,
    subtitle: str = None,
    button_text: str = None,
    button_link: str = None,
    order: int = None,
    is_active: bool = None,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update carousel image"""
    image = db.query(CarouselImage).filter(CarouselImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if image_url is not None:
        image.image_url = image_url
    if title is not None:
        image.title = title
    if subtitle is not None:
        image.subtitle = subtitle
    if button_text is not None:
        image.button_text = button_text
    if button_link is not None:
        image.button_link = button_link
    if order is not None:
        image.order = order
    if is_active is not None:
        image.is_active = is_active
    
    db.commit()
    db.refresh(image)
    return image


@router.delete("/carousel/{image_id}")
def delete_carousel_image(
    image_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete carousel image"""
    image = db.query(CarouselImage).filter(CarouselImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db.delete(image)
    db.commit()
    return {"message": "Image deleted successfully"}


# ============================================================================
# Admin: Estender prazo de palpite e lançar palpite por usuário
# ============================================================================

class MatchDeadlineRequest(BaseModel):
    """Define ou limpa o prazo (override) para palpites de uma partida.

    - prediction_deadline = None  -> remove o override (volta a usar match_date - 10min)
    - prediction_deadline = datetime  -> palpites permitidos ate esse instante (Brasilia)
    """
    prediction_deadline: Optional[datetime] = None


@router.put("/matches/{match_id}/deadline")
def set_match_prediction_deadline(
    match_id: int,
    data: MatchDeadlineRequest,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Define/limpa um prazo customizado de palpite para a partida (horario de Brasilia)."""
    from datetime import timezone, timedelta
    
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    # Se recebeu um datetime, garantir que fique em horario de Brasilia (UTC-3)
    if data.prediction_deadline:
        # Se tem timezone info, converte para Brasilia (UTC-3)
        if data.prediction_deadline.tzinfo:
            brasilia_tz = timezone(timedelta(hours=-3))
            deadline = data.prediction_deadline.astimezone(brasilia_tz).replace(tzinfo=None)
        else:
            # Sem timezone, assume que ja esta em horario de Brasilia
            deadline = data.prediction_deadline
        match.prediction_deadline = deadline
    else:
        match.prediction_deadline = None
    
    match.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(match)

    return {
        "message": "Prazo atualizado com sucesso",
        "match_id": match.id,
        "match_date": match.match_date.isoformat() if match.match_date else None,
        "prediction_deadline": match.prediction_deadline.isoformat() if match.prediction_deadline else None,
    }


@router.delete("/matches/{match_id}/deadline")
def clear_match_prediction_deadline(
    match_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Remove o prazo customizado, voltando ao padrao (10 minutos antes do jogo)."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    match.prediction_deadline = None
    match.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(match)

    return {"message": "Prazo customizado removido", "match_id": match.id}


class AdminPredictionRequest(BaseModel):
    """Lancamento de palpite pelo admin em nome de um usuario.
    Bypassa as verificacoes de prazo e pagamento.
    """
    user_id: int
    match_id: int
    predicted_score_a: int
    predicted_score_b: int


@router.post("/predictions")
def admin_create_or_update_prediction(
    data: AdminPredictionRequest,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cria ou atualiza um palpite em nome de um usuario, ignorando prazos e pagamentos.

    Util para lancar palpite a qualquer momento (antes ou apos o prazo).
    Se a partida ja estiver finalizada, recalcula a pontuacao do palpite.
    """
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    match = db.query(Match).filter(Match.id == data.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    if data.predicted_score_a < 0 or data.predicted_score_b < 0:
        raise HTTPException(status_code=400, detail="Placar nao pode ser negativo")
    if data.predicted_score_a > 20 or data.predicted_score_b > 20:
        raise HTTPException(status_code=400, detail="Placar maximo permitido: 20")

    prediction = db.query(Prediction).filter(
        Prediction.user_id == data.user_id,
        Prediction.match_id == data.match_id
    ).first()

    created = False
    if prediction:
        prediction.predicted_score_a = data.predicted_score_a
        prediction.predicted_score_b = data.predicted_score_b
    else:
        prediction = Prediction(
            user_id=data.user_id,
            match_id=data.match_id,
            predicted_score_a=data.predicted_score_a,
            predicted_score_b=data.predicted_score_b,
        )
        db.add(prediction)
        created = True

    db.commit()
    db.refresh(prediction)

    # Se a partida ja terminou, recalcula pontos para esse palpite
    if match.status == MatchStatus.FINISHED and match.score_a is not None and match.score_b is not None:
        from app.services.points_calculator import calculate_points
        total, winner, score_a, score_b, exact = calculate_points(match, prediction)
        prediction.points_earned = total
        prediction.points_winner = winner
        prediction.points_score_a = score_a
        prediction.points_score_b = score_b
        prediction.points_exact = exact
        db.commit()
        db.refresh(prediction)

        # Atualiza ranking da rodada e geral
        try:
            from app.routers.rankings import calculate_round_ranking_internal, calculate_general_ranking_internal
            if match.round_number:
                calculate_round_ranking_internal(match.round_number, db)
            calculate_general_ranking_internal(db)
        except Exception as e:
            print(f"[admin_create_prediction] erro ao recalcular ranking: {e}")

    return {
        "message": "Palpite registrado com sucesso" if created else "Palpite atualizado com sucesso",
        "created": created,
        "prediction": {
            "id": prediction.id,
            "user_id": prediction.user_id,
            "match_id": prediction.match_id,
            "predicted_score_a": prediction.predicted_score_a,
            "predicted_score_b": prediction.predicted_score_b,
            "points_earned": prediction.points_earned,
        },
    }


@router.get("/predictions/match/{match_id}")
def admin_list_predictions_for_match(
    match_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lista todos os palpites lancados em uma partida (com nome do usuario)."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    rows = db.query(Prediction, User).join(
        User, Prediction.user_id == User.id
    ).filter(Prediction.match_id == match_id).order_by(User.full_name).all()

    return {
        "match": {
            "id": match.id,
            "team_a": match.team_a,
            "team_b": match.team_b,
            "match_date": match.match_date.isoformat() if match.match_date else None,
            "status": match.status.value if hasattr(match.status, "value") else match.status,
        },
        "predictions": [
            {
                "user_id": user.id,
                "user_name": user.full_name,
                "user_email": user.email,
                "predicted_score_a": pred.predicted_score_a,
                "predicted_score_b": pred.predicted_score_b,
                "points_earned": pred.points_earned,
                "created_at": pred.created_at.isoformat() if pred.created_at else None,
            }
            for pred, user in rows
        ],
    }


# ============================================================================
# Admin: Configurar partidas dos 16 avos de final
# ============================================================================

class MatchUpdateRequest(BaseModel):
    team_a: Optional[str] = None
    team_b: Optional[str] = None
    team_a_code: Optional[str] = None
    team_b_code: Optional[str] = None
    match_date: Optional[datetime] = None
    local_time: Optional[str] = None
    brasilia_time: Optional[str] = None
    city: Optional[str] = None
    stadium: Optional[str] = None


@router.get("/matches/round-of-32")
def get_round_of_32_matches(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retorna todas as partidas dos 16 avos de final"""
    from app.models import Stage
    matches = db.query(Match).filter(
        Match.stage == Stage.ROUND_OF_32
    ).order_by(Match.match_number).all()

    return [
        {
            "id": m.id,
            "match_number": m.match_number,
            "team_a": m.team_a,
            "team_b": m.team_b,
            "team_a_code": m.team_a_code,
            "team_b_code": m.team_b_code,
            "match_date": m.match_date.isoformat() if m.match_date else None,
            "local_time": m.local_time,
            "brasilia_time": m.brasilia_time,
            "city": m.city,
            "stadium": m.stadium,
            "status": m.status.value if hasattr(m.status, "value") else m.status,
            "round_number": m.round_number,
        }
        for m in matches
    ]


STAGE_LABEL_MAP = {
    "round_of_32": "16 Avos de Final",
    "round_of_16": "Oitavas de Final",
    "quarter_final": "Quartas de Final",
    "semi_final": "Semifinais",
    "third_place": "Disputa 3º Lugar",
    "final": "Final",
}


@router.get("/matches/knockout")
def get_knockout_matches_by_stage(
    stage: str = "round_of_32",
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retorna partidas de qualquer fase eliminatória, filtrando pelo parâmetro stage."""
    from app.models import Stage as StageEnum

    stage_map = {
        "round_of_32": StageEnum.ROUND_OF_32,
        "round_of_16": StageEnum.ROUND_OF_16,
        "quarter_final": StageEnum.QUARTER_FINAL,
        "semi_final": StageEnum.SEMI_FINAL,
        "third_place": StageEnum.THIRD_PLACE,
        "final": StageEnum.FINAL,
    }

    if stage not in stage_map:
        raise HTTPException(
            status_code=400,
            detail=f"Stage inválido. Use: {', '.join(stage_map.keys())}"
        )

    matches = db.query(Match).filter(
        Match.stage == stage_map[stage]
    ).order_by(Match.match_number).all()

    return {
        "stage": stage,
        "stage_label": STAGE_LABEL_MAP.get(stage, stage),
        "matches": [
            {
                "id": m.id,
                "match_number": m.match_number,
                "team_a": m.team_a,
                "team_b": m.team_b,
                "team_a_code": m.team_a_code,
                "team_b_code": m.team_b_code,
                "match_date": m.match_date.isoformat() if m.match_date else None,
                "local_time": m.local_time,
                "brasilia_time": m.brasilia_time,
                "city": m.city,
                "stadium": m.stadium,
                "status": m.status.value if hasattr(m.status, "value") else m.status,
                "score_a": m.score_a,
                "score_b": m.score_b,
                "penalty_winner": m.penalty_winner,
                "round_number": m.round_number,
            }
            for m in matches
        ]
    }


@router.put("/matches/{match_id}")
def update_match(
    match_id: int,
    data: MatchUpdateRequest,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Atualiza dados de uma partida (times, data, horario, local)"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida nao encontrada")

    if data.team_a is not None:
        match.team_a = data.team_a
    if data.team_b is not None:
        match.team_b = data.team_b
    if data.team_a_code is not None:
        match.team_a_code = data.team_a_code
    if data.team_b_code is not None:
        match.team_b_code = data.team_b_code
    if data.match_date is not None:
        match.match_date = data.match_date
    if data.local_time is not None:
        match.local_time = data.local_time
    if data.brasilia_time is not None:
        match.brasilia_time = data.brasilia_time
    if data.city is not None:
        match.city = data.city
    if data.stadium is not None:
        match.stadium = data.stadium

    match.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(match)

    return {
        "message": "Partida atualizada com sucesso",
        "match": {
            "id": match.id,
            "match_number": match.match_number,
            "team_a": match.team_a,
            "team_b": match.team_b,
            "team_a_code": match.team_a_code,
            "team_b_code": match.team_b_code,
            "match_date": match.match_date.isoformat() if match.match_date else None,
            "local_time": match.local_time,
            "brasilia_time": match.brasilia_time,
            "city": match.city,
            "stadium": match.stadium,
        }
    }


@router.delete("/predictions/{user_id}/{match_id}")
def admin_delete_prediction(
    user_id: int,
    match_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Remove um palpite especifico de um usuario para uma partida."""
    prediction = db.query(Prediction).filter(
        Prediction.user_id == user_id,
        Prediction.match_id == match_id
    ).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Palpite nao encontrado")

    db.delete(prediction)
    db.commit()
    return {"message": "Palpite removido com sucesso"}

