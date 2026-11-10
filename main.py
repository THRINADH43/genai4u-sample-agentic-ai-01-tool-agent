"""python main.py "What is 15% of 2400?"        (Groq if GROQ_API_KEY is set)
python main.py --fake "When is the demo?"       (scripted fake model, no key)"""

import os
import sys

from agent.loop import run_agent
from agent.models import FakeModel, GroqModel


def main():
    args = sys.argv[1:]
    fake = "--fake" in args
    question = " ".join(a for a in args if a != "--fake")
    if fake or not os.environ.get("GROQ_API_KEY"):
        model = FakeModel([{"tool": "search_notes", "args": {"query": question}},
                           {"answer": "(fake model) See the search result above."}])
    else:
        model = GroqModel()
    print(run_agent(question, model))


if __name__ == "__main__":
    main()
