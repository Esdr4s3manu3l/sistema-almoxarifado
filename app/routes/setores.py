import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database.connection import get_db
from app.database.models import Setor, Movimentacao

router = APIRouter()

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_TEMPLATES = os.path.join(DIRETORIO_ATUAL, "..", "templates")
templates = Jinja2Templates(directory=DIRETORIO_TEMPLATES)

# =========================================================================
# ESQUEMAS DE DADOS (Pydantic)
# Traduzem os pacotes JSON que o app.js envia e recebe de forma instantânea
# =========================================================================
class SetorCreate(BaseModel):
    nome: str
    secretaria: Optional[str] = None

class SetorResponse(BaseModel):
    id: int
    nome: str
    secretaria: Optional[str] = None
    
    class Config:
        from_attributes = True

# =========================================================================
# ROTAS DA API (JSON) - Comunicação invisível de alta velocidade
# =========================================================================

@router.get("/", response_model=List[SetorResponse])
def listar_setores(db: Session = Depends(get_db)):
    """Retorna a lista completa de setores em JSON para o front-end."""
    setores = db.query(Setor).order_by(Setor.nome).all()
    return setores

@router.post("/", response_model=SetorResponse, status_code=status.HTTP_201_CREATED)
def criar_setor(setor: SetorCreate, db: Session = Depends(get_db)):
    """Recebe o JSON do app.js e cadastra um novo setor no banco."""
    novo_setor = Setor(nome=setor.nome, secretaria=setor.secretaria)
    db.add(novo_setor)
    db.commit()
    db.refresh(novo_setor)
    return novo_setor

@router.put("/{setor_id}", response_model=SetorResponse)
def atualizar_setor(setor_id: int, setor: SetorCreate, db: Session = Depends(get_db)):
    """Recebe o JSON do app.js e atualiza o setor."""
    setor_db = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor_db:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    
    setor_db.nome = setor.nome
    setor_db.secretaria = setor.secretaria
    db.commit()
    db.refresh(setor_db)
    return setor_db

@router.delete("/{setor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_setor(setor_id: int, db: Session = Depends(get_db)):
    """Deleta o setor se não houver histórico atrelado a ele."""
    setor_db = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor_db:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
        
    movimentacao_existente = db.query(Movimentacao).filter(Movimentacao.setor_id == setor_id).first()
    if movimentacao_existente:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível excluir este setor pois ele já possui histórico de materiais requisitados."
        )
        
    db.delete(setor_db)
    db.commit()
    return {"mensagem": "Setor removido com sucesso"}

# =========================================================================
# ROTAS DE TELA (HTML) - Renderização visual
# =========================================================================

@router.get("/html/cadastro", response_class=HTMLResponse)
def renderizar_tela_cadastro_setor(request: Request, db: Session = Depends(get_db)):
    """Desenha a tela do navegador com os modais e tabelas."""
    setores = db.query(Setor).order_by(Setor.nome).all()
    return templates.TemplateResponse(
        request=request, 
        name="setores/cadastro.html", 
        context={"request": request, "setores": setores}
    )