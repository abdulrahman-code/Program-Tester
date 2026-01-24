# Developed by Abdelrahman Hgazy
import math
import re
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ScientificCalculator(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Scientific Calculator")
        self.geometry("430x640")
        self.resizable(False, False)

        self.use_degrees = True  # degrees by default
        self.expr = ""

        # ===== Display =====
        self.display = ctk.CTkEntry(
            self,
            height=70,
            corner_radius=14,
            font=("Segoe UI", 26, "bold"),
            justify="right"
        )
        self.display.pack(padx=16, pady=(16, 10), fill="x")
        self.display.insert(0, "0")

        # ===== Small status row =====
        self.status = ctk.CTkLabel(
            self,
            text="DEG",
            font=("Segoe UI", 12, "bold"),
            text_color="#9aa0a6"
        )
        self.status.pack(padx=18, anchor="w")

        # ===== Buttons frame =====
        self.grid_frame = ctk.CTkFrame(self, corner_radius=16)
        self.grid_frame.pack(padx=16, pady=12, fill="both", expand=True)

        # Layout buttons
        self.create_buttons()

    # ==========================
    # UI helpers
    # ==========================
    def set_display(self, text: str):
        self.display.delete(0, "end")
        self.display.insert(0, text)

    def append(self, s: str):
        current = self.display.get()
        if current == "0" and s.isdigit():
            self.expr = s
        else:
            self.expr += s
        self.set_display(self.expr if self.expr else "0")

    def clear_all(self):
        self.expr = ""
        self.set_display("0")

    def backspace(self):
        self.expr = self.expr[:-1]
        self.set_display(self.expr if self.expr else "0")

    def toggle_sign(self):
        if not self.expr:
            self.expr = "-"
            self.set_display(self.expr)
            return

        # flip last number sign
        m = re.search(r"(\d+(\.\d+)?)$", self.expr)
        if not m:
            return

        start = m.start()
        if start > 0 and self.expr[start - 1] == '-' and (start - 2 < 0 or self.expr[start - 2] in "+-*/(^"):
            self.expr = self.expr[:start - 1] + self.expr[start:]
        else:
            self.expr = self.expr[:start] + "-" + self.expr[start:]
        self.set_display(self.expr)

    def toggle_deg_rad(self):
        self.use_degrees = not self.use_degrees
        self.status.configure(text="DEG" if self.use_degrees else "RAD")

    # ==========================
    # Math engine
    # ==========================
    def to_radians(self, x):
        return math.radians(x) if self.use_degrees else x

    def preprocess(self, s: str) -> str:
        # Replace symbols
        s = s.replace("×", "*").replace("÷", "/")
        s = s.replace("π", str(math.pi)).replace("e", str(math.e))

        # √x or √( ... ) -> sqrt(...)
        s = re.sub(r"√\s*(\d+(\.\d+)?|\([^\)]+\))", r"sqrt(\1)", s)

        # Convert ^ into pow(a,b) (simple iterative approach)
        s = self.convert_power_to_pow(s)
        return s

    def convert_power_to_pow(self, s: str) -> str:
        while "^" in s:
            idx = s.find("^")

            # left operand
            left_end = idx - 1
            if left_end < 0:
                break

            if s[left_end] == ")":
                # find matching '('
                depth = 0
                left_start = left_end
                for i in range(left_end, -1, -1):
                    if s[i] == ")":
                        depth += 1
                    elif s[i] == "(":
                        depth -= 1
                    if depth == 0:
                        left_start = i
                        break
            else:
                left_start = left_end
                while left_start >= 0 and (s[left_start].isdigit() or s[left_start] in ".-"):
                    left_start -= 1
                left_start += 1

            # right operand
            right_start = idx + 1
            if right_start >= len(s):
                break

            if s[right_start] == "(":
                depth = 0
                right_end = right_start
                for i in range(right_start, len(s)):
                    if s[i] == "(":
                        depth += 1
                    elif s[i] == ")":
                        depth -= 1
                    if depth == 0:
                        right_end = i
                        break
            else:
                right_end = right_start
                while right_end < len(s) and (s[right_end].isdigit() or s[right_end] in ".-"):
                    right_end += 1
                right_end -= 1

            left = s[left_start:left_end + 1]
            right = s[right_start:right_end + 1]

            s = s[:left_start] + f"pow({left},{right})" + s[right_end + 1:]
        return s

    def split_top_level_comma(self, inside: str):
        parts = []
        depth = 0
        start = 0
        for i, ch in enumerate(inside):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(inside[start:i].strip())
                start = i + 1
        parts.append(inside[start:].strip())
        return parts

    def eval_expr(self, s: str) -> float:
        s = self.preprocess(s)

        # Allowed functions (safe-ish dictionary)
        def sin(x): return math.sin(self.to_radians(x))
        def cos(x): return math.cos(self.to_radians(x))
        def tan(x): return math.tan(self.to_radians(x))
        def log(x): return math.log10(x)
        def ln(x): return math.log(x)
        def sqrt(x): return math.sqrt(x)
        def pow_(a, b): return math.pow(a, b)

        # Convert pow(...) to pow_(...) because pow name conflicts with built-in
        s = s.replace("pow(", "pow_(")

        allowed = {
            "sin": sin,
            "cos": cos,
            "tan": tan,
            "log": log,
            "ln": ln,
            "sqrt": sqrt,
            "pow_": pow_,
            "__builtins__": {}
        }

        # Validate characters (basic filter)
        if not re.fullmatch(r"[0-9\.\+\-\*\/\(\),\s_a-zA-Z]+", s):
            raise ValueError("Invalid characters")

        return float(eval(s, allowed, {}))

    def calculate(self):
        try:
            if not self.expr:
                return
            result = self.eval_expr(self.expr)
            # Format nicely
            if abs(result - int(result)) < 1e-12:
                result_str = str(int(result))
            else:
                result_str = f"{result:.12g}"
            self.expr = result_str
            self.set_display(result_str)
        except Exception:
            self.set_display("Error")
            self.expr = ""

    # ==========================
    # Buttons
    # ==========================
    def btn(self, text, row, col, cmd, colspan=1, fg=None):
        b = ctk.CTkButton(
            self.grid_frame,
            text=text,
            height=55,
            corner_radius=14,
            font=("Segoe UI", 16, "bold"),
            command=cmd,
            fg_color=fg
        )
        b.grid(row=row, column=col, columnspan=colspan, padx=6, pady=6, sticky="nsew")

    def create_buttons(self):
        # Configure grid
        for c in range(5):
            self.grid_frame.grid_columnconfigure(c, weight=1)
        for r in range(7):
            self.grid_frame.grid_rowconfigure(r, weight=1)

        # Row 0
        self.btn("DEG/RAD", 0, 0, self.toggle_deg_rad, fg="#2b2f36")
        self.btn("(", 0, 1, lambda: self.append("("), fg="#2b2f36")
        self.btn(")", 0, 2, lambda: self.append(")"), fg="#2b2f36")
        self.btn("⌫", 0, 3, self.backspace, fg="#2b2f36")
        self.btn("C", 0, 4, self.clear_all, fg="#7a2e2e")

        # Row 1
        self.btn("sin", 1, 0, lambda: self.append("sin("), fg="#2b2f36")
        self.btn("cos", 1, 1, lambda: self.append("cos("), fg="#2b2f36")
        self.btn("tan", 1, 2, lambda: self.append("tan("), fg="#2b2f36")
        self.btn("log", 1, 3, lambda: self.append("log("), fg="#2b2f36")
        self.btn("ln", 1, 4, lambda: self.append("ln("), fg="#2b2f36")

        # Row 2
        self.btn("√", 2, 0, lambda: self.append("√("), fg="#2b2f36")
        self.btn("^", 2, 1, lambda: self.append("^"), fg="#2b2f36")
        self.btn("π", 2, 2, lambda: self.append("π"), fg="#2b2f36")
        self.btn("e", 2, 3, lambda: self.append("e"), fg="#2b2f36")
        self.btn("÷", 2, 4, lambda: self.append("÷"), fg="#3a3f47")

        # Row 3
        self.btn("7", 3, 0, lambda: self.append("7"))
        self.btn("8", 3, 1, lambda: self.append("8"))
        self.btn("9", 3, 2, lambda: self.append("9"))
        self.btn("×", 3, 3, lambda: self.append("×"), fg="#3a3f47")
        self.btn("±", 3, 4, self.toggle_sign, fg="#2b2f36")

        # Row 4
        self.btn("4", 4, 0, lambda: self.append("4"))
        self.btn("5", 4, 1, lambda: self.append("5"))
        self.btn("6", 4, 2, lambda: self.append("6"))
        self.btn("-", 4, 3, lambda: self.append("-"), fg="#3a3f47")
        self.btn("%", 4, 4, lambda: self.append("/100"), fg="#2b2f36")

        # Row 5
        self.btn("1", 5, 0, lambda: self.append("1"))
        self.btn("2", 5, 1, lambda: self.append("2"))
        self.btn("3", 5, 2, lambda: self.append("3"))
        self.btn("+", 5, 3, lambda: self.append("+"), fg="#3a3f47")
        self.btn("=", 5, 4, self.calculate, fg="#1f6aa5")

        # Row 6
        self.btn("0", 6, 0, lambda: self.append("0"), colspan=2)
        self.btn(".", 6, 2, lambda: self.append("."))
        self.btn("(", 6, 3, lambda: self.append("("), fg="#2b2f36")
        self.btn(")", 6, 4, lambda: self.append(")"), fg="#2b2f36")


if __name__ == "__main__":
    app = ScientificCalculator()
    app.mainloop()
