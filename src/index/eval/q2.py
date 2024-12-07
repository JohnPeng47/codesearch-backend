from .base import QuestionFileOnly

MULTI_FILE_EXPLICIT = [
    QuestionFileOnly(
        question="What exact steps does split_cluster() use in the LLMModel to break down a cluster, and what specific Pydantic models are used to structure the output?",
        files=["rtfs/cluster/lmp/split_cluster.py", "llm/types/clustering.py", "rtfs/cluster/graph.py"],
    ),
    QuestionFileOnly(
        question="What method does the ChunkGraph class use to concatenate chunk contents, and how does ClusterGraph utilize these chunks to build cluster edges?",
        files=["rtfs/chunk_resolution/chunk_graph.py", "rtfs/cluster/cluster_graph.py", "rtfs/chunk_resolution/graph.py"],
    ),
    QuestionFileOnly(
        question="What specific edge types does ClusterGraph use to track relationships between chunks and clusters, and how are these edge types defined in the base graph module?",
        files=["rtfs/cluster/cluster_graph.py", "rtfs/cluster/graph.py", "rtfs/graph.py"],
    ),
    QuestionFileOnly(
        question="What data structure does cluster_wiki() use to generate documentation, and how does ClusterSummary store this information in the cluster nodes?",
        files=["src/chat/lmp/walkthrough.py", "rtfs/cluster/graph.py", "rtfs/cluster/cluster_graph.py"],
    ),
    QuestionFileOnly(
        question="How does ChunkNode implement the range property for TextRange, and what specific metadata does CodeChunk use to support this functionality?",
        files=["rtfs/chunk_resolution/graph.py", "src/models.py", "rtfs/graph.py"],
    ),
]

MULTI_FILE_IMPLICIT = [
    QuestionFileOnly(
        question="How does the system handle breaking down large clusters into smaller, more manageable pieces?",
        files=["rtfs/cluster/lmp/split_cluster.py", "llm/types/clustering.py", "rtfs/cluster/graph.py"],
    ),
    QuestionFileOnly(
        question="How are chunk contents organized and used to establish relationships between clusters?",
        files=["rtfs/chunk_resolution/chunk_graph.py", "rtfs/cluster/cluster_graph.py", "rtfs/chunk_resolution/graph.py"],
    ),
    QuestionFileOnly(
        question="What different types of connections exist between code chunks and their clusters?",
        files=["rtfs/cluster/cluster_graph.py", "rtfs/cluster/graph.py", "rtfs/graph.py"],
    ),
    QuestionFileOnly(
        question="How is documentation generated and stored for code clusters?",
        files=["src/chat/lmp/walkthrough.py", "rtfs/cluster/graph.py", "rtfs/cluster/cluster_graph.py"],
    ),
    QuestionFileOnly(
        question="How does the system track the location and scope of code chunks?",
        files=["rtfs/chunk_resolution/graph.py", "src/models.py", "rtfs/graph.py"],
    ),
]