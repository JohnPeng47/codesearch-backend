from src.cluster.types import ClusteredTopic
from src.config import EVAL_ROOT

from datetime import datetime
from typing import List
import os
from pathlib import Path


class EvalReport:
    """
    For styling evaluation reports
    """

    def __init__(self, title: str):
        self._content = f"_____ {title} _____\n\n"

    def add_section(self, name: str):
        self._content += f"###### {name} ######\n"

    def add_line(self, line: str):
        self._content += f"{line}\n"

    def write(self, eval_name: str, subfolder: str = "") :
        """
        Writes the evaluation log to a file with a unique, incremented index
        for a given date timestamp
        """
        if not subfolder:
            raise ValueError("Subfolder must be provided for writing eval logs")
        
        curr_date = datetime.now().strftime('%Y-%m-%d')
        eval_path = EVAL_ROOT / subfolder

        if not eval_path.exists():
            os.makedirs(eval_path, exist_ok=True)
        
        latest_index = max(
            [
                int(self._get_file_index(fn)) for fn 
                in eval_path.glob(f"{curr_date}*")
            ], default=0
        )
        latest_index = str(latest_index + 1)

        fn = eval_path / f"{curr_date}_{eval_name}_{latest_index}.txt"
        with open(fn, "w") as f:
            f.write(self._content)

    def _get_file_index(self, fn: Path):
        return int(fn.name.split(".")[0].split("_")[-1])

    def __str__(self):
        return self._content


def match_clusters(cluster_a: List[ClusteredTopic], 
                 cluster_b: List[ClusteredTopic], 
                 min_match=3):
    """
    Loops through all clusters to find the best match for each cluster in the other set.
    """
    min_match = 0
    matched_clusters = []
    for a in cluster_a:
        best_match = None
        best_score = -1
        for b in cluster_b:
            score = len(set(a.chunks) & set(b.chunks))
            if score > best_score:
                best_score = score
                best_match = b
        if best_score >= min_match:
            matched_clusters.append((a, best_match))

    return matched_clusters
    