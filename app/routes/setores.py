import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_db
from app.database.models import Setor
from app.schemas.setor import SetorCreate, SetorResponse

router = APIRouter()

DIRETORIO_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
templates = Jinja2Templates(directory=DIRETORIO_TEMPLATES)

@router.post("/", response_model=SetorResponse, status_code=status.HTTP_201_CREATED)
def criar_setor(setor: SetorCreate, db: Session = Depends(get_db)):
    novo_setor = Setor(nome=setor.nome, secretaria=setor.secretaria)
    db.add(novo_setor)
    db.commit()
    db.refresh(novo_setor)
    return novo_setor

@router.put("/{setor_id}", response_model=SetorResponse)
def atualizar_setor(setor_id: int, setor_atualizado: SetorCreate, db: Session = Depends(get_db)):
    db_setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not db_setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    
    db_setor.nome = setor_atualizado.nome
    db_setor.secretaria = setor_atualizado.secretaria
    db.commit()
    db.refresh(db_setor)
    return db_setor

@router.delete("/{setor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_setor(setor_id: int, db: Session = Depends(get_db)):
    setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    
    try:
        db.delete(setor)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Não é possível excluir este setor pois ele já recebeu materiais no passado.")
    
    return {"mensagem": "Setor deletado"}

@router.get("/html/cadastro", response_class=HTMLResponse)
def renderizar_cadastro_setor(request: Request, db: Session = Depends(get_db)):
    setores = db.query(Setor).order_by(Setor.nome).all()
    return templates.TemplateResponse(request=request, name="setores/cadastro.html", context={"request": request, "setores": setores})

@router.get("/html/editar/{setor_id}", response_class=HTMLResponse)
def renderizar_editar_setor(request: Request, setor_id: int, db: Session = Depends(get_db)):
    setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor:
        return HTMLResponse(content="<h1>Setor não encontrado</h1>", status_code=404)
    return templates.TemplateResponse(request=request, name="setores/editar.html", context={"request": request, "setor": setor})