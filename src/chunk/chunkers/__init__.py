from .base import Chunker

from .python import PythonChunker
from src.config import SUPPORTED_LANGS

CHUNKERS = {
    SUPPORTED_LANGS.PYTHON : PythonChunker,
}