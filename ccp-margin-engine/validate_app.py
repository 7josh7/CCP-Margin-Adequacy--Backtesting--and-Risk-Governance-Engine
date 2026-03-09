"""Verify streamlit_app.py compiles without errors."""
import sys, ast
from pathlib import Path

app_file = Path(__file__).resolve().parent / "app" / "streamlit_app.py"
source = app_file.read_text(encoding="utf-8")

# 1. AST parse – catches all syntax errors
tree = ast.parse(source, filename=str(app_file))
print(f"AST parse OK  ({len(tree.body)} top-level nodes)")

# 2. Compile to bytecode – catches anything AST misses
code = compile(source, str(app_file), "exec")
print(f"Compile OK  ({len(code.co_consts)} constants)")

# 3. Verify 'config' import is present
import_names = []
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module:
        for alias in node.names:
            import_names.append(f"{node.module}.{alias.name}" if alias.name != "*" else node.module)
    elif isinstance(node, ast.Import):
        for alias in node.names:
            import_names.append(alias.name)

assert any("config" in n for n in import_names), "Missing 'config' import"
print("Config import present ✓")

# 4. Check that all 'config.XXX' attribute references resolve
import importlib
sys.path.insert(0, str(app_file.parent.parent))
config = importlib.import_module("src.config")
for node in ast.walk(tree):
    if (isinstance(node, ast.Attribute) and
        isinstance(node.value, ast.Name) and
        node.value.id == "config"):
        attr = node.attr
        assert hasattr(config, attr), f"config.{attr} not found!"
        print(f"  config.{attr} = {getattr(config, attr)}")

print("\n=== STREAMLIT APP VALIDATION PASSED ===")
