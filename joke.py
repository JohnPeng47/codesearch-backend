import ell
from src.llm.utils import get_session_cost

ell.init(store="logdir")

@ell.complex(model="gpt-4o-mini", temperature=2, max_tokens=200)
def tell_joke():
    """
    Generate a joke using the language model.
    """
    JOKE_PROMPT = """
    Tell me a short, clever joke that's suitable for all ages. 
    The joke should be witty and make people smile.
    """
    return JOKE_PROMPT

@ell.complex(model="gpt-4o-mini", temperature=2, max_tokens=200)
def tell_story():
    """
    Generate a joke using the language model.
    """
    STORY_PROMPT = """
Welcome to gpt-tokenizer. Replace this with your text to see how tokenization works.# Story Writing Prompt Framework

## Setting
- **Time Period**: Late Victorian Era (1880s)
- **Location**: A prosperous coastal town in Cornwall, England
- **Season/Weather**: Autumn, with frequent storms and misty mornings
- **Key Locations**:
  - An old lighthouse perched on treacherous cliffs
  - A bustling harbor filled with fishing boats and merchant vessels
  - A grand manor house overlooking the town
  - Narrow, cobblestone streets lined with gas lamps

## Main Character
- **Name**: Elizabeth "Beth" Blackwood
- **Age**: 27
- **Occupation**: The town's only female physician
- **Physical Description**: Tall and willowy with auburn hair, usually dressed in practical dark clothing
- **Key Traits**:
  - Highly intelligent but socially awkward
  - Determined to prove herself in a male-dominated profession
  - Harbors a deep fear of the ocean despite living in a coastal town
  - Possesses an unusual ability to sense when death is near
- **Background**: Daughter of a renowned London surgeon, moved to Cornwall to escape her father's shadow

## Supporting Characters
1. **James Morrison**
   - 45-year-old lighthouse keeper
   - Widower with a mysterious past
   - Only person who knows Beth's secret ability
   
2. **Lady Margaret Pembrooke**
   - Elderly aristocrat living in the manor house
   - Beth's primary patron and protector
   - Keeping her own dark secrets about the town's history
   
3. **Dr. Thomas Reed**
   - 50-year-old senior physician
   - Initially skeptical of Beth but gradually becomes an ally
   - Hiding a degenerative illness that's affecting his work

## Central Conflict
A series of mysterious deaths begins plaguing the town:
- All victims are found near the harbor
- Each body shows signs of drowning but with unexplainable burns
- Deaths only occur during the new moon
- Local authorities are baffled
- Beth's ability suggests these aren't natural deaths

## Plot Elements to Include
1. **Primary Mystery**
   - The true nature of the deaths
   - Connection to an old town legend about merfolk
   - Lady Pembrooke's involvement

2. **Personal Challenges**
   - Beth must confront her fear of the ocean
   - Professional rivalry with a newly arrived male doctor
   - Growing romantic tension with James Morrison

3. **Historical Context**
   - Town's dependence on fishing and maritime trade
   - Victorian medical practices and limitations
   - Social restrictions on women in professional roles

## Thematic Elements
- The conflict between science and supernatural
- Gender roles and societal expectations
- The price of ambition and success
- The weight of family legacy
- The power of facing one's fears

## Story Structure Guidelines
1. **Opening Scene**: Begin with Beth being called to examine a body at the harbor during a stormy dawn
2. **First Act**: Establish Beth's position in town and introduce the first mysterious death
3. **Middle Development**: 
   - Escalate the frequency of deaths
   - Deepen Beth's involvement with James
   - Reveal connections to town history
4. **Climax**: Set during the biggest storm of the season, forcing Beth to confront both her fears and the truth
5. **Resolution**: Should tie together both the supernatural and scientific elements while leaving some mystery intact

## Technical Requirements
- Written in third person, past tense
- Include detailed sensory descriptions of the Victorian coastal setting
- Maintain period-appropriate dialogue and medical knowledge
- Balance supernatural elements with historical realism
- Include at least three scenes from the lighthouse
- Incorporate weather as a mood-setting device

## Optional Elements to Consider
- A parallel storyline from 50 years earlier
- Local folklore and superstitions- Incorporate weather as a mood-setting device

## Optional Elements to Consider
- A parallel storyline from 50 years earlier
- Local folklore and superstitions
- Period-specific medical procedures
- Maritime navigation techniques
- Incorporate weather as a mood-setting device

## Optional Elements to Consider
- A parallel storyline from 50 years earlier
- Local folklore and superstitions
- Period-specific medical procedures
- Maritime navigation techniques
- Incorporate weather as a mood-setting device

## Optional Elements to Consider
- A parallel storyline from 50 years earlier
- Local folklore and superstitions
- Period-specific medical procedures
- Maritime navigation techniques
- Incorporate weather as a mood-setting device

## Optional Elements to Consider
- A parallel storyline from 50 years earlier
- Local folklore and superstitions
- Period-specific medical procedures
- Maritime navigation techniques
- Incorporate weather as a mood-setting device

## Optional Elements to Consider
- A parallel storyline from 50 years earlier
- Local folklore and superstitions
- Period-specific medical procedures
- Maritime navigation techniques

- Period-specific medical procedures
- Maritime navigation techniques
- Victorian mourning customs

This prompt provides a foundation for a gothic mystery with elements of historical fiction, romance, and supernatural thriller. Writers can expand or modify elements while maintaining the core narrative structure.    """
    return STORY_PROMPT

for i in range(3):
    tell_story()

p_tokens, c_tokens, cached_tokens = get_session_cost()
print(f"Prompt tokens: {p_tokens}, Completion tokens: {c_tokens}, Cached tokens: {cached_tokens}")