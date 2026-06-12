#!/usr/bin/env python3
"""
Script para corrigir horários das partidas no banco de dados.
Subtrai 3 horas de todos os match_date.
"""

import os
import sys
from datetime import timedelta

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Match
from sqlalchemy import text

def fix_match_times():
    db = SessionLocal()
    try:
        # Mostrar horários antes
        print("=== ANTES ===")
        matches = db.query(Match).order_by(Match.id).all()
        for m in matches[:5]:
            print(f"Partida {m.id}: {m.team_a} x {m.team_b} - {m.match_date}")
        
        # Subtrair 3 horas de todos os match_date
        print("\n=== CORRIGINDO ===")
        for match in matches:
            old_date = match.match_date
            match.match_date = old_date - timedelta(hours=3)
            print(f"Partida {match.id}: {old_date} -> {match.match_date}")
        
        db.commit()
        
        # Verificar depois
        print("\n=== DEPOIS ===")
        matches = db.query(Match).order_by(Match.id).all()
        for m in matches[:5]:
            print(f"Partida {m.id}: {m.team_a} x {m.team_b} - {m.match_date}")
        
        print(f"\n✅ Total de partidas corrigidas: {len(matches)}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_match_times()
