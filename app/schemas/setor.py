from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SetorCreate(BaseModel):
    nome: str
    secretaria: Optional[str] = None

class SetorResponse(BaseModel):
    id: int
    nome: str
    secretaria: Optional[str] = None
    criado_em: datetime

    class Config:
        from_attributes = True