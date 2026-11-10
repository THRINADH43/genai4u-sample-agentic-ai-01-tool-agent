"""The agent loop: think (ask the model), act (run the tool it chose), observe (add the
result to the conversation), and repeat until it answers or the step limit is reached."""

import json

from agent.tools import ToolError, run_tool

SYSTEM = ("You are a helpful assistant. Use the tools when they help: calculator for arithmetic, "
          "search_notes and read_note for anything about the user's notes. Answer briefly.")


def run_agent(question, model, max_steps=5, log=print):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for step in range(1, max_steps + 1):
        reply = model.next(messages)                       # think
        if "answer" in reply:
            log(f"step {step}: answer")
            return reply["answer"]
        name, args = reply.get("tool"), reply.get("args")
        try:
            result = run_tool(name, args)                  # act (validated first)
        except ToolError as err:
            result = f"ERROR: {err}"
        except TypeError as err:
            result = f"ERROR: bad arguments: {err}"
        log(f"step {step}: {name}({json.dumps(args)}) -> {result[:80]!r}")
        messages.append({"role": "assistant", "content": json.dumps({"tool": name, "args": args})})
        messages.append({"role": "user", "content": f"Tool result from {name}:\n{result}"})  # observe
    return f"I stopped after {max_steps} steps without an answer."
