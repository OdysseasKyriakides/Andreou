"""
Runs pandas code written by the LLM in a restricted namespace.

The LLM never answers with numbers itself: it writes code, the code runs on the
real log, and the app shows what the code computed.
"""
import ast
import re

import numpy as np
import pandas as pd
import plotly.express as px

BLOCKED_NAMES = {"eval", "exec", "open", "compile", "__import__", "globals", "locals", "getattr",
                 "setattr", "delattr", "vars", "input", "breakpoint", "exit", "quit"}
ALLOWED_BUILTINS = {name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)
                    for name in ["len", "min", "max", "sum", "round", "sorted", "list", "dict", "set", "tuple",
                                 "range", "enumerate", "zip", "abs", "str", "int", "float", "bool", "any",
                                 "all", "isinstance", "map", "filter", "print", "Exception", "ValueError"]}


def extract_code(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def check_code(code):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("imports are not allowed")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"'{node.id}' is not allowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder attributes are not allowed")


def run_code(code, events, cases):
    check_code(code)
    ns = {"__builtins__": ALLOWED_BUILTINS, "pd": pd, "np": np, "px": px,
          "events": events.copy(), "cases": cases.copy(), "result": None, "fig": None, "answer": ""}
    exec(code, ns)
    return ns["result"], ns["fig"], ns["answer"]
