from src.cluster.types import ClusteredTopic

from collections import defaultdict
from datetime import datetime
from typing import List, Dict
import os
from pathlib import Path
import inspect
import copy

class EvalReport:
    """
    For styling evaluation reports
    """
    _parent_instance: Dict[str, "EvalReport"] = {}

    def __new__(cls, title: str, reportdir: Path = "", log_local: bool = False):
        caller_file = inspect.currentframe().f_back.f_code.co_filename
        parent_instance = cls._parent_instance.get(caller_file)
        if parent_instance:
            child_logger: "EvalReport" = parent_instance._clone()
            child_logger._init_child(title, reportdir, log_local=log_local)
            return child_logger
        
        print(f"Creating new instance for {caller_file}")
        instance = super().__new__(cls)
        cls._parent_instance[caller_file] = instance
        instance.__init__(title, reportdir, is_parent=True, log_local=log_local)
        return instance

    # NOTE: very strange behaviour, that this would get called even if __new__
    # returns the child instance
    def __init__(self, 
                 title: str, 
                 reportdir: Path = "", 
                 log_local: bool = False, 
                 is_parent: bool = False):
        if not is_parent:
            return

        if not log_local:
            if not reportdir.exists():
                os.makedirs(reportdir, exist_ok=True)
            curr_date = datetime.now().strftime('%Y-%m-%d')
            f_index = self._get_file_index(reportdir, fn_prefix=curr_date)

            self._currdir = reportdir / f"{curr_date}_{f_index}"
            os.makedirs(self._currdir, exist_ok=True)
        else:
            self._currdir = Path(".")

        self._content = f"_____ {title} _____\n\n"

        print("Initializing parent with: ", self._currdir)

    def _init_child(self, title: str, child_dir: Path, log_local: bool = False):
        print("Initializing child with: ", self._currdir)
        if not log_local:
            self._currdir = self._currdir / child_dir
            if not self._currdir.exists():
                os.makedirs(self._currdir, exist_ok=True)
        else:
            self._currdir = Path(".")

        self._content = f"_____ {title} _____\n\n"
        
    def add_section(self, name: str):
        self._content += f"###### {name} ######\n"

    def add_line(self, line: str):
        self._content += f"{line}\n"

    def write(self, name: str = ""):
        """
        Writes the evaluation log to a file with a unique, incremented index
        for a given date timestamp
        """        
        latest_index = self._get_file_index(self._currdir)
        fp = self._currdir / f"{name}{latest_index}.txt"
        
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

    def _clone(self):
        """
        Creates a deep copy of the current EvalReport
        """
        new_instance = object.__new__(EvalReport)
        for attr, value in self.__dict__.items():
            setattr(new_instance, attr, copy.deepcopy(value))
        
        return new_instance

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
    