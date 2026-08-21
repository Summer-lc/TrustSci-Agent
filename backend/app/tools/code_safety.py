import ast

DENIED_MODULES = {"ctypes", "httpx", "importlib", "multiprocessing", "os", "pathlib", "pip", "requests",
                  "shutil", "socket", "subprocess", "sys", "urllib"}
DENIED_CALLS = {"__import__", "compile", "eval", "exec", "input", "open"}


class UnsafeGeneratedCode(ValueError):
    pass


def validate_generated_model(source: str) -> None:
    try:
        tree = ast.parse(source, filename="model.py")
    except SyntaxError as exc:
        raise UnsafeGeneratedCode(f"model.py syntax error: {exc.msg}") from exc
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(f"denied import: {a.name}" for a in node.names if a.name.split(".", 1)[0] in DENIED_MODULES)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".", 1)[0] in DENIED_MODULES:
            violations.append(f"denied import: {node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in DENIED_CALLS:
            violations.append(f"denied call: {node.func.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.append(f"denied dunder attribute: {node.attr}")
    if violations:
        raise UnsafeGeneratedCode("; ".join(sorted(set(violations))))
