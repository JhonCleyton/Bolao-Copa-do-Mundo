"""
Admin messages router - manage automatic, scheduled and direct messages
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models import User, ScheduledMessage
from app.auth import get_current_admin
from app.services.email_service import email_service
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()


# --- Schemas ---
class MessageCreate(BaseModel):
    title: Optional[str] = None
    subject: str
    message: str
    channel: str  # email, whatsapp, both
    target_type: str  # all, active, user
    target_user_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None  # null = send now
    recurrence: Optional[str] = None  # null, daily, weekly, monthly


# --- Automatic (scheduler) messages ---
AUTOMATIC_MESSAGES = [
    {
        "id": "check_live_matches",
        "name": "Verificar Jogos ao Vivo",
        "description": "Atualiza o status dos jogos para 'ao vivo' quando começam",
        "schedule": "A cada 5 minutos",
        "channel": "Sistema",
        "type": "system"
    },
    {
        "id": "send_match_reminders",
        "name": "Lembretes de Palpite",
        "description": "Envia lembrete WhatsApp 1 hora antes do jogo para quem não palpitou",
        "schedule": "A cada 30 minutos",
        "channel": "WhatsApp",
        "type": "reminder"
    },
    {
        "id": "send_payment_reminders",
        "name": "Lembretes de Pagamento",
        "description": "Envia lembrete de inscrição/rodada pendente para usuários ativos",
        "schedule": "Diariamente às 09:00",
        "channel": "WhatsApp",
        "type": "reminder"
    },
    {
        "id": "send_round_start_notifications",
        "name": "Início de Rodada",
        "description": "Notifica usuários pagantes 1 dia antes do início da rodada",
        "schedule": "Diariamente às 10:00",
        "channel": "Email + WhatsApp",
        "type": "round"
    },
    {
        "id": "send_round_end_notifications",
        "name": "Fim de Rodada",
        "description": "Envia resultado da rodada com pontos, posição e prêmio",
        "schedule": "Diariamente às 09:00",
        "channel": "Email + WhatsApp",
        "type": "round"
    },
    {
        "id": "process_scheduled_messages",
        "name": "Processar Mensagens Agendadas",
        "description": "Verifica e envia mensagens manuais agendadas pelo admin",
        "schedule": "A cada 1 minuto",
        "channel": "Sistema",
        "type": "system"
    },
]


@router.get("/automatic")
def list_automatic_messages(current_user=Depends(get_current_admin)):
    """Return list of automatic scheduled jobs configured in the system"""
    return AUTOMATIC_MESSAGES


# --- Send / Schedule helpers ---
def _resolve_recipients(db: Session, target_type: str, target_user_id: Optional[int]) -> List[User]:
    if target_type == "user":
        if not target_user_id:
            raise HTTPException(status_code=400, detail="target_user_id required when target_type=user")
        user = db.query(User).filter(User.id == target_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return [user]
    elif target_type == "all":
        return db.query(User).all()
    elif target_type == "active":
        return db.query(User).filter(User.status == "active").all()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid target_type: {target_type}")


def deliver_message(db: Session, msg: ScheduledMessage) -> dict:
    """Actually send the message via configured channels. Updates msg in-place."""
    recipients = _resolve_recipients(db, msg.target_type, msg.target_user_id)
    sent = 0
    failed = 0
    
    for user in recipients:
        ok = True
        if msg.channel in ("email", "both"):
            try:
                if not email_service._send_email(
                    user.email,
                    msg.subject,
                    f"<p>{msg.message.replace(chr(10), '<br>')}</p>",
                    msg.message,
                ):
                    ok = False
            except Exception:
                ok = False
        if msg.channel in ("whatsapp", "both"):
            try:
                wa_text = f"🎯 *Bolão Copa 2026*\n\n*{msg.subject}*\n\n{msg.message}"
                if not whatsapp_service._send_message(user.phone, wa_text):
                    ok = False
            except Exception:
                ok = False
        if ok:
            sent += 1
        else:
            failed += 1
    
    msg.sent_count = sent
    msg.failed_count = failed
    msg.sent_at = datetime.utcnow()
    msg.status = "sent" if failed == 0 else ("partial" if sent > 0 else "failed")
    
    # Compute next_run for recurring
    if msg.recurrence:
        from datetime import timedelta
        base = msg.scheduled_at or msg.sent_at
        if msg.recurrence == "daily":
            msg.next_run = base + timedelta(days=1)
        elif msg.recurrence == "weekly":
            msg.next_run = base + timedelta(weeks=1)
        elif msg.recurrence == "monthly":
            msg.next_run = base + timedelta(days=30)
        msg.status = "scheduled"  # remain active for next run
    
    db.commit()
    return {"sent": sent, "failed": failed, "total": len(recipients)}


@router.post("/send")
def send_or_schedule_message(
    data: MessageCreate,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Send immediately or schedule a manual message"""
    if data.channel not in ("email", "whatsapp", "both"):
        raise HTTPException(status_code=400, detail="Invalid channel")
    if data.target_type not in ("all", "active", "user"):
        raise HTTPException(status_code=400, detail="Invalid target_type")
    if data.recurrence and data.recurrence not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="Invalid recurrence")
    
    now = datetime.utcnow()
    is_scheduled = data.scheduled_at and data.scheduled_at > now
    
    msg = ScheduledMessage(
        title=data.title or data.subject,
        subject=data.subject,
        message=data.message,
        channel=data.channel,
        target_type=data.target_type,
        target_user_id=data.target_user_id,
        scheduled_at=data.scheduled_at,
        recurrence=data.recurrence,
        next_run=data.scheduled_at if (is_scheduled and data.recurrence) else None,
        status="scheduled" if (is_scheduled or data.recurrence) else "pending",
        created_by=current_user.id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    if not is_scheduled:
        result = deliver_message(db, msg)
        return {
            "message": "Mensagem enviada",
            "id": msg.id,
            "sent": result["sent"],
            "failed": result["failed"],
            "total": result["total"],
        }
    
    return {
        "message": "Mensagem agendada",
        "id": msg.id,
        "scheduled_at": msg.scheduled_at.isoformat() if msg.scheduled_at else None,
        "recurrence": msg.recurrence,
    }


@router.get("/")
def list_messages(
    status: Optional[str] = None,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all manual messages (sent or scheduled)"""
    query = db.query(ScheduledMessage)
    if status:
        query = query.filter(ScheduledMessage.status == status)
    messages = query.order_by(desc(ScheduledMessage.created_at)).limit(200).all()
    
    result = []
    for m in messages:
        target_name = None
        if m.target_user_id:
            user = db.query(User).filter(User.id == m.target_user_id).first()
            target_name = user.full_name if user else f"User {m.target_user_id}"
        result.append({
            "id": m.id,
            "title": m.title,
            "subject": m.subject,
            "message": m.message,
            "channel": m.channel,
            "target_type": m.target_type,
            "target_user_id": m.target_user_id,
            "target_name": target_name,
            "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "status": m.status,
            "sent_count": m.sent_count,
            "failed_count": m.failed_count,
            "recurrence": m.recurrence,
            "next_run": m.next_run.isoformat() if m.next_run else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return result


@router.delete("/{message_id}")
def cancel_message(
    message_id: int,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Cancel a scheduled message"""
    msg = db.query(ScheduledMessage).filter(ScheduledMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.status == "sent":
        raise HTTPException(status_code=400, detail="Cannot cancel already-sent message")
    msg.status = "cancelled"
    msg.next_run = None
    db.commit()
    return {"message": "Mensagem cancelada"}


@router.post("/{message_id}/resend")
def resend_message(
    message_id: int,
    current_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Re-send an existing message immediately"""
    msg = db.query(ScheduledMessage).filter(ScheduledMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    result = deliver_message(db, msg)
    return {"message": "Reenviada", **result}
