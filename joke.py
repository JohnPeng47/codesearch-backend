import ell
from pydantic import BaseModel
from typing import List

from src.llm.lmp_base.logprobs import LogProbLMP


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

@ell.complex(model="gpt-4o-mini", temperature=2, max_tokens=20, return_metadata=True)
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

@ell.complex(model="gpt-4o-mini", max_tokens=100, return_metadata=True)
def write_short_story(subject):
   """
   Generate a short story using the language model.
   """
   return """
   Write a short story about {subject}. 
   The story should be engaging and have a clear beginning, middle, and end.
   """.format(subject=subject)


class ShortStory(BaseModel):
   story: str
   characters: List[str]
   setting: str
   plot: str


# lmp = UnstructuredLMP(write_short_story)
# res = lmp.call("cats", response_format=ShortStory)
# print(res)

lmp = LogProbLMP(write_short_story)
res = lmp.call("cats")
print(res)
print(lmp.logprobs())
print(lmp.logprobs().perplexity())