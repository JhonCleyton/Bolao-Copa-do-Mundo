from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.routers import auth, users, matches, predictions, rankings, admin, notifications, groq, messages, pvp, live_data
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="Bolão Copa 2026",
    description="Sistema de bolão para a Copa do Mundo 2026",
    version="1.0.0",
    lifespan=lifespan
)

# Templates
templates = Jinja2Templates(directory="static/templates")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(matches.router, prefix="/api/matches", tags=["Matches"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(rankings.router, prefix="/api/rankings", tags=["Rankings"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(groq.router, prefix="/api/groq", tags=["AI Assistant"])
app.include_router(pvp.router, prefix="/api/pvp", tags=["PVP Bets"])
app.include_router(live_data.router, prefix="/api/live", tags=["Live Data"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/cadastro", response_class=HTMLResponse)
async def cadastro(request: Request):
    return templates.TemplateResponse("cadastro.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/palpites", response_class=HTMLResponse)
async def palpites(request: Request):
    return templates.TemplateResponse("palpites.html", {"request": request})


@app.get("/ranking", response_class=HTMLResponse)
async def ranking(request: Request):
    return templates.TemplateResponse("ranking.html", {"request": request})


@app.get("/perfil", response_class=HTMLResponse)
async def perfil(request: Request):
    return templates.TemplateResponse("perfil.html", {"request": request})


@app.get("/grupos", response_class=HTMLResponse)
async def grupos(request: Request):
    return templates.TemplateResponse("grupos.html", {"request": request})


@app.get("/transparencia", response_class=HTMLResponse)
async def transparencia(request: Request):
    return templates.TemplateResponse("transparencia.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/admin/whatsapp", response_class=HTMLResponse)
async def admin_whatsapp(request: Request):
    return templates.TemplateResponse("whatsapp.html", {"request": request})


@app.get("/admin/cobrancas", response_class=HTMLResponse)
async def admin_cobrancas(request: Request):
    return templates.TemplateResponse("cobrancas.html", {"request": request})


@app.get("/admin/mensagens", response_class=HTMLResponse)
async def admin_mensagens(request: Request):
    return templates.TemplateResponse("mensagens.html", {"request": request})


@app.get("/recuperar-senha", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@app.get("/resetar-senha", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = None):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})


@app.get("/como-funciona", response_class=HTMLResponse)
async def como_funciona(request: Request):
    return templates.TemplateResponse("como_funciona.html", {"request": request})


@app.get("/pvp", response_class=HTMLResponse)
async def pvp_page(request: Request):
    return templates.TemplateResponse("pvp.html", {"request": request})


@app.get("/partidas", response_class=HTMLResponse)
async def partidas_page(request: Request):
    return templates.TemplateResponse("partidas.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5555, reload=True)
