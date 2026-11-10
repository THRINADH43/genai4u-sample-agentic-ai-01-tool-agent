"""Three tools, each with a JSON-style schema. Arguments are validated before a tool runs."""

import ast
import operator
import os
import re

NOTES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notes")


class ToolError(Exception):
    """A tool call was invalid or failed. The message goes back to the model."""


# ---- calculator: parses the expression, never uses eval() --------------------------------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ToolError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ToolError("only numbers and + - * / % ** are allowed")


def calculator(expression):
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except ZeroDivisionError:
        raise ToolError("division by zero")
    except SyntaxError:
        raise ToolError(f"not a valid expression: {expression!r}")


def read_note(name):
    """Reads one file from notes/. Paths that leave the folder are refused."""
    path = os.path.realpath(os.path.join(NOTES_DIR, name))
    if not path.startswith(os.path.realpath(NOTES_DIR) + os.sep):
        raise ToolError("only files inside notes/ can be read")
    if not os.path.isfile(path):
        raise ToolError(f"no note called {name!r}; available: {', '.join(sorted(os.listdir(NOTES_DIR)))}")
    with open(path, encoding="utf-8") as f:
        return f.read()[:2000]


STOP_WORDS = {"the", "and", "for", "when", "what", "where", "who", "how", "is", "are", "was", "my", "our"}


def search_notes(query):
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2 and w not in STOP_WORDS]
    hits = []
    for name in sorted(os.listdir(NOTES_DIR)):
        with open(os.path.join(NOTES_DIR, name), encoding="utf-8") as f:
            text = f.read()
        note_words = re.findall(r"[a-z0-9]+", text.lower())
        score = sum(note_words.count(w) for w in words)
        if score:
            hits.append((score, name, text.strip()[:120]))
    hits.sort(reverse=True)
    return "\n".join(f"{name}: {preview}" for _, name, preview in hits[:3]) or "no matching notes"


TOOLS = {
    "calculator": {
        "function": calculator,
        "description": "Evaluate an arithmetic expression, e.g. '(12 + 8) * 3'.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string", "maxLength": 200}},
                       "required": ["expression"], "additionalProperties": False},
    },
    "read_note": {
        "function": read_note,
        "description": "Read one note file from the notes folder by its file name.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string", "maxLength": 100}},
                       "required": ["name"], "additionalProperties": False},
    },
    "search_notes": {
        "function": search_notes,
        "description": "Search all notes for words and return the best matching files.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "maxLength": 200}},
                       "required": ["query"], "additionalProperties": False},
    },
}


def validate(name, args):
    """Check a call against the tool's schema: known tool, an object, required keys present,
    no extra keys, right types, length limits."""
    if name not in TOOLS:
        raise ToolError(f"unknown tool {name!r}; tools are {', '.join(TOOLS)}")
    if not isinstance(args, dict):
        raise ToolError("arguments must be a JSON object")
    schema = TOOLS[name]["parameters"]
    for key in schema["required"]:
        if key not in args:
            raise ToolError(f"missing argument {key!r}")
    for key, value in args.items():
        spec = schema["properties"].get(key)
        if spec is None:
            raise ToolError(f"unexpected argument {key!r}")
        if spec["type"] == "string" and not isinstance(value, str):
            raise ToolError(f"{key!r} must be a string")
        if len(value) > spec.get("maxLength", 10_000):
            raise ToolError(f"{key!r} is too long")


def run_tool(name, args):
    validate(name, args)
    return TOOLS[name]["function"](**args)


def schemas_for_model():
    return [{"type": "function", "function": {"name": n, "description": t["description"], "parameters": t["parameters"]}}
            for n, t in TOOLS.items()]
