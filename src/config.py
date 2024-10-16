from starlette.config import Config
from urllib.parse import urljoin
import os
from pathlib import Path

from enum import Enum

config = Config(".env")

ENV = config("ENV", default="dev")
CODESEARCH_DIR = (
    "/home/ubuntu"
    if ENV == "release"
    else r"C:\Users\jpeng\Documents\projects\codesearch-data"
)
PORT = int(config("PORT", default=3000))

# JWT settings
COWBOY_JWT_SECRET = config("DISPATCH_JWT_SECRET", default="")
COWBOY_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
COWBOY_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=308790000)  # Seconds

COWBOY_OPENAI_API_KEY = config("OPENAI_API_KEY")

DB_PASS = config("DB_PASS")
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://postgres:{DB_PASS}@127.0.0.1:5432/codesearch"
    if ENV == "release"
    else f"postgresql://postgres:{DB_PASS}@{config('DB_URL')}:5432/codesearch"
)
SQLALCHEMY_ENGINE_POOL_SIZE = 50

ALEMBIC_INI_PATH = "."
ALEMBIC_CORE_REVISION_PATH = "alembic"

# LLM settings and test gen settings
AUGMENT_ROUNDS = 4 if ENV == "release" else 1
LLM_RETRIES = 3
AUTO_GEN_SIZE = 7
LOG_DIR = "log"

REPOS_ROOT = Path(CODESEARCH_DIR) / "repo"
INDEX_ROOT = Path(CODESEARCH_DIR) / "index"
GRAPH_ROOT = Path(CODESEARCH_DIR) / "graphs"
SUMMARIES_ROOT = Path(CODESEARCH_DIR) / "summaries"
GITHUB_API_TOKEN = config("GITHUB_API_TOKEN")
REPO_MAX_SIZE_MB = 80

SUPPORTED_LANGS = [
    "python"
]

AWS_REGION = "us-east-2"
ANON_LOGIN = True


class Language(str, Enum):
    """
    Currently supported languages
    """

    python = "python"
