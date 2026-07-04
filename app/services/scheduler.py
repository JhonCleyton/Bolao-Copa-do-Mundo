from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import json
import os
import requests
import tempfile

from app.database import SessionLocal
from app.models import Match, MatchStatus, User, Prediction, RoundRanking, RoundNotification, Payment
from app.services.whatsapp_service import whatsapp_service
from app.services.email_service import email_service
from app.services.pvp_calculator import pvp_calculator
from app.utils.timezone import get_brasilia_now

scheduler = BackgroundScheduler()
PREDICTION_DEADLINE_MINUTES = 10  # Minutes before match when predictions are locked

_scheduler_lock_fd = None


def _try_acquire_scheduler_lock() -> bool:
    """
    Try to acquire an exclusive file lock so only one gunicorn/uvicorn worker
    runs the background scheduler. Returns True if the lock was acquired.
    On Windows (dev environment) fcntl is unavailable - always returns True.
    """
    global _scheduler_lock_fd
    lock_path = os.path.join(tempfile.gettempdir(), "bolao_scheduler.lock")
    try:
        import fcntl
        fd = open(lock_path, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        _scheduler_lock_fd = fd  # Keep reference alive to hold the lock
        return True
    except ImportError:
        # Windows - fcntl not available, safe to start (dev single-worker)
        return True
    except (IOError, OSError):
        # Lock held by another worker process
        return False


def check_live_matches():
    """Check for matches that should be live and update scores"""
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        
        # Find matches that should be live (started 5 mins ago, not finished)
        matches = db.query(Match).filter(
            Match.status == MatchStatus.SCHEDULED,
            Match.match_date <= now
        ).all()
        
        for match in matches:
            # In production, fetch real scores from API
            # For now, mark as live
            if now >= match.match_date:
                match.status = MatchStatus.LIVE
        
        db.commit()
    except Exception as e:
        print(f"Error checking live matches: {e}")
    finally:
        db.close()


def send_match_reminders():
    """Send reminders 1 hour before matches"""
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        one_hour_from_now = now + timedelta(hours=1)
        
        # Find matches starting in ~1 hour
        matches = db.query(Match).filter(
            Match.status == MatchStatus.SCHEDULED,
            Match.match_date.between(now, one_hour_from_now)
        ).all()
        
        # Send reminders to users who haven't made predictions
        for match in matches:
            # Get users without predictions for this match
            from app.models import User, Prediction
            
            users_without_prediction = db.query(User).filter(
                User.status == "active",
                ~db.query(Prediction).filter(
                    Prediction.user_id == User.id,
                    Prediction.match_id == match.id
                ).exists()
            ).all()
            
            for user in users_without_prediction:
                whatsapp_service.send_match_reminder(
                    user.phone,
                    user.full_name,
                    match.team_a,
                    match.team_b,
                    match.brasilia_time
                )
    except Exception as e:
        print(f"Error sending reminders: {e}")
    finally:
        db.close()


def send_payment_reminders():
    """Send payment reminders for pending payments"""
    db = SessionLocal()
    try:
        from app.models import User, Payment
        
        # Find users with pending registration
        users_pending = db.query(User).filter(
            User.status == "active",
            User.registration_paid == False
        ).all()
        
        for user in users_pending:
            whatsapp_service.send_payment_reminder(user.phone, user.full_name)
        
        # Find users with pending round payments
        pending_rounds = db.query(Payment).filter(
            Payment.paid == False,
            Payment.type == "round"
        ).all()
        
        for payment in pending_rounds:
            user = db.query(User).filter(User.id == payment.user_id).first()
            if user:
                whatsapp_service.send_payment_reminder(
                    user.phone, 
                    user.full_name, 
                    payment.round_number
                )
    except Exception as e:
        print(f"Error sending payment reminders: {e}")
    finally:
        db.close()


def send_round_start_notifications():
    """
    Send notifications when a new round is starting (day before first match)
    Email + WhatsApp to all active users who paid for that round
    """
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        tomorrow = now + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Find matches starting tomorrow
        tomorrow_matches = db.query(Match).filter(
            Match.match_date.between(tomorrow_start, tomorrow_end),
            Match.status == MatchStatus.SCHEDULED
        ).all()
        
        if not tomorrow_matches:
            return
        
        # Group by round
        rounds_starting = {}
        for match in tomorrow_matches:
            if match.round_number not in rounds_starting:
                rounds_starting[match.round_number] = []
            rounds_starting[match.round_number].append(match)
        
        for round_number, matches in rounds_starting.items():
            # Check if already notified for this round start
            already_notified = db.query(RoundNotification).filter(
                RoundNotification.round_number == round_number,
                RoundNotification.notification_type == 'start'
            ).first()
            
            if already_notified:
                continue
            
            # Get users who paid for this round
            users = db.query(User).filter(
                User.status == "active",
                User.registration_paid == True,
                db.query(Payment).filter(
                    Payment.user_id == User.id,
                    Payment.type == "round",
                    Payment.round_number == round_number,
                    Payment.paid == True
                ).exists()
            ).all()
            
            if not users:
                continue
            
            # Get first match date/time
            first_match = min(matches, key=lambda m: m.match_date)
            
            # Send notifications
            notified_count = 0
            for user in users:
                try:
                    message = f"""🎯 *Bolão Copa 2026 - Rodada {round_number}*

Olá, {user.full_name}!

⚽ A *{round_number}ª Rodada* começa AMANHÃ!

📅 Primeiro jogo: {first_match.team_a} x {first_match.team_b}
🕐 Horário: {first_match.brasilia_time} (Brasília)

✅ Faça seus palpites agora!
💰 Prêmio da rodada: R$ 100,00

Boa sorte! 🍀"""
                    
                    # WhatsApp
                    whatsapp_service._send_message(user.phone, message)
                    
                    # Email
                    email_service._send_email(
                        user.email,
                        f"🏆 Rodada {round_number} começa amanhã! - Bolão Copa 2026",
                        f"<p>Olá, {user.full_name}!</p><p>A <strong>{round_number}ª Rodada</strong> começa amanhã!</p><p>Primeiro jogo: {first_match.team_a} x {first_match.team_b} às {first_match.brasilia_time}</p><p>Faça seus palpites!</p>",
                        message
                    )
                    
                    notified_count += 1
                except Exception as e:
                    print(f"Error notifying user {user.id}: {e}")
            
            # Record notification sent
            notification = RoundNotification(
                round_number=round_number,
                notification_type='start',
                total_users_notified=notified_count
            )
            db.add(notification)
            db.commit()
            
            print(f"✅ Round {round_number} start notifications sent to {notified_count} users")
            
    except Exception as e:
        print(f"Error sending round start notifications: {e}")
    finally:
        db.close()


def send_round_end_notifications():
    """
    Send notifications at the end of each round with:
    - Points earned
    - Round position
    - General ranking position
    - Congratulations to the winner
    """
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        yesterday = now - timedelta(days=1)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Find matches that finished yesterday
        finished_matches = db.query(Match).filter(
            Match.status == MatchStatus.FINISHED,
            Match.updated_at.between(yesterday_start, yesterday_end)
        ).all()
        
        if not finished_matches:
            return
        
        # Group by round
        rounds_ended = {}
        for match in finished_matches:
            if match.round_number not in rounds_ended:
                rounds_ended[match.round_number] = []
            rounds_ended[match.round_number].append(match)
        
        for round_number, matches in rounds_ended.items():
            # Check if all matches in this round are finished
            total_matches = db.query(Match).filter(
                Match.round_number == round_number
            ).count()
            
            finished_count = db.query(Match).filter(
                Match.round_number == round_number,
                Match.status == MatchStatus.FINISHED
            ).count()
            
            if finished_count < total_matches:
                continue  # Round not complete yet
            
            # Check if already notified for this round end
            already_notified = db.query(RoundNotification).filter(
                RoundNotification.round_number == round_number,
                RoundNotification.notification_type == 'end'
            ).first()
            
            if already_notified:
                continue
            
            # Calculate round rankings first
            from app.routers.rankings import calculate_round_ranking_internal
            calculate_round_ranking_internal(round_number, db)
            
            # Get rankings for this round
            rankings = db.query(RoundRanking).filter(
                RoundRanking.round_number == round_number
            ).order_by(RoundRanking.position).all()
            
            if not rankings:
                continue
            
            # Get winner
            winner = rankings[0] if rankings else None
            
            # Send notifications to all users
            notified_count = 0
            for ranking in rankings:
                user = db.query(User).filter(User.id == ranking.user_id).first()
                if not user:
                    continue
                
                try:
                    # Check if this is the winner
                    is_winner = winner and winner.user_id == ranking.user_id and ranking.position == 1
                    
                    if is_winner:
                        # Winner message
                        message = f"""🏆🎉 *PARABÉNS! Você venceu a Rodada {round_number}!* 🎉🏆

Olá, {user.full_name}!

Você foi o CAMPEÃO da {round_number}ª Rodada!

📊 SEU DESEMPENHO:
• Pontos: {ranking.total_points}
• Posição: {ranking.position}º LUGAR 🥇
• Acertos: {ranking.correct_predictions}
• Placares Exatos: {ranking.exact_scores}

💰 PRÊMIO: R$ {ranking.prize_won:.2f}

Continue assim! 🚀"""
                        
                        email_subject = f"🏆 VOCÊ VENCEU A RODADA {round_number}! - Bolão Copa 2026"
                    else:
                        # Regular participant message
                        message = f"""🎯 *Resultado da Rodada {round_number}*

Olá, {user.full_name}!

📊 SEU DESEMPENHO:
• Pontos: {ranking.total_points}
• Posição na Rodada: {ranking.position}º lugar
• Acertos: {ranking.correct_predictions}
• Placares Exatos: {ranking.exact_scores}

🏆 VENCEDOR DA RODADA:
• {winner.user.full_name if winner else 'N/A'} - {winner.total_points if winner else 0} pontos

💰 Seu Prêmio: R$ {ranking.prize_won:.2f}

Continue participando! 💪"""
                        
                        email_subject = f"📊 Resultado da Rodada {round_number} - Bolão Copa 2026"
                    
                    # WhatsApp
                    whatsapp_service._send_message(user.phone, message)
                    
                    # Email
                    email_service._send_email(
                        user.email,
                        email_subject,
                        f"<p>Olá, {user.full_name}!</p><p>Sua pontuação na {round_number}ª Rodada:</p><ul><li>Pontos: {ranking.total_points}</li><li>Posição: {ranking.position}º</li><li>Prêmio: R$ {ranking.prize_won:.2f}</li></ul>",
                        message
                    )
                    
                    notified_count += 1
                except Exception as e:
                    print(f"Error notifying user {ranking.user_id}: {e}")
            
            # Record notification sent
            notification = RoundNotification(
                round_number=round_number,
                notification_type='end',
                total_users_notified=notified_count
            )
            db.add(notification)
            db.commit()
            
            print(f"✅ Round {round_number} end notifications sent to {notified_count} users")
            
    except Exception as e:
        print(f"Error sending round end notifications: {e}")
    finally:
        db.close()


def process_scheduled_messages():
    """Check and send scheduled/recurring messages created by admin"""
    db = SessionLocal()
    try:
        from app.models import ScheduledMessage
        from app.routers.messages import deliver_message
        
        now = get_brasilia_now()
        
        # One-time scheduled messages that are due
        due_messages = db.query(ScheduledMessage).filter(
            ScheduledMessage.status.in_(["scheduled", "pending"]),
            ScheduledMessage.scheduled_at != None,
            ScheduledMessage.scheduled_at <= now,
            ScheduledMessage.sent_at == None
        ).all()
        
        for msg in due_messages:
            try:
                # Atomically claim the message: only one worker will get rowcount=1
                claimed = db.execute(
                    text(
                        "UPDATE scheduled_messages SET status='sending'"
                        " WHERE id=:id AND status IN ('scheduled','pending') AND sent_at IS NULL"
                    ),
                    {"id": msg.id}
                ).rowcount
                db.commit()
                if claimed == 0:
                    continue  # Already claimed by another worker
                db.refresh(msg)
                deliver_message(db, msg)
                print(f"✅ Sent scheduled message {msg.id}")
            except Exception as e:
                print(f"Error sending scheduled message {msg.id}: {e}")
                msg.status = "failed"
                db.commit()
        
        # Recurring messages due to run again
        recurring = db.query(ScheduledMessage).filter(
            ScheduledMessage.status == "scheduled",
            ScheduledMessage.recurrence != None,
            ScheduledMessage.next_run != None,
            ScheduledMessage.next_run <= now
        ).all()
        
        for msg in recurring:
            try:
                claimed = db.execute(
                    text(
                        "UPDATE scheduled_messages SET next_run=NULL"
                        " WHERE id=:id AND status='scheduled' AND next_run IS NOT NULL AND next_run<=:now"
                    ),
                    {"id": msg.id, "now": now}
                ).rowcount
                db.commit()
                if claimed == 0:
                    continue  # Already claimed by another worker
                db.refresh(msg)
                deliver_message(db, msg)
                print(f"🔁 Sent recurring message {msg.id} ({msg.recurrence})")
            except Exception as e:
                print(f"Error sending recurring message {msg.id}: {e}")
    except Exception as e:
        print(f"Error processing scheduled messages: {e}")
    finally:
        db.close()


def process_pvp_bets():
    """Process PVP bets - check for completed matches/rounds and determine winners"""
    db = SessionLocal()
    try:
        # Check for expired challenges
        expired_count = pvp_calculator.check_expired_challenges(db)
        if expired_count > 0:
            print(f"🕐 Marked {expired_count} PVP challenges as expired")

        # Process bets that can be completed
        processed, errors = pvp_calculator.process_all_pending_bets(db)
        if processed > 0:
            print(f"🏆 Completed {processed} PVP bets")
        if errors > 0:
            print(f"⚠️ {errors} PVP bets could not be processed yet")

    except Exception as e:
        print(f"Error processing PVP bets: {e}")
    finally:
        db.close()


def sync_live_matches_with_api():
    """Sync live matches with external football API for automatic score updates"""
    try:
        from app.database import SessionLocal
        from app.models import Match, MatchStatus
        from app.services.football_api_service import football_api_service
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        
        # Get matches scheduled for today or currently live
        now = get_brasilia_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=2)
        
        matches = db.query(Match).filter(
            Match.match_date >= today_start,
            Match.match_date <= today_end,
            Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.LIVE])
        ).all()
        
        if not matches:
            print("🌐 [API Sync] No matches to sync today")
            return
        
        print(f"🌐 [API Sync] Syncing {len(matches)} matches with external API...")
        
        synced_count = 0
        updated_count = 0
        
        for match in matches:
            try:
                # Only sync if API key is configured
                if not football_api_service.api_key:
                    print("⚠️ [API Sync] No API key configured, skipping automatic sync")
                    return
                
                # Sync match data
                success = football_api_service.sync_match_with_api(match, db)
                
                if success:
                    synced_count += 1
                    
                    # Check if score was actually updated
                    if match.status == MatchStatus.LIVE:
                        updated_count += 1
                        print(f"⚽ [API Sync] {match.team_a} {match.score_a} x {match.score_b} {match.team_b} (LIVE)")
                    elif match.status == MatchStatus.FINISHED:
                        print(f"🏁 [API Sync] Match finished: {match.team_a} {match.score_a} x {match.score_b} {match.team_b}")
                        
            except Exception as e:
                print(f"⚠️ [API Sync] Error syncing match {match.id}: {e}")
                continue
        
        if synced_count > 0:
            print(f"✅ [API Sync] Successfully synced {synced_count} matches ({updated_count} live/updated)")
        else:
            print("🌐 [API Sync] No matches found in external API")
            
    except Exception as e:
        print(f"❌ [API Sync] Error in sync process: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler - only runs in one worker process"""
    if not _try_acquire_scheduler_lock():
        print(f"[Scheduler] Skipping startup — another worker already holds the scheduler lock (PID {os.getpid()})")
        return

    print(f"[Scheduler] Lock acquired — starting scheduler (PID {os.getpid()})")

    # Check live matches every 5 minutes
    scheduler.add_job(
        check_live_matches,
        trigger=CronTrigger(minute="*/5"),
        id="check_live_matches",
        replace_existing=True
    )
    
    # Send match reminders every 30 minutes
    scheduler.add_job(
        send_match_reminders,
        trigger=CronTrigger(minute="*/30"),
        id="send_match_reminders",
        replace_existing=True
    )
    
    # Send payment reminders daily at 9 AM
    scheduler.add_job(
        send_payment_reminders,
        trigger=CronTrigger(hour=9, minute=0),
        id="send_payment_reminders",
        replace_existing=True
    )
    
    # Send round start notifications daily at 10 AM (day before round starts)
    scheduler.add_job(
        send_round_start_notifications,
        trigger=CronTrigger(hour=10, minute=0),
        id="send_round_start_notifications",
        replace_existing=True
    )
    
    # Send round end notifications daily at 9 AM (after round ends)
    scheduler.add_job(
        send_round_end_notifications,
        trigger=CronTrigger(hour=9, minute=0),
        id="send_round_end_notifications",
        replace_existing=True
    )
    
    # Process scheduled/recurring admin messages every minute
    scheduler.add_job(
        process_scheduled_messages,
        trigger=CronTrigger(minute="*"),
        id="process_scheduled_messages",
        replace_existing=True
    )

    # Process PVP bets every 10 minutes
    scheduler.add_job(
        process_pvp_bets,
        trigger=CronTrigger(minute="*/10"),
        id="process_pvp_bets",
        replace_existing=True
    )
    
    # Sync live matches with external API every 2 minutes
    scheduler.add_job(
        sync_live_matches_with_api,
        trigger=CronTrigger(minute="*/2"),
        id="sync_live_matches_api",
        replace_existing=True
    )

    scheduler.start()
    print("✅ Scheduler started with all notifications")
    print("   - Live matches check: every 5 min")
    print("   - Match reminders: every 30 min")
    print("   - Payment reminders: daily 9 AM")
    print("   - Round start notifications: daily 10 AM")
    print("   - Round end notifications: daily 9 AM")
    print("   - Scheduled messages: every 1 min")
    print("   - PVP bets processing: every 10 min")
    print("   - Live matches API sync: every 2 min")


def stop_scheduler():
    """Stop the scheduler — only if it was started by this worker"""
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped")
