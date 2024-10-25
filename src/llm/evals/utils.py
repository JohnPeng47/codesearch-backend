from src.cluster.models import ClusteredTopic

from collections import defaultdict
from datetime import datetime
from typing import List, Dict
import os
from pathlib import Path
import copy

from src.config import EVAL_ROOT

class EvalReport:
    """
    For styling evaluation reports
    """
    _parent_instance: Dict[str, "EvalReport"] = {}

    def __init__(self, 
                 report_dir: str = None,
                 report_root: str = EVAL_ROOT): 
        # create the report root for today if it doesnt exist
        curr_date = datetime.now().strftime('%Y-%m-%d')
        report_root = Path(report_root) / curr_date
        if not report_root.exists():
            os.makedirs(report_root, exist_ok=True)

        # let report_dir be the same as report_root if not specified
        self.report_dir = report_root / report_dir if report_dir else report_root
        if not self.report_dir.exists():
            os.makedirs(self.report_dir, exist_ok=True)

        self._content = ""
        
    def add_section(self, name: str):
        self._content += f"###### {name} ######\n"

    def add_line(self, line: str):
        self._content += f"{line}\n"

    def write(self, name: str = ""):
        """
        Writes the evaluation log to a file with a unique, incremented index
        for a given date timestamp
        """        
        latest_index = self._get_file_index(self.report_dir)
        fp = self.report_dir / f"{name}{latest_index}.txt"
        
        with open(fp, "w", encoding="utf-8") as f:
            f.write(self._content)

    def _get_file_index(self, dir: Path, fn_prefix: str = ""):
        """
        Gets the next file index for a given directory
        """
        return str(
            max(
                [
                    int(self._get_file_index(fp)) for fp 
                    in dir.glob(f"{fn_prefix}*")
                ], default=0
            ) + 1
        )

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
    