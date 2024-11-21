from pydantic import BaseModel

class A(BaseModel):
    a: int
    b: str

    def __init__(self, **kwargs):
        self.a = 1
        self.b = 2
        self.c = 3

        super.__init__(**kwargs)


A()