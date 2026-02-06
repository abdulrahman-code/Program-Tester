
# Scientific Calculator (CustomTkinter)  
**Unit-Tested Math Engine with a Simple Desktop UI**

---

## Developer
- **Developer:** Abdelrahman Hgazy  
- **Project Owner / Maintainer:** Abdelrahman Hgazy  
- **Copyright:** © Abdelrahman Hgazy

---

## What This Project Is Really About
Despite the UI, the core of this project is a **calculation engine** (the function `eval_expr`) that parses and evaluates expressions like:

- `2*(3+4)`
- `sin(30)`
- `2π`
- `√(9)`
- `log(1000)`

And because engines break in sneaky ways, the project includes a separate, proper **unit testing suite** that verifies correctness and prevents regressions.

The UI is just a front-end.  
The tests are what make this a real project instead of a “works on my laptop” demo.

---

# Unit Testing (Main Focus)

## Why Unit Tests Matter Here
Expression engines usually fail in ways that are not obvious:
- constants interfering with scientific notation (e.g., `1e-3`)
- implicit multiplication not being recognized (e.g., `2π`, `2(3+4)`)
- power operator behavior (`^`)
- DEG vs RAD mode mistakes
- invalid character injection (security and correctness)

Unit tests solve this by making correctness **automatic**:
- if you change the engine code and break something, tests fail instantly
- you know exactly which feature broke
- you avoid shipping silent math bugs

---

## What Exactly Is Being Tested
The tests target **only the math engine**, specifically:

- `eval_expr(expression: str) -> float`

### Tested categories include:

### 1) Basic arithmetic
- `2+3 = 5`
- `8/4 = 2`
- correct operator handling

### 2) Parentheses and precedence
- `2*(3+4)` must equal `14`
- ensures correct evaluation order

### 3) Power and square roots
- `2^3 = 8`
- `√(9) = 3`

### 4) Constants
- `π` returns `math.pi`
- `2π` equals `2 * math.pi`

### 5) Trigonometry (DEG and RAD)
- In DEG mode: `sin(30) = 0.5`
- In RAD mode: `sin(pi/2) = 1`

### 6) Safety and invalid characters
- input like `os.system(...)` must be rejected
- ensures the allowed-character filter is doing its job

---

## How the Tests Avoid Opening the GUI
The calculator UI is built with CustomTkinter, and initializing it normally opens a window.

That’s bad for unit tests.

So the test suite creates an instance of the calculator class without calling its `__init__`:

```python
eng = ScientificCalculator.__new__(ScientificCalculator)
````

This produces the object without triggering GUI setup, then the test sets:

```python
eng.use_degrees = True
```

So tests run:

* fast
* stable
* headless
* no annoying UI popups

---

## Test File (Separate from Calculator Code)

The test suite lives in a dedicated file:

* `test_scientific_calc.py`

It imports the calculator class and tests the engine.

This separation is important:

* Calculator file = production code
* Test file = validation code
* No mixing, no confusion

---

## Running Tests

### Windows

```bat
py -m unittest -v test_scientific_calc.py
```

### macOS / Linux

```bash
python3 -m unittest -v test_scientific_calc.py
```

### Output Meaning

* ✅ `ok` means the test passed
* ❌ `FAIL` means expected result != actual result
* ❌ `ERROR` means the code crashed during the test

If you see `FAIL` or `ERROR`, the output will show:

* which test failed
* what value was expected
* what was returned instead
* traceback and exact failing line

---

## How to Add Your Own Tests (Recommended)

If you add new features, you should add new tests.

### Example: You add `factorial(n)`

You should add a test like:

```python
def test_factorial(self):
    eng = make_engine()
    self.assertAlmostEqual(eng.eval_expr("factorial(5)"), 120.0)
```

Rule of thumb:

* **Every new operation needs at least 2 tests**

  1. a normal case
  2. an edge case (0, negative, big input, invalid input)

---

## Typical Bugs the Tests Will Catch

These are classic expression-engine disasters:

* `1e-3` turning into nonsense because `e` got replaced incorrectly
* `2π` failing because the engine didn’t insert `*`
* `2(3+4)` failing because implicit multiplication wasn’t handled
* `sin(30)` returning the RAD result by mistake
* `^` behaving incorrectly or being parsed wrongly
* invalid characters slipping into `eval`

This is why the test suite exists. Not for decoration.

---

## Recommended Workflow (Professional)

If you’re editing the engine:

1. Make the change
2. Run tests
3. If tests fail, fix engine or update tests
4. Only then run the UI

This is how you build software that doesn’t randomly betray you.

---

# Project Structure

```
CalculatorProject/
  scientific_calc_fixed.py
  test_scientific_calc.py
  README.md
```

* `scientific_calc_fixed.py`
  Main app (UI + engine).
* `test_scientific_calc.py`
  Unit tests (engine validation).
* `README.md`
  Documentation.

---

# Minimal Notes About the Calculator (Less Focus)

The UI is a dark-mode CustomTkinter window that sends expressions to the engine.
It includes buttons for digits, operators, scientific functions, and a DEG/RAD toggle.
The real logic is in `eval_expr`.

---

## Dependencies

* Python 3.10+ recommended
* `customtkinter`

Install:

```bat
py -m pip install customtkinter
```

---

## License

**MIT License (recommended)**
You can use/modify/distribute with attribution to the developer.

---
```

