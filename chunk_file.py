import argparse
import json
from pathlib import Path

from src.chunk.chunkers import PythonChunker
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from src.index import Indexer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chunk a repository into code chunks and output to a file."
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument("--output-file", default="chunks.txt", help="Output file for the chunks")

    args = parser.parse_args()
    repo_path = Path(args.directory).resolve()

    chunker = PythonChunker(repo_path)
    chunks = chunker.chunk()
    print(f"Finished chunking with {len(chunks)} chunks")

    with open(args.output_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(f"Chunk ID: {chunk.id}\n")
            f.write(f"Filepath: {chunk.metadata.file_path}\n") 
            f.write(f"Content:\n{chunk.content}\n")
            f.write("-" * 80 + "\n")
    print(f"Chunks have been written to {args.output_file}")
