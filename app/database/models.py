from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database.connection import Base

class TipoMovimentacao(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"

class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=True)
    quantidade_estoque: Mapped[int] = mapped_column(Integer, default=0)
    estoque_minimo: Mapped[int] = mapped_column(Integer, default=0) # <--- NOVO CAMPO
    
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    movimentacoes = relationship("Movimentacao", back_populates="produto", cascade="all, delete-orphan")

class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False)
    tipo: Mapped[TipoMovimentacao] = mapped_column(Enum(TipoMovimentacao), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    observacao: Mapped[str] = mapped_column(String(255), nullable=True)
    data_movimentacao: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    nfe: Mapped[str] = mapped_column(String(50), nullable=True)
    setor_id: Mapped[int] = mapped_column(ForeignKey("setores.id"), nullable=True)

    produto = relationship("Produto", back_populates="movimentacoes")
    setor = relationship("Setor")

class Setor(Base):
    __tablename__ = "setores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    secretaria: Mapped[str] = mapped_column(String(100), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)