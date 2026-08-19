import os
import io
import pandas as pd
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract

from app.database.connection import get_db
from app.database.models import Movimentacao, Setor, TipoMovimentacao

router = APIRouter()

DIRETORIO_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
templates = Jinja2Templates(directory=DIRETORIO_TEMPLATES)

@router.get("/html/setores", response_class=HTMLResponse)
def relatorio_setores(request: Request, setor_id: int | None = None, mes: str = None, db: Session = Depends(get_db)):
    setores = db.query(Setor).order_by(Setor.nome).all()
    query = db.query(Movimentacao).filter(Movimentacao.tipo == TipoMovimentacao.SAIDA)
    
    # Se o setor_id vier vazio ou 0, ignoramos o filtro
    if setor_id:
        query = query.filter(Movimentacao.setor_id == setor_id)
    if mes:
        try:
            ano, m = mes.split('-')
            query = query.filter(
                extract('year', Movimentacao.data_movimentacao) == int(ano),
                extract('month', Movimentacao.data_movimentacao) == int(m)
            )
        except: pass
            
    movimentacoes = query.order_by(Movimentacao.data_movimentacao.desc()).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="relatorios/setores.html", 
        context={
            "request": request, 
            "setores": setores, 
            "movimentacoes": movimentacoes,
            "setor_selecionado": setor_id,
            "mes_selecionado": mes
        }
    )

@router.get("/exportar/excel")
def exportar_relatorio_excel(setor_id: int | None = None, mes: str = None, db: Session = Depends(get_db)):
    query = db.query(Movimentacao).filter(Movimentacao.tipo == TipoMovimentacao.SAIDA)
    
    if setor_id:
        query = query.filter(Movimentacao.setor_id == setor_id)
    if mes:
        try:
            ano, m = mes.split('-')
            query = query.filter(
                extract('year', Movimentacao.data_movimentacao) == int(ano),
                extract('month', Movimentacao.data_movimentacao) == int(m)
            )
        except: pass
    
    movimentacoes = query.all()
    
    data = [{
        "Data": m.data_movimentacao.strftime('%d/%m/%Y'),
        "Setor": m.setor.nome if m.setor else "-",
        "Produto": m.produto.nome,
        "Quantidade": m.quantidade,
        "Observação": m.observacao or ""
    } for m in movimentacoes]
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="Relatório")
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=relatorio_consumo.xlsx"}
    )