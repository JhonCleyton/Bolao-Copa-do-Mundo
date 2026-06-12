#!/usr/bin/env python3
"""
Script para popular o banco de dados com todos os jogos da Copa 2026
Execute: python seed_database.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models import Base, Match
from app.seed_data import matches_data

def seed_database():
    """Seed database with all World Cup 2026 matches"""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if matches already exist
        existing_count = db.query(Match).count()
        if existing_count > 0:
            print(f"⚠️  Database already has {existing_count} matches.")
            response = input("Do you want to reset and re-seed? (yes/no): ")
            if response.lower() == 'yes':
                # Delete existing matches
                db.query(Match).delete()
                db.commit()
                print("✅ Existing matches deleted.")
            else:
                print("❌ Seeding cancelled.")
                return
        
        # Add all matches
        print(f"🌱 Seeding {len(matches_data)} matches...")
        
        for match_data in matches_data:
            match = Match(**match_data)
            db.add(match)
        
        db.commit()
        
        # Verify
        count = db.query(Match).count()
        print(f"\n✅ Successfully seeded {count} matches!")
        
        # Show summary by stage
        from sqlalchemy import func
        from app.models import Stage
        
        summary = db.query(
            Match.stage,
            func.count(Match.id).label('count')
        ).group_by(Match.stage).all()
        
        print("\n📊 Summary by Stage:")
        stage_names = {
            'group_stage': 'Fase de Grupos',
            'round_of_32': 'Fase de 32',
            'round_of_16': 'Oitavas de Final',
            'quarter_final': 'Quartas de Final',
            'semi_final': 'Semifinais',
            'third_place': '3º Lugar',
            'final': 'Final'
        }
        
        for stage, count in summary:
            name = stage_names.get(stage.value, stage.value)
            print(f"   {name}: {count} jogos")
        
        # Show summary by round (for group stage)
        rounds = db.query(
            Match.round_number,
            func.count(Match.id).label('count')
        ).filter(Match.stage == Stage.GROUP_STAGE).group_by(Match.round_number).all()
        
        print("\n🔄 Group Stage by Round:")
        for round_num, count in sorted(rounds):
            print(f"   {round_num}ª Rodada: {count} jogos")
        
        print("\n🏆 Copa do Mundo 2026 - Todos os jogos cadastrados!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  BOLÃO COPA 2026 - Database Seeding")
    print("=" * 60)
    print()
    seed_database()
