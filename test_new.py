class Hello:
    a = 1
    def __new__(cls):
        print("Creating instance")
        return super().__new__(cls)
        

    def __init__(self):
        self.b = 2
    
    def clone(self):
        instance = object.__new__(self.__class__)
        for k,v in self.__dict__.items():
            setattr(instance, k, v)     

        return instance   


h = Hello()
print(h.a, h.b)
c = h.clone()
print(c.a, c.b)
