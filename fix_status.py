#!/usr/bin/env python3
"""
Script para corrigir o status das partidas
- Resetar jogos marcados como LIVE de volta para SCHEDULED se ainda não começaram
"""

import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Match, MatchStatus
from app.utils.timezone import get_brasilia_now

def fix_status():
    db = SessionLocal()
    try:
        now = get_brasilia_now()
        print(f"Horário atual (Brasília): {now}")
        print("=" * 60)
        
        # Encontrar jogos LIVE que ainda não começaram (data futura)
        future_live = db.query(Match).filter(
            Match.status == MatchStatus.LIVE,
            Match.match_date > now
        ).all()
        
        print(f"\nJogos marcados como LIVE mas ainda não começaram: {len(future_live)}")
        
        for match in future_live:
            print(f"  Corrigindo: {match.team_a} x {match.team_b} (ID {match.id})")
            print(f"    match_date: {match.match_date}")
            print(f"    Resetando para SCHEDULED")
            match.status = MatchStatus.SCHEDULED
        
        if future_live:
            db.commit()
            print(f"\n✅ {len(future_live)} jogo(s) corrigido(s)")
        else:
            print("\n✅ Nenhum jogo incorreto encontrado")
        
        # Verificar jogos SCHEDULED que já deveriam estar LIVE
        print("\n" + "=" * 60)
        should_be_live = db.query(Match).filter(
            Match.status == MatchStatus.SCHEDULED,
            Match.match_date <= now
        ).all()
        
        print(f"Jogos SCHEDULED que já deveriam estar LIVE: {len(should_be_live)}")
        for match in should_be_live:
            print(f"  {match.team_a} x {match.team_b} (ID {match.id}) - {match.match_date}")
            match.status = MatchStatus.LIVE
        
        if should_be_live:
            db.commit()
            print(f"\n✅ {len(should_be_live)} jogo(s) atualizado(s) para LIVE")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_status()
