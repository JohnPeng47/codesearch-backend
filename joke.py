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

# Use the function to generate and print a joke
for i in range(5):
    print(tell_joke())