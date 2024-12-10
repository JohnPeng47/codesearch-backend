# What am I looking at?
https://cowboy.rocks/codesearch

The original idea behind this was: can AI help solve code understanding?
I approached this problem by:
1. Identifying clusters of code that represented distinct functional components in the code (ie. API Request Error Handling)
2. Generate summaries of these
3. Present a UI that allows you to browse the source code using the summaries as guidance
The goal here was not to replace looking at source code with summaries, but to present the user with summaries that represents a 10,000 ft. view of the code, quickly orienting them in the unfamiliar territory so they can better navigate it on their own

# How it works
At its core, Codesearch tries to discover groups of source code that works together to implement a system function; so essentially a "clustering" problem in ML parlance.
At a high level, it accomplishes this by first running a generic graph-based clustering algorithm over a dependency graph (references -> definitions) of code chunks. It then uses LLMs to clean-up the results of the previous clustering step by reassigning chunks to clusters. Finally, a summary is generated for each cluster.

A detailed description is provided below. 
1. Chunk using code aware chunking strategy (lifted from https://github.com/aorwall/moatless-tools)
- "Code aware" means for example chunking on function boundaries to keep variable scopes intact during retrieval

def func(a: T, b: S):
------- CHUNK BOUNDARY ------
    dostuff(a, b):

(Example of non-code aware chunking) -> awareness of a,b as the function parameters is lost when the boundary is arbitrarily selected by a non-code aware chunking scheme

[Implementation] 
- src/chunk/chunkers/python.py -> Python chunker, wraps moatless
- moatless/index/epic_split.py -> actual chunking logic
- moatless/codeblocks/parser/python.py -> python parser

2. Generate dependency graph for references -> definitions (inspired by https://github.com/BloopAI/bloop.git)
- My dependency resolution algorithm works by assigning referenced/defined relationships to variables at the chunk level. So for each chunk, its outgoing edges are references to externally defined (in another chunk) symbols and the incoming edges when another chunk references its definitions.

A problem we encounter is disambiguating between references to variables that share common names within a source file.

f1.py

# scope 1, global scope
------- CHUNK 1 ---------
from f2 import a,b

------- CHUNK 2 ---------
def f(x, y): # scope 2, func scope
  ...
  x = a()
  y = b + 1 #
  global_var = 1


f2.py
------- CHUNK 1 ---------
def a(): # scope 2
    ...
------- CHUNK 2 ---------
b = x


The solution that I lifted from Bloop's rust code and optimized into python uses a scope graph (DAG) that tracks nested scopes by constructing a edge from child to parent. So starting from the global scope (root node), I iterate through each scope in the file and connecting each child to a path that eventually leads to the parent. When this is done, every reference can be unambiguously resolved by first checking its current scope, then walking up its parents until a scope containing the reference is found.

f1::chunk2 -- (a,b) --> f2::a(chunk1), f2::b(chunk2)

With references/definitions tied to scope, I can now construct edges from references to definitions across different chunks (chunk -> chunk graph)
    
[Implementation]
- rtfs/build_scopes.py -> goes over the code and extracts nodes using TS queries
- rtfs/scope_resolution/scope_graph.py -> constructing the scopegraph
- rtfs/repo_resolution/graph.py -> file -> file graph that maps import/export
- rtfs/chunk_resolution/graph.py -> chunk -> chunk graph constructed using the import/export relationships above

3. Cluster chunks together using a generic graph clustering/community detection algorithm (https://github.com/mapequation/infomap.git)
- Run a graph clustering algorithm to detect clusters in the previous chunk -> chunk graph
- The graph clustering objective here is roughly like "find a group of nodes that maximizes the ratio of in-group connections/out-group edges"
- (Works surprisingly well!)

[Implementation]
- rtfs/cluster/infomap.py -> wrapper around infoMap package

4. Reassign chunks with LLM
- Reason why this step exists is because (as you can imagine) steps 1-3 can end up with badly clustered chunks. 
- Reason why steps 1-3 exists is because clustering with LLM naively doesnt work very well (long list of reasons, mostly having to do with context length)

[Implementation]
- rtfs/cluster/cluster_graph.py -> main cluster cleanup routine
- rtfs/cluster/lmp/graph_ops.py -> a "pseudo-DSL" for LLM-based graph modifications

6. Generate summaries for chunks
- Generate summaries for each cluster

[Implementation]
- rtfs/cluster/cluster_graph.py -> main cluster cleanup routine

7. (ROADMAP) Code search [some thoughts for implementation]
- When thinking about NL queries against a repo-wide codesearching system, I find the following categorizations helpful:
1. queries relating to a single file
2. queries relating to multiple files
3. queries with references to specific symbols in the code (made by a user who is already familiar with the codebase)
4. queries without references to specific symbols, using more generally descriptive language (made by users who are unfamiliar with the codebase)

In comparing queries over a index built with summarized clusters vs. an index of chunks of raw code, I think there is a benefit in (2,3) from above. The reason for this is because cosine similarity is a vector by vector comparison, which means that comparison of code chunks are isolated from their wider context in interacting with the rest of the codebase. Also, for new users of the codebase who might not be familiar with the symbol names, queries that ask more general questions should be anticipated. Summaries in natural language might be a better match against these queries than raw code.

# Evaluations
It should be noted while some evaluation attemps have been made to quantify the quality of the clusters, most of the setup here is "one-shotted" and methodologies generally not based on empirical observation. It's on the roadmap :)

# Honorable Mentions
The original idea was inspired for Microsoft's https://github.com/microsoft/graphrag; figured that code dependency edges probably should convey way more information than generic entity relation graphs
