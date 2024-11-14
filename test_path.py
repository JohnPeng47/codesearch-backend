from src.chat.models import WalkthroughChat 
from src.config import WALKTHROUGH_ROOT
import json

from openai import OpenAI



walkthrough_path = WALKTHROUGH_ROOT / "aorwall_moatless-tools"

with open(walkthrough_path) as f:
    c = json.loads(f.read())
    WalkthroughChat(c)
