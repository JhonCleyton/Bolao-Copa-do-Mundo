from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User
from app.schemas import NotificationSend
from app.services.email_service import email_service
from app.services.whatsapp_service import whatsapp_service
from app.auth import get_current_admin

router = APIRouter()


@router.post("/send")
def send_notification(
    notification: NotificationSend,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Send notification to specific user or all users (admin only)"""
    
    if notification.user_id:
        # Send to specific user
        user = db.query(User).filter(User.id == notification.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        users = [user]
    else:
        # Send to all active users
        users = db.query(User).filter(User.status == "active").all()
    
    sent_count = 0
    failed_count = 0
    
    for user in users:
        success = True
        
        # Send email
        if notification.type in ["email", "both"]:
            if not email_service._send_email(
                user.email,
                notification.subject,
                f"<p>{notification.message}</p>",
                notification.message
            ):
                success = False
        
        # Send WhatsApp
        if notification.type in ["whatsapp", "both"]:
            message = f"🎯 *Bolão Copa 2026*\n\n*{notification.subject}*\n\n{notification.message}"
            if not whatsapp_service._send_message(user.phone, message):
                success = False
        
        if success:
            sent_count += 1
        else:
            failed_count += 1
    
    return {
        "message": "Notifications sent",
        "sent": sent_count,
        "failed": failed_count,
        "total": len(users)
    }


@router.post("/test-email")
def test_email(
    to_email: str,
    current_user = Depends(get_current_admin)
):
    """Test email sending"""
    success = email_service._send_email(
        to_email,
        "Test - Bolão Copa 2026",
        "<p>Este é um email de teste do sistema de bolão.</p>",
        "Este é um email de teste do sistema de bolão."
    )
    
    return {"success": success}


@router.post("/test-whatsapp")
def test_whatsapp(
    phone: str,
    current_user = Depends(get_current_admin)
):
    """Test WhatsApp sending"""
    success = whatsapp_service._send_message(
        phone,
        "🎯 *Bolão Copa 2026*\n\nEste é uma mensagem de teste do sistema de bolão."
    )
    
    return {"success": success}


@router.post("/test")
def test_notification(
    to_email: str = None,
    phone: str = None,
    current_user = Depends(get_current_admin)
):
    """Send test notification to specific email and/or WhatsApp"""
    results = {"email": None, "whatsapp": None}
    
    # Send test email
    if to_email:
        email_success = email_service._send_email(
            to_email,
            "🎯 Teste - Bolão Copa 2026",
            "<p>Este é um <b>email de teste</b> do sistema de bolão.</p><p>Se você recebeu esta mensagem, a configuração de email está funcionando corretamente! ✅</p>",
            "Este é um email de teste do sistema de bolão. Se você recebeu esta mensagem, a configuração de email está funcionando corretamente!"
        )
        results["email"] = {"sent": email_success, "to": to_email}
    
    # Send test WhatsApp
    if phone:
        whatsapp_message = (
            "🎯 *Bolão Copa 2026 - Teste*\n\n"
            "Este é uma mensagem de teste do sistema de bolão.\n\n"
            "Se você recebeu esta mensagem, a configuração do WhatsApp está funcionando corretamente! ✅\n\n"
            f"_Enviado por: {current_user.full_name}_"
        )
        whatsapp_success = whatsapp_service._send_message(phone, whatsapp_message)
        results["whatsapp"] = {"sent": whatsapp_success, "to": phone}
    
    # Determine overall success
    any_sent = any(r and r.get("sent") for r in [results["email"], results["whatsapp"]] if r)
    
    return {
        "success": any_sent,
        "message": "Test notifications sent" if any_sent else "No notifications sent - provide email or phone",
 "results": results
    }
