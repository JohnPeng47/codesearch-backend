from src.chunk.chunkers import PythonChunker
from src.chunk.settings import IndexSettings


chunker = PythonChunker(r"..\codesearch-data\repo\aorwall_moatless-tools")
chunks = chunker.chunk()

