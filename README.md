# Program Tester

A simple desktop tool that lets you upload a Python file and quickly test it using **static checks** and a **basic unit test**.  
Yes, it is basically a “sanity checker” for code before you pretend it’s perfect.

---

## Features

- **Upload Code**: Select a `.py` file from your computer.
- **Test Program**:
  - **Static checks (no execution)**:
    - Syntax check (does the file compile?)
    - Style hints (long lines, trailing whitespace, mixed indentation)
    - Documentation checks (module/function/class docstrings)
    - Naming checks (snake_case for functions, PascalCase for classes)
    - Complexity estimate (rough indicator)
    - Risky pattern flags (e.g., `eval`, `exec`, `os.system`, etc.)
  - **Unit test (executes import)**:
    - Imports the uploaded module
    - Confirms it loads without crashing
    - Confirms it has at least one public name (function/class/variable)
- **Program Info**: Shows what the app does in plain English.

---

## Important Security Warning

When Python **imports** a file, it can execute code at the top level of that file.

That means:
- If you test an untrusted file, it could do harmful actions (delete files, run commands, etc.).
- **Only test code you trust**, or run this app inside a sandbox/VM/container.

---

## Requirements

- Python 3.9+ (recommended)
- No external libraries (Standard Library only)

---

## How to Run

1. Download or copy `program_tester.py`
2. Open a terminal in the same folder
3. Run:

```bash
python program_tester.py
```
---
Developed by Abdelrahman Hgazy



