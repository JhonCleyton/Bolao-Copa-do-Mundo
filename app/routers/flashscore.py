"""
FlashScore Integration Router
Endpoints para buscar resultados ao vivo do FlashScore
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_admin
from app.services.flashscore_scraper import sync_match_from_flashscore

router = APIRouter(prefix="/flashscore", tags=["FlashScore"])


@router.get("/search")
def search_match(
    team_a: str,
    team_b: str,
    current_user = Depends(get_current_admin)
):
    """
    Busca uma partida no FlashScore (admin only)
    """
    result = sync_match_from_flashscore(team_a, team_b)
    
    if not result:
        raise HTTPException(status_code=404, detail="Partida não encontrada no FlashScore")
    
    return result


@router.post("/test-url")
async def test_flashscore_url(
    url: str,
    current_user = Depends(get_current_admin)
):
    """
    Testa scraping de uma URL do FlashScore (admin only)
    Retorna todos os dados extraídos para análise
    """
    from app.services.flashscore_playwright import scrape_match_url
    
    result = await scrape_match_url(url)
    
    if not result:
        raise HTTPException(status_code=404, detail="Não foi possível extrair dados da URL")
    
    return {
        "url": url,
        "extracted_data": result,
        "success": result.get('home_team') is not None and result.get('score_home') is not None
    }


@router.post("/sync-match/{match_id}")
def sync_match_with_flashscore(
    match_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Sincroniza uma partida do nosso sistema com o FlashScore
    Busca os times da partida no banco e procura no FlashScore
    """
    from app.models import Match
    
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    
    # Busca no FlashScore
    flash_data = sync_match_from_flashscore(match.team_a, match.team_b)
    
    if not flash_data:
        return {
            "success": False,
            "message": f"Partida não encontrada no FlashScore: {match.team_a} x {match.team_b}",
            "match": {
                "id": match.id,
                "team_a": match.team_a,
                "team_b": match.team_b,
                "score_a": match.score_a,
                "score_b": match.score_b,
                "status": match.status.value if hasattr(match.status, 'value') else str(match.status)
            }
        }
    
    # Atualiza a partida com os dados do FlashScore
    match.score_a = flash_data['score_home']
    match.score_b = flash_data['score_away']
    
    # Mapeia status
    from app.models import MatchStatus
    status_map = {
        'live': MatchStatus.LIVE,
        'finished': MatchStatus.FINISHED,
        'scheduled': MatchStatus.SCHEDULED
    }
    
    if flash_data['status'] in status_map:
        match.status = status_map[flash_data['status']]
    
    db.commit()
    
    return {
        "success": True,
        "message": "Partida sincronizada com FlashScore",
        "flashscore_data": flash_data,
        "updated_match": {
            "id": match.id,
            "team_a": match.team_a,
            "team_b": match.team_b,
            "score_a": match.score_a,
            "score_b": match.score_b,
            "status": match.status.value if hasattr(match.status, 'value') else str(match.status),
            "minute": flash_data.get('minute')
        }
    }


@router.post("/sync-live-matches")
def sync_all_live_matches(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Sincroniza todas as partidas ao vivo do sistema com FlashScore
    """
    from app.models import Match, MatchStatus
    
    # Pega todas as partidas scheduled ou live
    matches = db.query(Match).filter(
        Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.LIVE])
    ).all()
    
    results = []
    updated_count = 0
    not_found_count = 0
    
    for match in matches:
        flash_data = sync_match_from_flashscore(match.team_a, match.team_b)
        
        if flash_data:
            # Atualiza placar e status
            old_score = f"{match.score_a} x {match.score_b}"
            match.score_a = flash_data['score_home']
            match.score_b = flash_data['score_away']
            new_score = f"{match.score_a} x {match.score_b}"
            
            status_map = {
                'live': MatchStatus.LIVE,
                'finished': MatchStatus.FINISHED,
                'scheduled': MatchStatus.SCHEDULED
            }
            
            if flash_data['status'] in status_map:
                old_status = match.status
                match.status = status_map[flash_data['status']]
                
                # Se finalizou agora, recalcula pontos e rankings
                if old_status != MatchStatus.FINISHED and match.status == MatchStatus.FINISHED:
                    from app.routers.matches import update_score_endpoint
                    # Chama a lógica de finalização
                    from app.services.points_calculator import calculate_points
                    from app.services.standings_service import auto_update_standings_on_match_finish
                    from app.routers.rankings import calculate_round_ranking_internal, calculate_general_ranking_internal
                    from app.models import Prediction
                    
                    predictions = db.query(Prediction).filter(Prediction.match_id == match.id).all()
                    for pred in predictions:
                        total, winner, score_a, score_b, exact = calculate_points(match, pred)
                        pred.points_earned = total
                        pred.points_winner = winner
                        pred.points_score_a = score_a
                        pred.points_score_b = score_b
                        pred.points_exact = exact
                    
                    db.commit()
                    auto_update_standings_on_match_finish(db, match)
                    
                    if match.round_number:
                        calculate_round_ranking_internal(match.round_number, db)
                    calculate_general_ranking_internal(db)
                    
                    print(f"[FlashScore] Partida {match.id} finalizada - rankings atualizados!")
            
            updated_count += 1
            results.append({
                "match_id": match.id,
                "teams": f"{match.team_a} x {match.team_b}",
                "score_changed": old_score != new_score,
                "old_score": old_score,
                "new_score": new_score,
                "status": flash_data['status'],
                "minute": flash_data.get('minute')
            })
        else:
            not_found_count += 1
            results.append({
                "match_id": match.id,
                "teams": f"{match.team_a} x {match.team_b}",
                "error": "Não encontrada no FlashScore"
            })
    
    db.commit()
    
    return {
        "success": True,
        "total_checked": len(matches),
        "updated": updated_count,
        "not_found": not_found_count,
        "results": results
    }
