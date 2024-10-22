import ell

@ell.complex(model="gpt-4o-mini", temperature=2)
def tell_joke():
    """
    Generate a joke using the language model.
    """
    JOKE_PROMPT = """
    Tell me a short, clever joke that's suitable for all ages. 
    The joke should be witty and make people smile.
    """
    return JOKE_PROMPT

a, metadata, c = tell_joke()
print(metadata)
print(c)