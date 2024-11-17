class ClientActionException(Exception):
    """
    Exception type that needs to be displayed and handled in the client
    """
    def __init__(self, *, message):
        self.message = message
        
        super().__init__()

class LLMException(Exception):
    """
    Exception class for errors during LLM generation
    """
    pass