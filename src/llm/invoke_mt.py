from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Dict, Any

def invoke_multithread(args: List, func: Callable, max_workers: int = 6) -> Dict[str, Any]:
    results = [None] * len(args)  # Initialize a list to store results in order

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and map them to their indices
        future_to_index = {executor.submit(func, arg): index for index, arg in enumerate(args)}
        
        # Process completed futures as they finish
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results[index] = result  # Store result in the correct position
            except Exception as e:
                raise e
    
    return results