#!/usr/bin/env python3
"""
Script para criar usuário administrador
Execute: python create_admin.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, UserStatus
from app.auth import get_password_hash

def create_admin():
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("  CRIAR USUÁRIO ADMINISTRADOR - BOLÃO COPA 2026")
        print("=" * 60)
        print()
        
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        if existing_admin:
            print(f"⚠️  Já existe um admin: {existing_admin.email}")
            response = input("Deseja criar outro admin? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelado.")
                return
        
        # Get user input
        full_name = input("Nome completo: ").strip()
        email = input("Email: ").strip()
        phone = input("Telefone (WhatsApp): ").strip()
        password = input("Senha: ").strip()
        
        if not all([full_name, email, phone, password]):
            print("❌ Todos os campos são obrigatórios!")
            return
        
        if len(password) < 6:
            print("❌ A senha deve ter pelo menos 6 caracteres!")
            return
        
        # Check if email exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"❌ Email {email} já está cadastrado!")
            response = input("Deseja tornar este usuário admin? (yes/no): ")
            if response.lower() == 'yes':
                existing.is_admin = True
                existing.status = UserStatus.ACTIVE
                existing.email_verified = True
                existing.phone_verified = True
                db.commit()
                print(f"✅ {existing.full_name} agora é admin!")
            return
        
        # Create admin user
        admin = User(
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            phone=phone,
            status=UserStatus.ACTIVE,
            email_verified=True,
            phone_verified=True,
            registration_paid=True,
            is_admin=True
        )
        
        db.add(admin)
        db.commit()
        
        print()
        print("=" * 60)
        print("✅ ADMIN CRIADO COM SUCESSO!")
        print("=" * 60)
        print(f"Nome: {admin.full_name}")
        print(f"Email: {admin.email}")
        print(f"Senha: {'*' * len(password)}")
        print()
        print("Acesse: http://localhost:8000/login")
        print()
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
