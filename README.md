# Tool-using assistant from scratch

An agent in plain Python (no framework, standard library only) that answers questions with
three tools: a calculator, a note reader and a note search. I wrote the agent loop myself.

## Run

```
python main.py --fake "When is the demo?"                 # fake model, no key
GROQ_API_KEY=... python main.py "What is 15% of 2400?"    # real model on Groq (openai/gpt-oss-20b)
python -m unittest discover -s tests -t .
```

The key is read from `GROQ_API_KEY` (see `.env.example`) and never stored in the code.
`requirements.txt` is empty: only the standard library is used. The notes are `.md` files in
`notes/`.

Example with Groq:

```
step 1: search_notes({"query": "demo"}) -> 'deadlines.md: Project deadline: 15 December. Demo to the client on 18 December.'
step 2: answer
The demo to the client is on 18 December.
```

## The loop (`agent/loop.py`)

1. **Think:** send the conversation to the model. It replies with a tool call or an answer.
2. **Act:** validate the call and run the tool.
3. **Observe:** add the result (or the error) to the conversation.
4. Repeat, at most `max_steps` (5) times. After that the agent stops and says so, so a
   confused model cannot loop forever.

## Tools (`agent/tools.py`)

| tool | arguments | limits |
|------|-----------|--------|
| `calculator` | `expression` | parsed with `ast`; only numbers and `+ - * / % **`; never `eval()`; exponent at most 100 |
| `read_note` | `name` | only files inside `notes/`; `../` and absolute paths are refused |
| `search_notes` | `query` | top 3 notes by word count |

Each tool has a JSON Schema, and the schemas are sent to the model as tool definitions
(`schemas_for_model`). `validate()` checks every call before it runs: the tool exists,
arguments are an object, required keys are present, no extra keys, strings are strings and
not too long. A bad call does not crash the agent: the error goes back to the model as the
tool result so it can try again.

## Fake model

`FakeModel` plays back a list of replies, one per step, and records what it was sent. All
tests use it, so they run without an API key or network.

## Tests

Calculator (including attempts to run code), path escapes, search, schema validation, the
loop using a tool and answering, unknown tools reported back, the step limit, and a
two-tool question.
