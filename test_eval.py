from src.index.eval.q1 import SINGLE_FILE_EXPLICIT, SINGLE_FILE_IMPLICIT
from src.index.eval.q2 import MULTI_FILE_EXPLICIT, MULTI_FILE_IMPLICIT
from src.index.eval.base import EvalFileOnly
from src.index.stores import FaissVectorStore
from src.index.core import IndexStrat

from pathlib import Path

repo = "codesearch-backend"
repo_dir = "C:\\Users\\jpeng\\Documents\\projects\\codesearch-data\\repo\\{dir}"
repo_path = Path(repo_dir.format(dir=repo)).resolve()


store = FaissVectorStore(repo_path, IndexStrat.CLUSTER)
store2 =  FaissVectorStore(repo_path, IndexStrat.VANILLA)

for store in [store, store2]:
    print("Scores for store: ", store.name())
    evaluator = EvalFileOnly(store)

    score = evaluator.evaluate(SINGLE_FILE_EXPLICIT)
    score2 = evaluator.evaluate(SINGLE_FILE_IMPLICIT)
    score3 = evaluator.evaluate(MULTI_FILE_EXPLICIT)
    score4 = evaluator.evaluate(MULTI_FILE_IMPLICIT)

    print("Single File Explicit: ", score)
    print("Single File Implicit: ", score2)
    print("Multi File Explicit: ", score3) 
    print("Multi File Implicit: ", score4)