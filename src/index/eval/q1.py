from .base import QuestionFileOnly

SINGLE_FILE_EXPLICIT = [
    QuestionFileOnly(
        question="How does a Repo get created in view.py?",
        files=["src/views/repo.py"],
    ),
    QuestionFileOnly(
        question="What is the algorithm used in cluster_graph() to generate the clusters?",
        files=["rtfs/cluster/cluster_graph.py"],
    ),
    QuestionFileOnly(
        question="What AST parsing library is used to construct the initial ScopeGraph in build_scopes.py?",
        files=["rtfs/build_scopes.py"],
    ),
    QuestionFileOnly(
        question="How does the contain line method of the TextRange class check for inclusion in utils.py?",
        files=["rtfs/utils.py"],
    ),
    QuestionFileOnly(
        question="What does the DictMixin class do in graph.py?",
        files=["rtfs/graph.py"]
    )
]

SINGLE_FILE_IMPLICIT = [
    QuestionFileOnly(
        question="How does a Repo object get created during the server request handler?",
        files=["src/views/repo.py"],
    ),
    QuestionFileOnly(
        question="What is the deterministic graph specific algorithm used to generate the initial set of clusters?",
        files=["rtfs/cluster/cluster_graph.py"],
    ),
    QuestionFileOnly(
        question="Which parsing library is used to extract the scopes from the source file?",
        files=["rtfs/build_scopes.py"],
    ),
    QuestionFileOnly(
        question="Which method does the TextRange class use to check for inclusion within its range?",
        files=["rtfs/utils.py"],
    ),
    QuestionFileOnly(
        question="What method do the graph nodes inherit use to serialize into JSON?",
        files=["rtfs/graph.py"]
    )
]



