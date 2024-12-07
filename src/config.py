from starlette.config import Config
from urllib.parse import urljoin
import yaml
from pathlib import Path

from enum import Enum

config = Config(".env")
ROOT_DIR = Path(__file__).parent.parent

## TODO: clean up this config file
ENV = config("ENV", default="dev")
CODESEARCH_DIR = (
    "/home/ubuntu/codesearch-data"
    if ENV == "release"
    else r"C:\Users\jpeng\Documents\projects\codesearch-data"
)
PORT = int(config("PORT", default=3000))

COWBOY_JWT_SECRET = config("DISPATCH_JWT_SECRET", default="")
# JWT settings
COWBOY_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
COWBOY_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=308790000)  # Seconds

OPENAI_API_KEY = config("OPENAI_API_KEY")
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY")

DB_NAME = config("POSTGRES_DB")
DB_USER = config("POSTGRES_USER")
DB_PASS = config("DB_PASS")
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASS}@{config('POSTGRES_REMOTE_IP')}:{config('POSTGRES_PORT')}/{config('POSTGRES_DB')}"

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
WALKTHROUGH_ROOT = Path(CODESEARCH_DIR) / "walkthroughs"
CHUNKS_ROOT = Path(CODESEARCH_DIR) / "chunks"

GITHUB_API_TOKEN = config("GITHUB_API_TOKEN")
REPO_MAX_SIZE_MB = 80

EVAL_ROOT = Path(CODESEARCH_DIR) / "evals"
CLUSTER_ROOT = Path(CODESEARCH_DIR) / "clusters"

ELL_STORAGE = "./logdir"

AWS_REGION = "us-east-2"
ANON_LOGIN = True

class SUPPORTED_LANGS(str, Enum):
    PYTHON = "python"
