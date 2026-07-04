#!/usr/bin/env python3
"""
Script para desfazer a finalização de um jogo.
Reverte status para 'live', zera pontos das previsões e recalcula rankings.
"""
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Match, MatchStatus, Prediction, RoundRanking, GeneralRanking
from app.routers.rankings import calculate_round_ranking_internal, calculate_general_ranking_internal


def undo_finish_match(match_id: int):
    """Desfazer finalização de um jogo específico"""
    db = SessionLocal()
    
    try:
        # 1. Buscar o jogo
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            print(f"❌ Jogo ID {match_id} não encontrado!")
            return False
        
        print(f"\n📊 Jogo encontrado: {match.team_a} x {match.team_b}")
        print(f"   Status atual: {match.status}")
        print(f"   Placar: {match.score_a} x {match.score_b}")
        print(f"   Rodada: {match.round_number}")
        
        if match.status != MatchStatus.FINISHED:
            print(f"⚠️  Aviso: O jogo não está com status 'finished' (status={match.status})")
            confirm = input("Deseja continuar mesmo assim? (s/N): ")
            if confirm.lower() != 's':
                print("Operação cancelada.")
                return False
        
        # 2. Buscar todas as previsões deste jogo
        predictions = db.query(Prediction).filter(Prediction.match_id == match_id).all()
        print(f"\n📝 Encontradas {len(predictions)} previsões para este jogo")
        
        # 3. Mostrar pontos que serão zerados
        total_points_to_remove = sum(p.points_earned for p in predictions)
        print(f"   Total de pontos a serem removidos: {total_points_to_remove}")
        
        confirm = input("\n⚠️  Confirma que deseja DESFAZER a finalização? (s/N): ")
        if confirm.lower() != 's':
            print("Operação cancelada.")
            return False
        
        # 4. Reverter status do jogo para 'live'
        match.status = MatchStatus.LIVE
        # Opcional: limpar placar também? O usuário pode querer manter o placar atual
        clear_score = input("\nDeseja limpar o placar também? (s/N): ")
        if clear_score.lower() == 's':
            match.score_a = None
            match.score_b = None
            print("   Placar limpo (null)")
        else:
            print(f"   Placar mantido: {match.score_a} x {match.score_b}")
        
        match.updated_at = datetime.utcnow()
        
        # 5. Zerar pontos de todas as previsões
        points_reset = 0
        for pred in predictions:
            if pred.points_earned > 0:
                points_reset += 1
            pred.points_earned = 0
            pred.points_winner = 0
            pred.points_score_a = 0
            pred.points_score_b = 0
            pred.points_exact = 0
        
        print(f"\n✅ Pontos zerados em {points_reset} previsões")
        
        # 6. Commit das alterações do jogo e previsões
        db.commit()
        print("   Alterações salvas no banco de dados")
        
        # 7. Recalcular ranking da rodada (se aplicável)
        if match.round_number:
            print(f"\n🔄 Recalculando ranking da rodada {match.round_number}...")
            count = calculate_round_ranking_internal(match.round_number, db)
            print(f"   ✅ Ranking da rodada recalculado ({count} usuários)")
        
        # 8. Recalcular ranking geral
        print(f"\n🔄 Recalculando ranking geral...")
        count = calculate_general_ranking_internal(db)
        print(f"   ✅ Ranking geral recalculado ({count} usuários)")
        
        db.commit()
        
        print(f"\n🎉 Jogo ID {match_id} desfinalizado com sucesso!")
        print(f"   Status atual: {match.status.value}")
        print(f"   O ranking foi recalculado e os pontos removidos.")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro ao desfazer finalização: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    from datetime import datetime
    
    print("=" * 60)
    print("DESFAZER FINALIZAÇÃO DE JOGO")
    print("=" * 60)
    print("\nEste script irá:")
    print("  1. Reverter o status do jogo para 'live'")
    print("  2. Zerar os pontos de todas as previsões deste jogo")
    print("  3. Recalcular o ranking da rodada")
    print("  4. Recalcular o ranking geral")
    print()
    
    if len(sys.argv) < 2:
        match_id = input("Digite o ID do jogo que deseja desfinalizar: ")
        try:
            match_id = int(match_id)
        except ValueError:
            print("❌ ID inválido!")
            sys.exit(1)
    else:
        match_id = int(sys.argv[1])
    
    undo_finish_match(match_id)
