from src.llm.ell_api import get_invocations_by_session
import ell
import json

sessions = get_invocations_by_session("generate_clusters")
for sess, invocations in sessions.items():
    for inv in invocations:
        if getattr(inv.contents, "results", None):
            print(inv.contents.params["chunks"][0])