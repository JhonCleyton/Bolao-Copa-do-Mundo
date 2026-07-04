#!/usr/bin/env python3
"""
Script para diagnosticar e corrigir horários e status das partidas
"""

import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Match, MatchStatus
from app.utils.timezone import get_brasilia_now

def diagnostic():
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        print(f"Horário atual (Brasília): {now}")
        print("=" * 60)
        
        matches = db.query(Match).order_by(Match.id).all()
        
        print("\n=== TODAS AS PARTIDAS ===")
        for m in matches[:10]:  # Primeiras 10
            status_icon = "🔴" if m.status == MatchStatus.LIVE else "⚪" if m.status == MatchStatus.SCHEDULED else "✅"
            print(f"{status_icon} ID {m.id}: {m.team_a} x {m.team_b}")
            print(f"   match_date: {m.match_date}")
            print(f"   brasilia_time: {m.brasilia_time}")
            print(f"   status: {m.status.value}")
            print()
        
        # Verificar jogos que estão como LIVE mas ainda não deveriam estar
        print("=" * 60)
        print("\n=== JOGOS COM STATUS LIVE ===")
        live_matches = db.query(Match).filter(Match.status == MatchStatus.LIVE).all()
        if not live_matches:
            print("Nenhum jogo com status LIVE")
        else:
            for m in live_matches:
                should_be_live = now >= m.match_date
                print(f"ID {m.id}: {m.team_a} x {m.team_b}")
                print(f"  match_date: {m.match_date}")
                print(f"  Deveria estar ao vivo? {'SIM' if should_be_live else 'NÃO - ERRO!'}")
                print()
        
        # Jogo específico ID 3
        print("=" * 60)
        print("\n=== JOGO ID 3 (ESPECÍFICO) ===")
        match3 = db.query(Match).filter(Match.id == 3).first()
        if match3:
            print(f"ID: {match3.id}")
            print(f"Times: {match3.team_a} x {match3.team_b}")
            print(f"match_date: {match3.match_date}")
            print(f"brasilia_time: {match3.brasilia_time}")
            print(f"status: {match3.status.value}")
            print(f"Deveria estar ao vivo agora? {'SIM' if now >= match3.match_date else 'NÃO'}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnostic()
