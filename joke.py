import ell
# from ell.ctxt import get_session_id
# from src.llm.utils import get_session_cost

ell.init(store="logdir/test_joke")

ell.complex(model="gpt-4o-mini", temperature=2, max_tokens=50)
def suggest_jokes():
   TOPIC_PROMPT = """
   Suggest some funny topics for a joke.
   """
   return TOPIC_PROMPT

ell.complex(model="gpt-4o-mini", temperature=2, max_tokens=50)
def select_joke(topics: str):
   SELECT_TOPIC_PROMPT = """
   From the following topics, select one that would make the funniest joke: {topics}
   """
   return SELECT_TOPIC_PROMPT.format(topics=topics)

@ell.complex(model="gpt-4o-mini", temperature=2, max_tokens=20)
def tell_joke():
   """
   Generate a joke using the language model.
   """
   JOKE_PROMPT = """
   Tell me a short, clever joke about {subject}. 
   The joke should be witty and make people smile.
   """

   # suggestions = suggest_jokes()
   # selected = select_joke(suggestions)
   return JOKE_PROMPT.format(subject=select_joke(suggest_jokes()))

# print(tell_joke(subject="chickens"))

# import threading

# threads = []
# for i in range(3):
#     thread = threading.Thread(target=tell_story, kwargs={"session_id": get_session_id()})
#     threads.append(thread)
#     thread.start()

# for thread in threads:
#     thread.join()

print(tell_joke())

# cost = get_session_cost()
# print(cost)