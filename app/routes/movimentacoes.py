import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Movimentacao, Produto, Setor, TipoMovimentacao
from app.schemas.movimentacao import MovimentacaoCreate, MovimentacaoResponse

router = APIRouter()

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_TEMPLATES = os.path.join(DIRETORIO_ATUAL, "..", "templates")
templates = Jinja2Templates(directory=DIRETORIO_TEMPLATES)

@router.post("/", response_model=MovimentacaoResponse, status_code=status.HTTP_201_CREATED)
def registrar_movimentacao(mov: MovimentacaoCreate, db: Session = Depends(get_db)):
    produto = db.query(Produto).filter(Produto.id == mov.produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if mov.tipo == TipoMovimentacao.SAIDA:
        if produto.quantidade_estoque < mov.quantidade:
            raise HTTPException(status_code=400, detail=f"Estoque insuficiente. Estoque atual: {produto.quantidade_estoque}")
        if not mov.setor_id:
            raise HTTPException(status_code=400, detail="O setor destino é obrigatório para saídas.")
        produto.quantidade_estoque -= mov.quantidade

    elif mov.tipo == TipoMovimentacao.ENTRADA:
        produto.quantidade_estoque += mov.quantidade
            
    nova_movimentacao = Movimentacao(
        produto_id=mov.produto_id,
        tipo=mov.tipo,
        quantidade=mov.quantidade,
        observacao=mov.observacao,
        nfe=mov.nfe,
        setor_id=mov.setor_id,
        data_movimentacao=mov.data_movimentacao if mov.data_movimentacao else datetime.utcnow()
    )
    
    db.add(nova_movimentacao)
    db.commit()
    db.refresh(nova_movimentacao)
    return nova_movimentacao

@router.get("/html/entrada", response_class=HTMLResponse)
def renderizar_tela_entrada(request: Request, db: Session = Depends(get_db)):
    produtos = db.query(Produto).order_by(Produto.nome).all()
    categorias = list(set([p.categoria for p in produtos if p.categoria]))
    
    return templates.TemplateResponse(request=request, name="movimentacoes/entrada.html", 
                                      context={"request": request, "produtos": produtos, "categorias": categorias})

@router.get("/html/saida", response_class=HTMLResponse)
def renderizar_tela_saida(request: Request, db: Session = Depends(get_db)):
    produtos_com_estoque = db.query(Produto).filter(Produto.quantidade_estoque > 0).order_by(Produto.nome).all()
    categorias = list(set([p.categoria for p in produtos_com_estoque if p.categoria]))
    setores = db.query(Setor).order_by(Setor.nome).all()
    
    return templates.TemplateResponse(request=request, name="movimentacoes/saida.html", 
                                      context={"request": request, "produtos": produtos_com_estoque, "setores": setores, "categorias": categorias})

@router.get("/html/recibo/{movimentacao_id}", response_class=HTMLResponse)
def renderizar_recibo_saida(request: Request, movimentacao_id: int, db: Session = Depends(get_db)):
    mov = db.query(Movimentacao).filter(Movimentacao.id == movimentacao_id).first()
    if not mov or mov.tipo != TipoMovimentacao.SAIDA:
        return HTMLResponse(content="Recibo não encontrado ou não é uma saída.", status_code=404)
    return templates.TemplateResponse(request=request, name="movimentacoes/recibo.html", context={"request": request, "mov": mov})