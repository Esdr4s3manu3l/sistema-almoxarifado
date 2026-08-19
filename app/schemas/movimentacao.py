from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database.models import TipoMovimentacao

class MovimentacaoCreate(BaseModel):
    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    observacao: Optional[str] = None
    
    # Específicos para almoxarifado público
    nfe: Optional[str] = None
    preco_unitario_nfe: Optional[float] = None
    setor_id: Optional[int] = None
    data_movimentacao: Optional[datetime] = None  # <-- NOVO CAMPO AQUI

class MovimentacaoResponse(BaseModel):
    id: int
    produto_id: int
    tipo: TipoMovimentacao
    quantidade: int
    observacao: Optional[str] = None
    data_movimentacao: datetime
    nfe: Optional[str] = None
    preco_unitario_nfe: Optional[float] = None
    setor_id: Optional[int] = None

    class Config:
        from_attributes = True

