import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Carrega as variáveis do arquivo .env da raiz do projeto
load_dotenv()

# Caminho padrão para o SQLite interno caso o .env não especifique outro
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DB_SQLITE = os.path.join(DIRETORIO_BASE, "..", "..", "almoxarifado.db")
DEFAULT_SQLITE_URL = f"sqlite:///{CAMINHO_DB_SQLITE}"

# Pega a URL do .env ou usa o SQLite por padrão
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# Argumentos específicos para o SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()