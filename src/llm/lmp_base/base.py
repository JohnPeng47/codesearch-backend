from typing import Callable

class LMP:
    def __init__(self, lmp: Callable):
        self._lmp = lmp

    def call(self, *args, **kwargs):
        return self._lmp(*args, **kwargs)