"""Regression guard for the PyInstaller entry points.

`dcs-serve.spec` and `dcs-client.spec` pass an application module to
`Analysis([...])`, which makes that module *the frozen script*: PyInstaller runs it
top-to-bottom and exits. Without an `if __name__ == "__main__": main()` block the
executable therefore defines everything and quits without starting anything — the
Poetry console-scripts (`dcs-serve = ...app:main`) hide the gap during development.

These tests assert the guard is present in every module a spec freezes as a script.
The release workflow additionally smoke-tests the built `dcs-serve.exe`.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILES = ("dcs-serve.spec", "dcs-client.spec")


def _analysis_scripts(spec_path: Path) -> list[str]:
    """Extract the script paths passed to `Analysis([...])` in a PyInstaller spec.

    Args:
        spec_path: Path to the `.spec` file (valid Python syntax, parsed not executed).

    Returns:
        The string literals of the first positional argument of the `Analysis` call.
    """
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Analysis"
            and node.args
            and isinstance(node.args[0], ast.List)
        ):
            return [elt.value for elt in node.args[0].elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
    return []


def _has_main_guard(module_path: Path) -> bool:
    """Check whether a module has a top-level `__name__ == "__main__"` block calling `main()`.

    Args:
        module_path: Path to the Python module to inspect.

    Returns:
        True if the guard exists and its body calls `main()`.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        left = node.test.left
        right = node.test.comparators[0] if node.test.comparators else None
        guards_main = (
            isinstance(left, ast.Name)
            and left.id == "__name__"
            and isinstance(right, ast.Constant)
            and right.value == "__main__"
        )
        if not guards_main:
            continue
        return any(
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == "main"
            for stmt in node.body
        )
    return False


@pytest.mark.parametrize("spec_name", SPEC_FILES)
def test_spec_declares_exactly_one_entry_script(spec_name: str) -> None:
    """Each spec must freeze a single, existing module as its script."""
    scripts = _analysis_scripts(REPO_ROOT / spec_name)
    assert len(scripts) == 1, f"{spec_name}: expected one Analysis script, got {scripts}"
    assert (REPO_ROOT / scripts[0]).is_file(), f"{spec_name}: script {scripts[0]} does not exist"


@pytest.mark.parametrize("spec_name", SPEC_FILES)
def test_frozen_script_invokes_main(spec_name: str) -> None:
    """The frozen script must call `main()` itself, or the .exe starts and exits."""
    script = _analysis_scripts(REPO_ROOT / spec_name)[0]
    assert _has_main_guard(REPO_ROOT / script), (
        f"{script} is frozen as the script by {spec_name} but has no "
        'if __name__ == "__main__": main() block — the built .exe would exit doing nothing.'
    )
