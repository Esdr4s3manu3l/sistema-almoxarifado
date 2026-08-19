from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProdutoCreate(BaseModel):
    nome: str
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    estoque_minimo: Optional[int] = 0  # <--- NOVO

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    quantidade_estoque: int
    estoque_minimo: int  # <--- NOVO
    criado_em: datetime

    class Config:
        from_attributes = True