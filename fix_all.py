#!/usr/bin/env python3
"""
Script completo para corrigir:
1. Horários das partidas (resetar para valores originais do seed_data)
2. Status das partidas (SCHEDULED/LIVE baseado no horário atual)
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Match, MatchStatus
from app.utils.timezone import get_brasilia_now
from app.seed_data import matches_data

def fix_all():
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        print(f"Horário atual (Brasília): {now}")
        print("=" * 60)
        
        # Criar mapa de dados originais
        original_times = {}
        for m in matches_data:
            original_times[m['match_number']] = m['match_date']
        
        # Corrigir horários
        print("\n=== CORRIGINDO HORÁRIOS ===")
        matches = db.query(Match).order_by(Match.id).all()
        fixed_count = 0
        
        for match in matches:
            if match.match_number in original_times:
                original = original_times[match.match_number]
                if match.match_date != original:
                    print(f"ID {match.id} ({match.team_a} x {match.team_b}):")
                    print(f"  {match.match_date} -> {original}")
                    match.match_date = original
                    fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"\n✅ {fixed_count} horário(s) corrigido(s)")
        else:
            print("✅ Todos os horários já estão corretos")
        
        # Corrigir status
        print("\n" + "=" * 60)
        print("=== CORRIGINDO STATUS ===")
        
        # Resetar LIVE incorretos
        future_live = db.query(Match).filter(
            Match.status == MatchStatus.LIVE,
            Match.match_date > now
        ).all()
        
        for match in future_live:
            print(f"Resetando ID {match.id} ({match.team_a} x {match.team_b}) para SCHEDULED")
            match.status = MatchStatus.SCHEDULED
        
        # Atualizar para LIVE os que já começaram
        should_live = db.query(Match).filter(
            Match.status == MatchStatus.SCHEDULED,
            Match.match_date <= now
        ).all()
        
        for match in should_live:
            print(f"Atualizando ID {match.id} ({match.team_a} x {match.team_b}) para LIVE")
            match.status = MatchStatus.LIVE
        
        db.commit()
        
        print(f"\n✅ {len(future_live)} resetado(s) para SCHEDULED")
        print(f"✅ {len(should_live)} atualizado(s) para LIVE")
        
        # Mostrar estado final
        print("\n" + "=" * 60)
        print("=== ESTADO FINAL (primeiras 5) ===")
        for m in db.query(Match).order_by(Match.id).limit(5).all():
            icon = "🔴" if m.status == MatchStatus.LIVE else "⚪"
            print(f"{icon} ID {m.id}: {m.match_date} - {m.team_a} x {m.team_b} ({m.status.value})")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_all()
