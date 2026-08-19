import os
import webbrowser
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import extract

# Carrega as variáveis do arquivo .env antes de iniciar o banco
load_dotenv()

from app.database.connection import Base, engine, get_db
from app.database.models import Produto, Movimentacao, TipoMovimentacao
from app.routes import produtos, movimentacoes, setores, relatorios

app = FastAPI(title="Sistema de Almoxarifado")

# Configuração da pasta de arquivos estáticos (CSS, JS, Imagens)
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_STATIC = os.path.join(DIRETORIO_ATUAL, "static")
app.mount("/static", StaticFiles(directory=DIRETORIO_STATIC), name="static")

# Incluindo as rotas do sistema
app.include_router(produtos.router, prefix="/produtos", tags=["Produtos"])
app.include_router(movimentacoes.router, prefix="/movimentacoes", tags=["Movimentações"])
app.include_router(setores.router, prefix="/setores", tags=["Setores"])
app.include_router(relatorios.router, prefix="/relatorios", tags=["Relatórios"])

@app.get("/", response_class=HTMLResponse)
def root_dashboard(request: Request, db: Session = Depends(get_db)):
    """ Carrega a tela de Dashboard com os indicadores em tempo real. """
    templates = Jinja2Templates(directory=os.path.join(DIRETORIO_ATUAL, "templates"))
    
    # Cálculos dinâmicos em tempo real do banco de dados
    total_produtos = db.query(Produto).count()
    produtos_zerados = db.query(Produto).filter(Produto.quantidade_estoque == 0).count()
    
    mes_atual = datetime.utcnow().month
    ano_atual = datetime.utcnow().year
    
    saidas_mes = db.query(Movimentacao).filter(
        Movimentacao.tipo == TipoMovimentacao.SAIDA,
        extract('month', Movimentacao.data_movimentacao) == mes_atual,
        extract('year', Movimentacao.data_movimentacao) == ano_atual
    ).count()

    entradas_mes = db.query(Movimentacao).filter(
        Movimentacao.tipo == TipoMovimentacao.ENTRADA,
        extract('month', Movimentacao.data_movimentacao) == mes_atual,
        extract('year', Movimentacao.data_movimentacao) == ano_atual
    ).count()

    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html",
        context={
            "request": request,
            "total_produtos": total_produtos,
            "produtos_zerados": produtos_zerados,
            "saidas_mes": saidas_mes,
            "entradas_mes": entradas_mes
        }
    )

@app.on_event("startup")
def iniciar_sistema():
    # Cria o banco e as tabelas automaticamente se não existirem
    Base.metadata.create_all(bind=engine)
    webbrowser.open("http://localhost:8000")