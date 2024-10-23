from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable

def invoke_multithread(args: List, func: Callable, max_workers: int = 4):
    with ThreadPoolExecutor as executor:
        results_list = list(executor.map(func,args,))
        
    return results_list

