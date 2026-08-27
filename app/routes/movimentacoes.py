import os
import io
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile
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


@router.post("/importar-historico")
async def importar_historico_saidas(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Lê uma planilha e importa o histórico antigo de saídas."""
    conteudo = await arquivo.read()
    
    try:
        if arquivo.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(conteudo), sep=';') # Suporte a CSV padrão brasileiro
        else:
            df = pd.read_excel(io.BytesIO(conteudo))
            
        df = df.fillna("")
        registros_adicionados = 0
        erros = []

        for index, row in df.iterrows():
            nome_produto = str(row.get("Produto", "")).strip()
            qtd_str = row.get("Quantidade", 0)
            nome_setor = str(row.get("Setor", "")).strip()
            data_str = str(row.get("Data", "")).strip()
            
            # Pula a linha se faltar o básico
            if not nome_produto or not qtd_str:
                continue
            
            try:
                qtd = int(qtd_str)
            except ValueError:
                continue # Pula se a quantidade não for um número
                
            # 1. Busca o Produto no banco
            produto = db.query(Produto).filter(Produto.nome == nome_produto).first()
            if not produto:
                erros.append(f"Linha {index+2}: Produto '{nome_produto}' não cadastrado no catálogo.")
                continue
                
            # 2. Busca ou Cria o Setor automaticamente
            setor_id = None
            if nome_setor:
                setor = db.query(Setor).filter(Setor.nome == nome_setor).first()
                if not setor:
                    setor = Setor(nome=nome_setor)
                    db.add(setor)
                    db.commit()
                    db.refresh(setor)
                setor_id = setor.id

            # 3. Formata a Data do Excel
            data_movimentacao = datetime.utcnow()
            if data_str:
                try:
                    data_movimentacao = pd.to_datetime(data_str, dayfirst=True).to_pydatetime()
                except:
                    pass 
                    
            # 4. Registra a Saída usando o Enum
            nova_saida = Movimentacao(
                tipo=TipoMovimentacao.SAIDA,
                produto_id=produto.id,
                quantidade=qtd,
                setor_id=setor_id,
                nfe=str(row.get("NFE", "")).strip(),
                observacao=str(row.get("Observacao", "")).strip(),
                data_movimentacao=data_movimentacao
            )
            
            # 5. Abate do estoque atual
            produto.quantidade_estoque -= qtd
            
            db.add(nova_saida)
            registros_adicionados += 1

        db.commit()
        
        mensagem = f"{registros_adicionados} movimentações importadas com sucesso!"
        if erros:
            mensagem += f" Aviso: {len(erros)} itens não foram importados pois o produto não existe no sistema."
            
        return {"mensagem": mensagem, "erros": erros}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao processar planilha: {str(e)}")

# =========================================================================
# ROTAS HTML
# =========================================================================

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