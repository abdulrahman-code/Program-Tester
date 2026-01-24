# -*- coding: utf-8 -*-
"""
Program Tester (Dark UI, English-only)
- Upload one Python (.py) file
- Run static checks (no execution): syntax, style, docstrings, naming, complexity, risky patterns
- Run a basic unit test in a subprocess with timeout (imports the module, which executes top-level code)
- Show results in a clean dark GUI

Standard library only (no pip).
"""

from __future__ import annotations

import ast
import io
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk


# ----------------------------
# Colors (Dark Theme)
# ----------------------------

BG = "#121212"
CARD = "#1E1E1E"
CARD_2 = "#242424"
FG = "#E6E6E6"
MUTED = "#A8A8A8"
BORDER = "#2B2B2B"
ACCENT = "#4C8BF5"
ACCENT_HOVER = "#3B78DD"
BTN_GHOST = "#2A2A2A"
BTN_GHOST_HOVER = "#333333"
TEXT_BG = "#0F0F0F"
TEXT_FG = "#EDEDED"
TEXT_INSERT = "#FFFFFF"
TEXT_SEL = "#2F5DA8"


# ----------------------------
# Core analysis utilities
# ----------------------------

SNAKE_CASE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@dataclass
class RunResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    seconds: float
    timed_out: bool


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def safe_run(cmd: List[str], cwd: Path, timeout_sec: int) -> RunResult:
    t0 = time.time()
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        dt = time.time() - t0
        return RunResult(
            ok=(p.returncode == 0),
            returncode=p.returncode,
            stdout=p.stdout or "",
            stderr=p.stderr or "",
            seconds=dt,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as e:
        dt = time.time() - t0
        return RunResult(
            ok=False,
            returncode=124,
            stdout=(e.stdout or ""),
            stderr=(e.stderr or "Process timed out."),
            seconds=dt,
            timed_out=True,
        )


def syntax_check(source: str) -> Dict[str, Any]:
    try:
        compile(source, "<uploaded>", "exec")
        return {"ok": True, "error": None}
    except SyntaxError as e:
        return {
            "ok": False,
            "error": {
                "type": "SyntaxError",
                "msg": str(e),
                "lineno": e.lineno,
                "offset": e.offset,
                "text": (e.text or "").rstrip("\n"),
            },
        }


def style_check(source: str) -> Dict[str, Any]:
    lines = source.splitlines(True)
    issues: List[Dict[str, Any]] = []
    counts = {
        "total_lines": len(lines),
        "long_lines_gt_100": 0,
        "trailing_whitespace_lines": 0,
        "tab_char_lines": 0,
        "mixed_indentation": 0,
    }

    has_tab_indent = False
    has_space_indent = False

    for i, line in enumerate(lines, start=1):
        raw = line.rstrip("\n")
        if len(raw) > 100:
            counts["long_lines_gt_100"] += 1
            issues.append({"line": i, "type": "LongLine", "detail": f"Length={len(raw)} > 100"})
        if raw != raw.rstrip(" \t"):
            counts["trailing_whitespace_lines"] += 1
            issues.append({"line": i, "type": "TrailingWhitespace", "detail": "Trailing spaces/tabs"})
        if "\t" in line:
            counts["tab_char_lines"] += 1
        if line.startswith("\t"):
            has_tab_indent = True
        if line.startswith(" "):
            has_space_indent = True

    if has_tab_indent and has_space_indent:
        counts["mixed_indentation"] = 1
        issues.append({"line": None, "type": "MixedIndentation", "detail": "Both tabs and spaces used for indentation"})

    return {"counts": counts, "issues": issues[:200]}


def risky_patterns(source: str) -> Dict[str, Any]:
    flags: List[Dict[str, str]] = []
    patterns = {
        "eval(": "Use of eval()",
        "exec(": "Use of exec()",
        "os.system": "Shell execution via os.system",
        "subprocess.Popen": "Process spawning via subprocess.Popen",
        "pickle.loads": "Unsafe deserialization risk (pickle.loads)",
        "import *": "Wildcard import reduces clarity",
    }
    for key, msg in patterns.items():
        if key in source:
            flags.append({"pattern": key, "detail": msg})
    return {"flags": flags}


def comment_stats(source: str) -> Dict[str, Any]:
    comments: List[str] = []
    try:
        tokgen = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok_type, tok_str, _, _, _ in tokgen:
            if tok_type == tokenize.COMMENT:
                comments.append(tok_str.lstrip("#").strip())
    except Exception:
        comments = []

    total_lines = max(1, len(source.splitlines()))
    comment_lines = len(comments)
    density = comment_lines / total_lines

    return {
        "comment_lines": comment_lines,
        "total_lines": total_lines,
        "comment_density": round(density, 4),
        "sample_comments": comments[:8],
    }


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_complexities: List[Tuple[str, int, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        c = self._complexity_of(node)
        self.function_complexities.append((node.name, getattr(node, "lineno", -1), c))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        c = self._complexity_of(node)
        self.function_complexities.append((node.name, getattr(node, "lineno", -1), c))
        self.generic_visit(node)

    def _complexity_of(self, fn: ast.AST) -> int:
        inc = 0
        for n in ast.walk(fn):
            if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.ExceptHandler)):
                inc += 1
            elif isinstance(n, ast.BoolOp):
                inc += max(1, len(getattr(n, "values", [])) - 1)
            elif hasattr(ast, "Match") and isinstance(n, getattr(ast, "Match")):
                inc += 1
        return 1 + inc


def docstrings_and_naming(tree: ast.AST) -> Dict[str, Any]:
    module_doc = ast.get_docstring(tree)
    fn_info: List[Dict[str, Any]] = []
    cls_info: List[Dict[str, Any]] = []
    naming_issues: List[Dict[str, Any]] = []

    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_doc = ast.get_docstring(node) is not None
            fn_info.append({"name": node.name, "lineno": getattr(node, "lineno", None), "has_docstring": has_doc})
            if not (node.name.startswith("_") or (node.name.startswith("__") and node.name.endswith("__"))):
                if not SNAKE_CASE_RE.match(node.name):
                    naming_issues.append({"type": "FunctionNameNotSnakeCase", "name": node.name, "lineno": node.lineno})
        elif isinstance(node, ast.ClassDef):
            has_doc = ast.get_docstring(node) is not None
            cls_info.append({"name": node.name, "lineno": getattr(node, "lineno", None), "has_docstring": has_doc})
            if not node.name.startswith("_"):
                if not PASCAL_CASE_RE.match(node.name):
                    naming_issues.append({"type": "ClassNameNotPascalCase", "name": node.name, "lineno": node.lineno})

    missing_fn_docs = sum(1 for f in fn_info if not f["has_docstring"])
    missing_cls_docs = sum(1 for c in cls_info if not c["has_docstring"])

    return {
        "module_has_docstring": module_doc is not None,
        "module_docstring_length": len(module_doc) if module_doc else 0,
        "functions": fn_info,
        "classes": cls_info,
        "missing_function_docstrings": missing_fn_docs,
        "missing_class_docstrings": missing_cls_docs,
        "naming_issues": naming_issues,
    }


def static_analysis(program_path: Path) -> Dict[str, Any]:
    source = read_text(program_path)

    syn = syntax_check(source)
    style = style_check(source)
    risky = risky_patterns(source)
    comm = comment_stats(source)

    ast_block: Dict[str, Any] = {"ok": False, "error": "Skipped due to syntax error."}
    if syn["ok"]:
        try:
            tree = ast.parse(source)
            cv = ComplexityVisitor()
            cv.visit(tree)
            comps = [{"name": n, "lineno": ln, "complexity": c} for (n, ln, c) in cv.function_complexities]
            comps_sorted = sorted(comps, key=lambda x: x["complexity"], reverse=True)
            ds = docstrings_and_naming(tree)
            ast_block = {
                "ok": True,
                "docstrings_naming": ds,
                "complexity_top5": comps_sorted[:5],
                "complexity_all": comps_sorted,
            }
        except Exception as e:
            ast_block = {"ok": False, "error": str(e)}

    return {
        "syntax": syn,
        "style": style,
        "risky_patterns": risky,
        "comments": comm,
        "ast": ast_block,
    }


def generate_basic_test(module_name: str) -> str:
    return f'''# Auto-generated basic tests
import unittest
import importlib

class BasicTests(unittest.TestCase):
    def test_import(self):
        m = importlib.import_module("{module_name}")
        self.assertIsNotNone(m)

    def test_has_public_names(self):
        m = importlib.import_module("{module_name}")
        public = [n for n in dir(m) if not n.startswith("_")]
        self.assertGreaterEqual(len(public), 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


def run_basic_unit_test(program_path: Path, timeout_sec: int) -> Dict[str, Any]:
    """
    Runs a minimal unit test in a temporary folder.
    WARNING: Importing the module executes its top-level code.
    """
    with tempfile.TemporaryDirectory(prefix="program_tester_") as td:
        tdir = Path(td)
        module_name = "target_module"
        target = tdir / f"{module_name}.py"
        shutil.copy2(program_path, target)

        test_file = tdir / "test_basic.py"
        test_file.write_text(generate_basic_test(module_name), encoding="utf-8")

        cmd1 = [sys.executable, "-I", "-m", "unittest", "discover", "-v"]
        r1 = safe_run(cmd1, cwd=tdir, timeout_sec=timeout_sec)

        if (not r1.ok) and ("ModuleNotFoundError" in (r1.stderr + r1.stdout)):
            cmd2 = [sys.executable, "-m", "unittest", "discover", "-v"]
            r2 = safe_run(cmd2, cwd=tdir, timeout_sec=timeout_sec)
            used_cmd = cmd2
            rr = r2
        else:
            used_cmd = cmd1
            rr = r1

        return {
            "ok": rr.ok,
            "returncode": rr.returncode,
            "seconds": round(rr.seconds, 3),
            "timed_out": rr.timed_out,
            "command": used_cmd,
            "stdout": rr.stdout[-20000:],
            "stderr": rr.stderr[-20000:],
        }


def verdict(static_rep: Dict[str, Any], test_rep: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    score = 100
    notes: List[str] = []

    if not static_rep["syntax"]["ok"]:
        score -= 80
        notes.append("Syntax error: the file does not compile.")

    style_counts = static_rep["style"]["counts"]
    if style_counts.get("mixed_indentation"):
        score -= 10
        notes.append("Mixed indentation (tabs + spaces).")

    ll = style_counts.get("long_lines_gt_100", 0)
    if ll:
        score -= min(10, ll // 10 + 1)
        notes.append(f"{ll} long lines (> 100 chars).")

    risky = static_rep["risky_patterns"]["flags"]
    if risky:
        score -= min(25, 5 * len(risky))
        notes.append(f"Risky patterns detected: {len(risky)} hit(s).")

    if static_rep["ast"].get("ok"):
        ds = static_rep["ast"]["docstrings_naming"]
        if not ds.get("module_has_docstring", False):
            score -= 5
            notes.append("Missing module docstring.")
        mfd = ds.get("missing_function_docstrings", 0)
        if mfd:
            score -= min(10, mfd)
            notes.append(f"{mfd} function(s) missing docstrings.")
        naming_issues = ds.get("naming_issues", [])
        if naming_issues:
            score -= min(10, len(naming_issues))
            notes.append(f"Naming convention issues: {len(naming_issues)} item(s).")

    if test_rep is not None:
        if not test_rep.get("ok", False):
            score -= 30
            notes.append("Unit test failed (or crashed).")
        if test_rep.get("timed_out"):
            score -= 20
            notes.append("Unit test timed out.")

    score = max(0, min(100, score))
    level = "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 55 else "Poor"
    return {"score": score, "level": level, "notes": notes}


# ----------------------------
# App Info (English-only, simpler)
# ----------------------------

ABOUT_TEXT = """Program Info

What this app does:
- Upload one Python (.py) file
- Check the code for common issues (syntax, style, documentation, naming)
- Run a basic unit test with a timeout

What the unit test does:
- Imports your file (so it must load without errors)
- Checks your file has at least one public name

Warning:
- Importing a Python file runs its top-level code
- Do not test untrusted files unless you use a safe sandbox

Developer: Abdulrahman Hijazi
"""


# ----------------------------
# Icon (generated in code)
# ----------------------------

def build_icon_image() -> tk.PhotoImage:
    """
    Generates a simple icon (no external files).
    It looks like a dark square with an accent border and 'PT' blocks.
    """
    w, h = 64, 64
    img = tk.PhotoImage(width=w, height=h)

    # Background
    img.put(BG, to=(0, 0, w, h))

    # Border
    b = 4
    img.put(ACCENT, to=(0, 0, w, b))
    img.put(ACCENT, to=(0, h - b, w, h))
    img.put(ACCENT, to=(0, 0, b, h))
    img.put(ACCENT, to=(w - b, 0, w, h))

    # Inner card
    img.put(CARD, to=(b, b, w - b, h - b))

    # Draw "P"
    # Vertical bar
    img.put(FG, to=(16, 18, 22, 46))
    # Top bar
    img.put(FG, to=(16, 18, 34, 24))
    # Middle bar
    img.put(FG, to=(16, 30, 34, 36))
    # Right top
    img.put(FG, to=(28, 18, 34, 36))

    # Draw "T"
    # Top bar
    img.put(FG, to=(38, 18, 54, 24))
    # Stem
    img.put(FG, to=(44, 18, 48, 46))

    return img


def set_app_icon(root: tk.Tk) -> None:
    """
    Sets a custom icon.
    If 'program_tester.ico' exists next to the script on Windows, it will use it.
    Otherwise it uses a generated PhotoImage icon.
    """
    # Try .ico on Windows if available
    try:
        if sys.platform.startswith("win"):
            ico_path = Path(__file__).with_name("program_tester.ico")
            if ico_path.exists():
                root.iconbitmap(default=str(ico_path))
                return
    except Exception:
        pass

    # Fallback: generated icon
    try:
        icon_img = build_icon_image()
        root.iconphoto(True, icon_img)
        root._program_tester_icon = icon_img  # keep reference
    except Exception:
        pass


# ----------------------------
# GUI
# ----------------------------

class ProgramTesterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Program Tester")
        self.root.minsize(980, 680)
        self.root.configure(bg=BG)

        self.program_path: Optional[Path] = None
        self.is_running = False

        self._setup_theme()
        self._build_ui()

    def _setup_theme(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        default_font = ("Segoe UI", 10)
        style.configure(".", font=default_font)

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, bordercolor=BORDER, padding=14)
        style.configure("Header.TFrame", background=BG)
        style.configure("Footer.TFrame", background=BG)

        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), background=BG, foreground=FG)
        style.configure("Sub.TLabel", background=BG, foreground=MUTED)
        style.configure("CardLabel.TLabel", background=CARD, foreground=FG)
        style.configure("Status.TLabel", font=("Segoe UI", 9), background=BG, foreground=MUTED)

        style.configure(
            "Accent.TButton",
            padding=(14, 10),
            background=ACCENT,
            foreground="white",
            borderwidth=0,
            focusthickness=0
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_HOVER), ("disabled", "#2B2B2B")],
            foreground=[("disabled", "#888888")]
        )

        style.configure(
            "Ghost.TButton",
            padding=(14, 10),
            background=BTN_GHOST,
            foreground=FG,
            borderwidth=0,
            focusthickness=0
        )
        style.map(
            "Ghost.TButton",
            background=[("active", BTN_GHOST_HOVER), ("disabled", "#2B2B2B")],
            foreground=[("disabled", "#888888")]
        )

        style.configure("TProgressbar", troughcolor=BTN_GHOST, background=ACCENT)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16, style="TFrame")
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="Header.TFrame")
        header.pack(fill="x")

        ttk.Label(header, text="Program Tester", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Upload a Python file, then test it quickly.",
            style="Sub.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        card = ttk.Frame(container, style="Card.TFrame")
        card.pack(fill="x", pady=(14, 10))

        self.file_label = ttk.Label(card, text="No code file selected.", style="CardLabel.TLabel")
        self.file_label.pack(anchor="w")

        btn_row = ttk.Frame(container, style="TFrame")
        btn_row.pack(fill="x", pady=(6, 10))

        self.btn_upload = ttk.Button(btn_row, text="Upload Code", style="Accent.TButton", command=self.on_upload)
        self.btn_upload.pack(side="left")

        self.btn_test = ttk.Button(btn_row, text="Test Program", style="Accent.TButton", command=self.on_test, state="disabled")
        self.btn_test.pack(side="left", padx=(10, 0))

        self.btn_info = ttk.Button(btn_row, text="Program Info", style="Ghost.TButton", command=self.on_info)
        self.btn_info.pack(side="left", padx=(10, 0))

        out_card = ttk.Frame(container, style="Card.TFrame")
        out_card.pack(fill="both", expand=True)

        self.output = ScrolledText(
            out_card,
            wrap="word",
            font=("Consolas", 10),
            height=18,
            bg=TEXT_BG,
            fg=TEXT_FG,
            insertbackground=TEXT_INSERT,
            selectbackground=TEXT_SEL,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )
        self.output.pack(fill="both", expand=True)

        footer = ttk.Frame(container, style="Footer.TFrame")
        footer.pack(fill="x", pady=(10, 0))

        self.progress = ttk.Progressbar(footer, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True)

        self.status = ttk.Label(footer, text="Ready.", style="Status.TLabel")
        self.status.pack(side="right", padx=(10, 0))

        self._log("Ready. Upload a Python file to begin.\n")

    def _log(self, text: str) -> None:
        self.output.insert("end", text)
        self.output.see("end")

    def _set_running(self, running: bool) -> None:
        self.is_running = running
        if running:
            self.btn_upload.config(state="disabled")
            self.btn_test.config(state="disabled")
            self.btn_info.config(state="disabled")
            self.progress.start(12)
            self.status.config(text="Running...")
        else:
            self.btn_upload.config(state="normal")
            self.btn_info.config(state="normal")
            self.btn_test.config(state="normal" if self.program_path else "disabled")
            self.progress.stop()
            self.status.config(text="Ready.")

    def on_upload(self) -> None:
        fp = filedialog.askopenfilename(
            title="Select a Python file",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")],
        )
        if not fp:
            return
        self.program_path = Path(fp)
        self.file_label.config(text=f"Selected: {self.program_path}")
        self.btn_test.config(state="normal")
        self._log(f"\nSelected file:\n  {self.program_path}\n")

    def on_info(self) -> None:
        messagebox.showinfo("Program Info", ABOUT_TEXT)

    def on_test(self) -> None:
        if not self.program_path or not self.program_path.exists():
            messagebox.showerror("Error", "Please upload a valid .py file first.")
            return
        if self.is_running:
            return

        self._set_running(True)
        self.output.delete("1.0", "end")
        self._log("Testing started.\n\n")

        t = threading.Thread(target=self._run_checks_thread, daemon=True)
        t.start()

    def _run_checks_thread(self) -> None:
        try:
            program = self.program_path
            assert program is not None

            static_rep = static_analysis(program)
            test_rep: Optional[Dict[str, Any]] = None

            if static_rep["syntax"]["ok"]:
                test_rep = run_basic_unit_test(program, timeout_sec=20)

            v = verdict(static_rep, test_rep)

            self.root.after(0, lambda: self._render_report(static_rep, test_rep, v))

        except Exception as e:
            self.root.after(0, lambda: self._log(f"\nUnexpected error:\n{e}\n"))
            self.root.after(0, lambda: self._set_running(False))

    def _render_report(self, static_rep: Dict[str, Any], test_rep: Optional[Dict[str, Any]], v: Dict[str, Any]) -> None:
        self._log("=== Summary ===\n")
        self._log(f"Score: {v['score']}   Level: {v['level']}\n")
        if v["notes"]:
            self._log("Notes:\n")
            for n in v["notes"]:
                self._log(f"  - {n}\n")
        else:
            self._log("Notes:\n  - No major issues detected.\n")

        self._log("\n=== Static Checks (no execution) ===\n")
        syn = static_rep["syntax"]
        self._log(f"Syntax OK: {syn['ok']}\n")
        if not syn["ok"]:
            err = syn["error"]
            self._log(f"  Error: {err['type']} at line {err['lineno']}, col {err['offset']}\n")
            self._log(f"  Message: {err['msg']}\n")
            if err.get("text"):
                self._log(f"  Line: {err['text']}\n")

        style = static_rep["style"]["counts"]
        self._log("\nStyle:\n")
        self._log(f"  Total lines: {style['total_lines']}\n")
        self._log(f"  Long lines (>100): {style['long_lines_gt_100']}\n")
        self._log(f"  Trailing whitespace lines: {style['trailing_whitespace_lines']}\n")
        self._log(f"  Lines containing tab characters: {style['tab_char_lines']}\n")
        self._log(f"  Mixed indentation: {bool(style['mixed_indentation'])}\n")

        comm = static_rep["comments"]
        self._log("\nDocumentation:\n")
        self._log(f"  Comment lines: {comm['comment_lines']}\n")
        self._log(f"  Comment density: {comm['comment_density']}\n")

        self._log("\nAST Checks:\n")
        if static_rep["ast"].get("ok"):
            ds = static_rep["ast"]["docstrings_naming"]
            self._log(f"  Module docstring: {ds['module_has_docstring']} (len={ds['module_docstring_length']})\n")
            self._log(f"  Missing function docstrings: {ds['missing_function_docstrings']}\n")
            self._log(f"  Missing class docstrings: {ds['missing_class_docstrings']}\n")

            naming_issues = ds.get("naming_issues", [])
            self._log(f"  Naming issues: {len(naming_issues)}\n")
            for it in naming_issues[:10]:
                self._log(f"    - {it['type']} '{it['name']}' (line {it['lineno']})\n")

            top5 = static_rep["ast"].get("complexity_top5", [])
            self._log("\n  Complexity (top 5 functions):\n")
            if top5:
                for fn in top5:
                    self._log(f"    - {fn['name']} (line {fn['lineno']}): complexity ~ {fn['complexity']}\n")
            else:
                self._log("    - No functions detected.\n")
        else:
            self._log(f"  AST analysis failed: {static_rep['ast'].get('error')}\n")

        risky = static_rep["risky_patterns"]["flags"]
        self._log("\nRisk Flags:\n")
        if risky:
            for r in risky:
                self._log(f"  - {r['detail']} (pattern: {r['pattern']})\n")
        else:
            self._log("  - None detected.\n")

        self._log("\n=== Unit Test (imports your file) ===\n")
        if test_rep is None:
            self._log("Skipped (syntax was not OK).\n")
        else:
            self._log(f"OK: {test_rep['ok']}\n")
            self._log(f"Return code: {test_rep['returncode']}\n")
            self._log(f"Seconds: {test_rep['seconds']}\n")
            self._log(f"Timed out: {test_rep['timed_out']}\n")
            self._log("\nOutput (tail):\n")
            if test_rep.get("stdout"):
                self._log("--- stdout ---\n")
                self._log(test_rep["stdout"] + "\n")
            if test_rep.get("stderr"):
                self._log("--- stderr ---\n")
                self._log(test_rep["stderr"] + "\n")

        self._log("\nDone.\n")
        self._set_running(False)


def main() -> None:
    root = tk.Tk()

    try:
        if sys.platform.startswith("win"):
            root.tk.call("tk", "scaling", 1.2)
    except Exception:
        pass

    set_app_icon(root)

    ProgramTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
