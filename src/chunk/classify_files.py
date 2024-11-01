from pathlib import Path
from typing import List
import os

from .lmp.classify_tree import classify_tree
from .tree.tree import generate_tree
from .models import ClassifiedFile

def classify_files(repo_dir: Path, exclusions=[], iters=3) -> List[ClassifiedFile]:
    # Initialize control flags and state
    classified_fps = []
    all_fps = [
        # gotta replace pathsep to normalize for windows
        str(p.relative_to(repo_dir)).replace("\\", "/") 
        for p in list(repo_dir.rglob("*"))
        if not any(p.match(pattern) for pattern in exclusions)
    ]
    should_continue = True
    remaining_iters = iters
    current_exclusions = exclusions.copy()

    print("Total files: ", len(all_fps))
    while should_continue:
        # Get current batch of files
        tree = generate_tree(repo_dir, exclusions=current_exclusions)
        current_files = classify_tree(tree).parsed.classified_files
        
        # Process current batch
        for file in current_files:
            has_file = file.fp in all_fps
            if has_file:
                all_fps.remove(file.fp)
                classified_fps.append(file)
        
        # Update state for next iteration
        current_exclusions = exclusions + [f.fp for f in classified_fps]
        remaining_iters -= 1
        should_continue = remaining_iters > 0 and len(all_fps) > 0
        
        print("Remaining files: ", len(all_fps))

    return classified_fps