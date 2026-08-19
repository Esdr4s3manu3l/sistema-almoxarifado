import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.database.models import Produto, Movimentacao
from app.schemas.produto import ProdutoCreate, ProdutoResponse

router = APIRouter()

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_TEMPLATES = os.path.join(DIRETORIO_ATUAL, "..", "templates")
templates = Jinja2Templates(directory=DIRETORIO_TEMPLATES)

@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar_produto(produto: ProdutoCreate, db: Session = Depends(get_db)):
    novo_produto = Produto(
        nome=produto.nome,
        categoria=produto.categoria,
        descricao=produto.descricao,
        quantidade_estoque=0,
        estoque_minimo=produto.estoque_minimo or 0
    )
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    return novo_produto

@router.get("/", response_model=List[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(Produto).all()

@router.put("/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(produto_id: int, produto_atualizado: ProdutoCreate, db: Session = Depends(get_db)):
    db_produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    db_produto.nome = produto_atualizado.nome
    db_produto.categoria = produto_atualizado.categoria
    db_produto.descricao = produto_atualizado.descricao
    db_produto.estoque_minimo = produto_atualizado.estoque_minimo or 0
    db.commit()
    db.refresh(db_produto)
    return db_produto

@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    db.delete(produto)
    db.commit()
    return {"mensagem": "Produto deletado"}

# ====== ROTAS HTML ======

@router.get("/html/lista", response_class=HTMLResponse)
def renderizar_lista_html(request: Request, db: Session = Depends(get_db)):
    produtos = db.query(Produto).all()
    return templates.TemplateResponse(request=request, name="produtos/lista.html", context={"request": request, "produtos": produtos})

@router.get("/html/cadastro", response_class=HTMLResponse)
def renderizar_cadastro_html(request: Request):
    return templates.TemplateResponse(request=request, name="produtos/cadastro.html", context={"request": request})

@router.get("/html/editar/{produto_id}", response_class=HTMLResponse)
def renderizar_editar_html(request: Request, produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        return HTMLResponse(content="<h1>Produto não encontrado</h1>", status_code=404)
    return templates.TemplateResponse(request=request, name="produtos/editar.html", context={"request": request, "produto": produto})

@router.get("/html/extrato/{produto_id}", response_class=HTMLResponse)
def renderizar_extrato_html(request: Request, produto_id: int, db: Session = Depends(get_db)):
    """ Rota para visualizar o histórico de um produto específico """
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        return HTMLResponse(content="<h1>Produto não encontrado</h1>", status_code=404)
        
    # Busca todas as movimentações ordenadas da mais recente para a mais antiga
    movimentacoes = db.query(Movimentacao).filter(Movimentacao.produto_id == produto_id)\
                      .order_by(Movimentacao.data_movimentacao.desc()).all()
                      
    return templates.TemplateResponse(
        request=request, 
        name="produtos/extrato.html", 
        context={"request": request, "produto": produto, "movimentacoes": movimentacoes}
    )