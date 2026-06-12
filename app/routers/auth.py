from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import random
import string

from app.database import get_db
from app.models import User, UserStatus
from app.schemas import UserCreate, UserResponse, UserLogin, Token, UserVerifyEmail, UserVerifyPhone
from app.auth import (
    get_password_hash, authenticate_user, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.email_service import email_service
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()


def generate_code():
    """Generate 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone exists
    if db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone already registered"
        )
    
    # Create user
    email_code = generate_code()
    phone_code = generate_code()
    
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        status=UserStatus.PENDING,
        email_verification_code=email_code,
        phone_verification_code=phone_code
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send verification codes
    email_service.send_verification_code(user.email, email_code, user.full_name)
    whatsapp_service.send_verification_code(user.phone, phone_code, user.full_name)
    
    return user


@router.post("/verify-email")
def verify_email(data: UserVerifyEmail, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verification_code != data.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    user.email_verified = True
    user.email_verification_code = None
    
    # Activate if both verified
    if user.phone_verified:
        user.status = UserStatus.ACTIVE
        email_service.send_welcome(user.email, user.full_name)
        whatsapp_service.send_welcome(user.phone, user.full_name)
    
    db.commit()
    return {"message": "Email verified successfully"}


@router.post("/verify-phone")
def verify_phone(data: UserVerifyPhone, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.phone_verification_code != data.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    user.phone_verified = True
    user.phone_verification_code = None
    
    # Activate if both verified
    if user.email_verified:
        user.status = UserStatus.ACTIVE
        email_service.send_welcome(user.email, user.full_name)
        whatsapp_service.send_welcome(user.phone, user.full_name)
    
    db.commit()
    return {"message": "Phone verified successfully"}


@router.post("/resend-email-code")
def resend_email_code(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    code = generate_code()
    user.email_verification_code = code
    db.commit()
    
    email_service.send_verification_code(user.email, code, user.full_name)
    return {"message": "Code resent"}


@router.post("/resend-phone-code")
def resend_phone_code(phone: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.phone_verified:
        raise HTTPException(status_code=400, detail="Phone already verified")
    
    code = generate_code()
    user.phone_verification_code = code
    db.commit()
    
    whatsapp_service.send_verification_code(user.phone, code, user.full_name)
    return {"message": "Code resent"}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# Password Recovery Endpoints

@router.post("/forgot-password")
def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """Request password reset - sends email with reset link"""
    user = db.query(User).filter(User.email == email).first()
    
    # Always return success even if user not found (security)
    if not user:
        return {"message": "Se o email existir, você receberá instruções de recuperação."}
    
    # Generate reset token
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset"},
        expires_delta=timedelta(hours=1)
    )
    
    # Store token in user (or you could use a separate table)
    user.email_verification_code = reset_token  # Reusing this field for reset token
    db.commit()
    
    # Send reset email
    reset_url = f"{os.getenv('APP_URL', 'http://localhost:5555')}/resetar-senha?token={reset_token}"
    email_sent = email_service.send_password_reset(user.email, user.full_name, reset_url)
    
    if email_sent:
        return {"message": "Email de recuperação enviado com sucesso!"}
    else:
        return {"message": "Se o email existir, você receberá instruções de recuperação."}


@router.post("/reset-password")
def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Reset password using token"""
    try:
        # Verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")
        
        if token_type != "password_reset":
            raise HTTPException(status_code=400, detail="Token inválido")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        user.email_verification_code = None  # Clear the token
        db.commit()
        
        return {"message": "Senha alterada com sucesso!"}
        
    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
