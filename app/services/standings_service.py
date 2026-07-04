"""
Service for automatic group standings and knockout stage updates
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional

from app.models import Match, MatchStatus, GroupStanding, Stage


def update_group_standings(db: Session, group: str):
    """
    Update group standings automatically based on finished matches
    Called when a group stage match is finished
    """
    # Get all finished matches for this group
    matches = db.query(Match).filter(
        Match.group == group,
        Match.stage == Stage.GROUP_STAGE,
        Match.status == MatchStatus.FINISHED,
        Match.score_a.isnot(None),
        Match.score_b.isnot(None)
    ).all()
    
    if not matches:
        return
    
    # Get all unique teams in this group
    teams = {}
    for match in matches:
        if match.team_a not in teams:
            teams[match.team_a] = {
                'code': match.team_a_code,
                'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                'gf': 0, 'ga': 0, 'points': 0
            }
        if match.team_b not in teams:
            teams[match.team_b] = {
                'code': match.team_b_code,
                'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                'gf': 0, 'ga': 0, 'points': 0
            }
    
    # Calculate stats for each match
    for match in matches:
        team_a = match.team_a
        team_b = match.team_b
        score_a = match.score_a
        score_b = match.score_b
        
        # Update played
        teams[team_a]['played'] += 1
        teams[team_b]['played'] += 1
        
        # Update goals
        teams[team_a]['gf'] += score_a
        teams[team_a]['ga'] += score_b
        teams[team_b]['gf'] += score_b
        teams[team_b]['ga'] += score_a
        
        # Update results
        if score_a > score_b:
            teams[team_a]['won'] += 1
            teams[team_a]['points'] += 3
            teams[team_b]['lost'] += 1
        elif score_b > score_a:
            teams[team_b]['won'] += 1
            teams[team_b]['points'] += 3
            teams[team_a]['lost'] += 1
        else:
            teams[team_a]['drawn'] += 1
            teams[team_a]['points'] += 1
            teams[team_b]['drawn'] += 1
            teams[team_b]['points'] += 1
    
    # Sort teams by points, then goal difference, then goals for
    sorted_teams = sorted(
        teams.items(),
        key=lambda x: (-x[1]['points'], -(x[1]['gf'] - x[1]['ga']), -x[1]['gf'])
    )
    
    # Clear existing standings for this group
    db.query(GroupStanding).filter(GroupStanding.group == group).delete()
    
    # Create new standings
    for position, (team_name, stats) in enumerate(sorted_teams, start=1):
        standing = GroupStanding(
            group=group,
            team=team_name,
            team_code=stats['code'],
            played=stats['played'],
            won=stats['won'],
            drawn=stats['drawn'],
            lost=stats['lost'],
            goals_for=stats['gf'],
            goals_against=stats['ga'],
            goal_difference=stats['gf'] - stats['ga'],
            points=stats['points'],
            position=position
        )
        db.add(standing)
    
    db.commit()


def get_knockout_teams(db: Session, group: str) -> Dict[str, Optional[Dict]]:
    """
    Get 1st, 2nd, and 3rd place teams from a group
    Returns None if group is not decided yet
    """
    standings = db.query(GroupStanding).filter(
        GroupStanding.group == group
    ).order_by(GroupStanding.position).all()
    
    if len(standings) < 3:
        # Check if all matches are finished
        total_matches = db.query(Match).filter(
            Match.group == group,
            Match.stage == Stage.GROUP_STAGE
        ).count()
        
        finished_matches = db.query(Match).filter(
            Match.group == group,
            Match.stage == Stage.GROUP_STAGE,
            Match.status == MatchStatus.FINISHED
        ).count()
        
        if finished_matches < total_matches:
            return {'1st': None, '2nd': None, '3rd': None}
    
    return {
        '1st': standings[0] if len(standings) > 0 else None,
        '2nd': standings[1] if len(standings) > 1 else None,
        '3rd': standings[2] if len(standings) > 2 else None
    }


def update_knockout_match(db: Session, match_number: int, winner: str, winner_code: str):
    """
    Update a knockout match with the winning team
    """
    # Find next match that needs this winner
    next_matches = db.query(Match).filter(
        Match.match_number > match_number,
        Match.stage.in_([
            Stage.ROUND_OF_32, Stage.ROUND_OF_16, 
            Stage.QUARTER_FINAL, Stage.SEMI_FINAL,
            Stage.THIRD_PLACE, Stage.FINAL
        ])
    ).all()
    
    for next_match in next_matches:
        # Check if this winner should be team_a or team_b
        if f"Vencedor {match_number}" in next_match.team_a or f"W{match_number}" in next_match.team_a_code:
            next_match.team_a = winner
            next_match.team_a_code = winner_code
            db.commit()
            return True
        elif f"Vencedor {match_number}" in next_match.team_b or f"W{match_number}" in next_match.team_b_code:
            next_match.team_b = winner
            next_match.team_b_code = winner_code
            db.commit()
            return True
        
        # For losers (3rd place match)
        if f"Perdedor {match_number}" in next_match.team_a or f"L{match_number}" in next_match.team_a_code:
            # Get loser from the match
            match = db.query(Match).filter(Match.match_number == match_number).first()
            if match:
                loser = match.team_b if match.team_a == winner else match.team_a
                loser_code = match.team_b_code if match.team_a == winner else match.team_a_code
                next_match.team_a = loser
                next_match.team_a_code = loser_code
                db.commit()
            return True
        elif f"Perdedor {match_number}" in next_match.team_b or f"L{match_number}" in next_match.team_b_code:
            match = db.query(Match).filter(Match.match_number == match_number).first()
            if match:
                loser = match.team_b if match.team_a == winner else match.team_a
                loser_code = match.team_b_code if match.team_a == winner else match.team_a_code
                next_match.team_b = loser
                next_match.team_b_code = loser_code
                db.commit()
            return True
    
    return False


def update_all_group_standings(db: Session):
    """Update standings for all groups"""
    groups = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    for group in groups:
        update_group_standings(db, group)


def check_and_update_knockout_matches(db: Session):
    """
    Check if all groups are decided and update knockout matches
    """
    groups = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    group_winners = {}
    
    for group in groups:
        winners = get_knockout_teams(db, group)
        group_winners[group] = winners
    
    # Update Round of 32 matches
    round_of_32 = db.query(Match).filter(
        Match.stage == Stage.ROUND_OF_32
    ).all()
    
    for match in round_of_32:
        updated = False
        
        # Pattern: "1º Grupo X" -> 1st place from group X
        for group in groups:
            first = group_winners[group].get('1st')
            second = group_winners[group].get('2nd')
            third = group_winners[group].get('3rd')
            
            if first:
                # Check for 1st place references
                if f"1º Grupo {group}" in match.team_a or f"1{group}" in match.team_a_code:
                    match.team_a = first.team
                    match.team_a_code = first.team_code
                    updated = True
                if f"1º Grupo {group}" in match.team_b or f"1{group}" in match.team_b_code:
                    match.team_b = first.team
                    match.team_b_code = first.team_code
                    updated = True
            
            if second:
                # Check for 2nd place references
                if f"2º Grupo {group}" in match.team_a or f"2{group}" in match.team_a_code:
                    match.team_a = second.team
                    match.team_a_code = second.team_code
                    updated = True
                if f"2º Grupo {group}" in match.team_b or f"2{group}" in match.team_b_code:
                    match.team_b = second.team
                    match.team_b_code = second.team_code
                    updated = True
            
            if third:
                # Check for 3rd place references
                if f"3º Grupo {group}" in match.team_a or f"3{group}" in match.team_a_code:
                    match.team_a = third.team
                    match.team_a_code = third.team_code
                    updated = True
                if f"3º Grupo {group}" in match.team_b or f"3{group}" in match.team_b_code:
                    match.team_b = third.team
                    match.team_b_code = third.team_code
                    updated = True
        
        if updated:
            db.commit()


def auto_update_standings_on_match_finish(db: Session, match: Match):
    """
    Main function to call when a match finishes
    Updates group standings and potentially knockout matches
    """
    if match.stage == Stage.GROUP_STAGE and match.group:
        # Update this group's standings
        update_group_standings(db, match.group)
        
        # Check if we can update knockout matches
        check_and_update_knockout_matches(db)
    
    elif match.stage in [
        Stage.ROUND_OF_32, Stage.ROUND_OF_16, 
        Stage.QUARTER_FINAL, Stage.SEMI_FINAL
    ]:
        # Determine winner and update next round
        if match.score_a > match.score_b:
            winner = match.team_a
            winner_code = match.team_a_code
        elif match.score_b > match.score_a:
            winner = match.team_b
            winner_code = match.team_b_code
        elif match.penalty_winner == "A":
            winner = match.team_a
            winner_code = match.team_a_code
        elif match.penalty_winner == "B":
            winner = match.team_b
            winner_code = match.team_b_code
        else:
            # Empate sem vencedor nos penaltis definido - aguardar
            return
        
        update_knockout_match(db, match.match_number, winner, winner_code)
