from setuptools import setup, find_packages

setup(
    name="bolao-copa-2026",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.109.0",
        "uvicorn[standard]==0.27.0",
        "sqlalchemy==2.0.25",
        "alembic==1.13.1",
        "pydantic[email]==2.5.3",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-multipart==0.0.6",
        "aiofiles==23.2.1",
        "jinja2==3.1.3",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "aiohttp==3.9.1",
        "apscheduler==3.10.4",
        "websockets==12.0",
    ],
    python_requires=">=3.8",
)
