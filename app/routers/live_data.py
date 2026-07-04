"""
Live Data Router
Endpoints for fetching live match data from external football APIs
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.auth import get_current_admin, get_current_user
from app.models import User, Match
from app.services.football_api_service import football_api_service
from app.utils.timezone import get_brasilia_now

router = APIRouter()


@router.get("/sync-match/{match_id}")
def sync_match_from_api(
    match_id: int,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Sync a specific match with live API data (admin only)"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    
    success = football_api_service.sync_match_with_api(match, db)
    
    if success:
        return {
            "message": "Partida sincronizada com sucesso!",
            "match": {
                "id": match.id,
                "team_a": match.team_a,
                "team_b": match.team_b,
                "score_a": match.score_a,
                "score_b": match.score_b,
                "status": match.status.value if hasattr(match.status, 'value') else match.status
            }
        }
    else:
        raise HTTPException(status_code=400, detail="Não foi possível sincronizar com a API externa")


@router.post("/sync-all-live")
def sync_all_live_matches(
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Sync all live or scheduled matches with API (admin only)"""
    from app.models import MatchStatus
    
    # Get matches that are live or scheduled for today
    today = get_brasilia_now().date()
    tomorrow = today + timedelta(days=1)
    
    matches = db.query(Match).filter(
        Match.status.in_([MatchStatus.LIVE, MatchStatus.SCHEDULED]),
        Match.match_date >= today,
        Match.match_date < tomorrow + timedelta(days=1)
    ).all()
    
    if not matches:
        return {"message": "Nenhuma partida para sincronizar hoje", "synced": 0}
    
    synced_count = 0
    failed_count = 0
    results = []
    
    for match in matches:
        success = football_api_service.sync_match_with_api(match, db)
        if success:
            synced_count += 1
            results.append(f"✅ {match.team_a} x {match.team_b}")
        else:
            failed_count += 1
            results.append(f"❌ {match.team_a} x {match.team_b}")
    
    return {
        "message": f"Sincronização completa: {synced_count} sucesso, {failed_count} falhas",
        "synced": synced_count,
        "failed": failed_count,
        "details": results
    }


@router.get("/search-external")
def search_external_fixture(
    team_a: str,
    team_b: str,
    date: Optional[str] = None,
    current_user: User = Depends(get_current_admin)
):
    """Search for a fixture in external API"""
    fixture = football_api_service.search_fixture(team_a, team_b, date)
    
    if not fixture:
        raise HTTPException(status_code=404, detail="Partida não encontrada na API externa")
    
    return {
        "fixture": fixture,
        "message": "Partida encontrada!"
    }


@router.get("/match-details/{match_id}")
def get_match_details_endpoint(
    match_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get detailed match information including score and status"""
    details = football_api_service.get_match_details(match_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Não foi possível obter detalhes da partida")
    
    return details


@router.get("/live-now")
def get_live_matches_now(
    current_user: User = Depends(get_current_user)
):
    """Get all currently live matches from external API"""
    fixtures = football_api_service.get_live_fixtures()
    
    return {
        "count": len(fixtures),
        "matches": fixtures
    }


@router.get("/match-events/{match_id}")
def get_match_events_formatted(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get formatted match events (goals, cards, etc) for display"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    
    # Search for match in API
    api_match = football_api_service.search_fixture(
        match.team_a, 
        match.team_b, 
        str(match.match_date.date()) if match.match_date else None
    )
    
    if not api_match:
        raise HTTPException(status_code=404, detail="Partida não encontrada na API externa")
    
    # football-data.org uses "id" directly
    api_match_id = api_match.get("id")
    formatted_events = football_api_service.get_match_events_formatted(api_match_id)
    
    return {
        "match": f"{match.team_a} x {match.team_b}",
        "formatted": formatted_events
    }


@router.get("/world-cup-schedule")
def get_world_cup_schedule(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get World Cup 2026 schedule from API"""
    today = get_brasilia_now().date()
    date_from = str(today)
    date_to = str(today + timedelta(days=days))
    
    fixtures = football_api_service.get_world_cup_fixtures(date_from, date_to)
    
    return {
        "period": f"{date_from} a {date_to}",
        "count": len(fixtures),
        "fixtures": fixtures
    }
