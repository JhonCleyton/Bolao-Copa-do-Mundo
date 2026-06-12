"""
PVP Bet Calculator Service
Calcula resultados de apostas PVP entre jogadores
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime
from typing import List, Tuple, Optional

from app.models import PVPBet, PVPBetType, PVPBetStatus, Prediction, Match, User
from app.services.whatsapp_service import whatsapp_service


class PVPCalculator:
    """Calculates PVP bet results and notifies winners"""

    @staticmethod
    def calculate_match_bet_result(bet: PVPBet, db: Session) -> Optional[int]:
        """
        Calculate result for a match bet
        Returns winner_id or None if tie/cannot calculate
        """
        if not bet.match_id:
            return None

        # Get both users' predictions for this match
        challenger_pred = db.query(Prediction).filter(
            and_(
                Prediction.user_id == bet.challenger_id,
                Prediction.match_id == bet.match_id
            )
        ).first()

        challenged_pred = db.query(Prediction).filter(
            and_(
                Prediction.user_id == bet.challenged_id,
                Prediction.match_id == bet.match_id
            )
        ).first()

        # If either didn't make predictions, check match results
        match = db.query(Match).filter(Match.id == bet.match_id).first()
        if not match or match.status.value != "finished":
            return None

        # Calculate points earned by each user for this match
        challenger_points = challenger_pred.points_earned if challenger_pred else 0
        challenged_points = challenged_pred.points_earned if challenged_pred else 0

        # Store points
        bet.challenger_points = challenger_points
        bet.challenged_points = challenged_points

        # Determine winner
        if challenger_points > challenged_points:
            return bet.challenger_id
        elif challenged_points > challenger_points:
            return bet.challenged_id
        else:
            return None  # Tie

    @staticmethod
    def calculate_round_bet_result(bet: PVPBet, db: Session) -> Optional[int]:
        """
        Calculate result for a round bet
        Returns winner_id or None if tie/cannot calculate
        """
        if not bet.round_number:
            return None

        # Check if all matches in round are finished
        unfinished = db.query(Match).filter(
            and_(
                Match.round_number == bet.round_number,
                Match.status != "finished"
            )
        ).count()

        if unfinished > 0:
            return None  # Round not complete yet

        # Get all predictions for this round by both users
        challenger_points = db.query(func.sum(Prediction.points_earned)).join(
            Match, Prediction.match_id == Match.id
        ).filter(
            and_(
                Prediction.user_id == bet.challenger_id,
                Match.round_number == bet.round_number
            )
        ).scalar() or 0

        challenged_points = db.query(func.sum(Prediction.points_earned)).join(
            Match, Prediction.match_id == Match.id
        ).filter(
            and_(
                Prediction.user_id == bet.challenged_id,
                Match.round_number == bet.round_number
            )
        ).scalar() or 0

        # Store points
        bet.challenger_points = challenger_points
        bet.challenged_points = challenged_points

        # Determine winner
        if challenger_points > challenged_points:
            return bet.challenger_id
        elif challenged_points > challenger_points:
            return bet.challenged_id
        else:
            return None  # Tie

    @staticmethod
    def calculate_championship_bet_result(bet: PVPBet, db: Session) -> Optional[int]:
        """
        Calculate result for championship bet (based on general ranking)
        Returns winner_id or None if tie/cannot calculate
        """
        # Check if championship is over (all matches finished)
        unfinished = db.query(Match).filter(
            Match.status != "finished"
        ).count()

        if unfinished > 0:
            return None  # Championship not over yet

        # Calculate total points for both users across all matches
        challenger_points = db.query(func.sum(Prediction.points_earned)).filter(
            Prediction.user_id == bet.challenger_id
        ).scalar() or 0

        challenged_points = db.query(func.sum(Prediction.points_earned)).filter(
            Prediction.user_id == bet.challenged_id
        ).scalar() or 0

        # Store points
        bet.challenger_points = challenger_points
        bet.challenged_points = challenged_points

        # Determine winner
        if challenger_points > challenged_points:
            return bet.challenger_id
        elif challenged_points > challenger_points:
            return bet.challenged_id
        else:
            return None  # Tie

    @classmethod
    def process_bet(cls, bet: PVPBet, db: Session) -> bool:
        """
        Process a single PVP bet and determine winner
        Returns True if bet was completed
        """
        if bet.status != PVPBetStatus.ACCEPTED:
            return False

        winner_id = None

        try:
            if bet.bet_type == PVPBetType.MATCH:
                winner_id = cls.calculate_match_bet_result(bet, db)
            elif bet.bet_type == PVPBetType.ROUND:
                winner_id = cls.calculate_round_bet_result(bet, db)
            elif bet.bet_type == PVPBetType.CHAMPIONSHIP:
                winner_id = cls.calculate_championship_bet_result(bet, db)

            # If we got a result (can be None for tie)
            if bet.challenger_points is not None and bet.challenged_points is not None:
                bet.winner_id = winner_id
                bet.status = PVPBetStatus.COMPLETED
                bet.completed_at = datetime.utcnow()
                db.commit()

                # Send notifications
                cls._send_result_notifications(bet, db)
                return True

        except Exception as e:
            print(f"[PVP] Error processing bet {bet.id}: {e}")
            db.rollback()
            return False

        return False

    @classmethod
    def _send_result_notifications(cls, bet: PVPBet, db: Session):
        """Send WhatsApp notifications to both participants"""
        try:
            challenger = db.query(User).filter(User.id == bet.challenger_id).first()
            challenged = db.query(User).filter(User.id == bet.challenged_id).first()

            if not challenger or not challenged:
                return

            match_details = None
            bet_type_str = bet.bet_type.value if hasattr(bet.bet_type, 'value') else str(bet.bet_type)

            if bet.match_id:
                match = db.query(Match).filter(Match.id == bet.match_id).first()
                if match:
                    match_details = f"{match.team_a} x {match.team_b}"

            # Notify challenger
            challenger_won = bet.winner_id == bet.challenger_id
            whatsapp_service.send_pvp_match_result(
                phone=challenger.phone,
                user_name=challenger.full_name,
                opponent_name=challenged.full_name,
                prize_description=bet.prize_description,
                user_points=bet.challenger_points,
                opponent_points=bet.challenged_points,
                won=challenger_won,
                bet_type=bet_type_str,
                match_details=match_details
            )

            # Notify challenged
            challenged_won = bet.winner_id == bet.challenged_id
            whatsapp_service.send_pvp_match_result(
                phone=challenged.phone,
                user_name=challenged.full_name,
                opponent_name=challenger.full_name,
                prize_description=bet.prize_description,
                user_points=bet.challenged_points,
                opponent_points=bet.challenger_points,
                won=challenged_won,
                bet_type=bet_type_str,
                match_details=match_details
            )

        except Exception as e:
            print(f"[PVP] Error sending result notifications: {e}")

    @classmethod
    def process_all_pending_bets(cls, db: Session) -> Tuple[int, int]:
        """
        Process all accepted bets that can be completed
        Returns (processed_count, error_count)
        """
        bets = db.query(PVPBet).filter(
            PVPBet.status == PVPBetStatus.ACCEPTED
        ).all()

        processed = 0
        errors = 0

        for bet in bets:
            if cls.process_bet(bet, db):
                processed += 1
            else:
                # Check if bet should be marked as error
                if bet.challenger_points is None:
                    errors += 1

        return processed, errors

    @classmethod
    def check_expired_challenges(cls, db: Session) -> int:
        """
        Mark expired pending challenges
        Returns number of expired challenges
        """
        expired = db.query(PVPBet).filter(
            and_(
                PVPBet.status == PVPBetStatus.PENDING,
                PVPBet.expires_at < datetime.utcnow()
            )
        ).all()

        count = 0
        for bet in expired:
            bet.status = PVPBetStatus.EXPIRED
            count += 1

        if count > 0:
            db.commit()

        return count


# Global instance
pvp_calculator = PVPCalculator()
