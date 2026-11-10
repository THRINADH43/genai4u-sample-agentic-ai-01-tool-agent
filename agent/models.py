"""Models return either {"tool": name, "args": {...}} or {"answer": text}."""

import json
import os
import urllib.request

from agent.tools import schemas_for_model


class FakeModel:
    """Plays back a script of replies, one per step. Tests use it so they need no key."""

    def __init__(self, script):
        self.script = list(script)
        self.seen = []

    def next(self, messages):
        self.seen.append(list(messages))
        if not self.script:
            return {"answer": "I have run out of scripted replies."}
        return self.script.pop(0)


class GroqModel:
    def __init__(self, model="openai/gpt-oss-20b"):
        self.key = os.environ["GROQ_API_KEY"]
        self.model = model

    def next(self, messages):
        body = {"model": self.model, "messages": messages, "tools": schemas_for_model(), "temperature": 0}
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                                              "User-Agent": "tool-agent/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            msg = json.load(r)["choices"][0]["message"]
        if msg.get("tool_calls"):
            call = msg["tool_calls"][0]["function"]
            try:
                args = json.loads(call["arguments"] or "{}")
            except json.JSONDecodeError:
                args = call["arguments"]  # invalid JSON: validation will report it
            return {"tool": call["name"], "args": args}
        return {"answer": msg.get("content") or ""}
