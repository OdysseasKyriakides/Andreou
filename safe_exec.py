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
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor

BLOCKED_NAMES = {"eval", "exec", "open", "compile", "__import__", "globals", "locals", "getattr",
                 "setattr", "delattr", "vars", "input", "breakpoint", "exit", "quit"}
ALLOWED_BUILTINS = {name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)
                    for name in ["len", "min", "max", "sum", "round", "sorted", "list", "dict", "set", "tuple",
                                 "range", "enumerate", "zip", "abs", "str", "int", "float", "bool", "any",
                                 "all", "isinstance", "map", "filter", "print", "Exception", "ValueError",
                                 "reversed", "next", "hasattr", "KeyError", "TypeError", "IndexError"]}


def extract_code(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


# harmless libraries the generated code may import (everything else stays blocked)
ALLOWED_MODULES = {"pandas", "numpy", "sklearn", "datetime", "math", "statistics"}


def _module_ok(name):
    return (name or "").split(".")[0] in ALLOWED_MODULES


def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or not _module_ok(name):
        raise ImportError(f"import of '{name}' is not allowed")
    return __import__(name, globals, locals, fromlist, level)


def check_code(code):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and not all(_module_ok(a.name) for a in node.names):
            raise ValueError(f"only these imports are allowed: {sorted(ALLOWED_MODULES)}")
        if isinstance(node, ast.ImportFrom) and (node.level or not _module_ok(node.module)):
            raise ValueError(f"only these imports are allowed: {sorted(ALLOWED_MODULES)}")
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


ML_MODELS = {"RandomForestRegressor": RandomForestRegressor, "GradientBoostingRegressor": GradientBoostingRegressor,
             "LinearRegression": LinearRegression, "KNeighborsRegressor": KNeighborsRegressor}


LLM_FILE = "<llm_code>"


def describe_error(e, code):
    """Error message + the line of the generated code that raised it (sent back to the LLM on retry)."""
    import traceback
    msg = f"{type(e).__name__}: {e}"
    frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == LLM_FILE]
    if frames:
        n = frames[-1].lineno
        msg += f" (line {n}: {code.splitlines()[n - 1].strip()})"
    return msg


def run_fix_code(code, events):
    """Step 5: the code must assign `fixed` (events + is_error + timestamp_fixed) and `answer`."""
    check_code(code)
    ns = {"__builtins__": {**ALLOWED_BUILTINS, "__import__": safe_import}, "pd": pd, "np": np, **ML_MODELS,
          "events": events.copy(), "fixed": None, "answer": ""}
    exec(compile(code, LLM_FILE, "exec"), ns)
    fixed = ns["fixed"]
    if not isinstance(fixed, pd.DataFrame):
        raise ValueError("`fixed` must be a pandas DataFrame")
    missing = {"case", "activity", "is_error", "timestamp_fixed"} - set(fixed.columns)
    if missing:
        raise ValueError(f"`fixed` is missing the columns {sorted(missing)}")
    return fixed, str(ns["answer"])
