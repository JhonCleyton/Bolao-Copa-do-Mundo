#!/usr/bin/env python3
"""
Script simples para desfazer finalização - edite o match_id abaixo e execute
"""
from datetime import datetime
from app.database import SessionLocal
from app.models import Match, MatchStatus, Prediction
from app.routers.rankings import calculate_round_ranking_internal, calculate_general_ranking_internal

# ========== CONFIGURE AQUI ==========
MATCH_ID = 1  # <-- ALTERE PARA O ID DO JOGO QUE DESEJA DESFINALIZAR
CLEAR_SCORE = False  # <-- True para limpar placar, False para manter
# ===================================

def main():
    db = SessionLocal()
    
    try:
        # 1. Buscar jogo
        match = db.query(Match).filter(Match.id == MATCH_ID).first()
        if not match:
            print(f"Jogo {MATCH_ID} não encontrado!")
            return
        
        print(f"Processando: {match.team_a} x {match.team_b}")
        print(f"Status atual: {match.status.value}")
        
        # 2. Reverter para live
        match.status = MatchStatus.LIVE
        if CLEAR_SCORE:
            match.score_a = None
            match.score_b = None
            print("Placar limpo")
        
        # 3. Zerar pontos das previsões
        predictions = db.query(Prediction).filter(Prediction.match_id == MATCH_ID).all()
        for pred in predictions:
            pred.points_earned = 0
            pred.points_winner = 0
            pred.points_score_a = 0
            pred.points_score_b = 0
            pred.points_exact = 0
        
        print(f"Zerados pontos de {len(predictions)} previsões")
        
        # 4. Salvar
        db.commit()
        
        # 5. Recalcular rankings
        if match.round_number:
            calculate_round_ranking_internal(match.round_number, db)
            print(f"Ranking da rodada {match.round_number} recalculado")
        
        calculate_general_ranking_internal(db)
        print("Ranking geral recalculado")
        
        db.commit()
        print("✅ Pronto! Jogo desfinalizado.")
        
    except Exception as e:
        db.rollback()
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
