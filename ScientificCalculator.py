# Developed by Abdelrahman Hgazy (patched)
import math
import re
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ScientificCalculator(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 
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

        self.create_buttons()

    # ==========================
    # UI helpers
    # ==========================
    def set_display(self, text: str):
        self.display.delete(0, "end")
        self.display.insert(0, text)

    def append(self, s: str):
        # لو كان في Error وبدأت تكتب، نبدأ من جديد
        if self.display.get() == "Error":
            self.expr = ""

        ops_display = {"×": "*", "÷": "/"}
        s_norm = ops_display.get(s, s)

        # منع بدء التعبير بعوامل لا معنى لها
        if not self.expr:
            if s_norm in "+*/)^":
                return
            if s_norm == ".":
                self.expr = "0."
                self.set_display(self.expr)
                return

        # لو آخر شيء عامل حسابي وجاء عامل حسابي ثاني، استبدله
        ops = set("+-*/")
        if self.expr and self.expr[-1] in ops and s_norm in ops:
            # اسمح بـ 5*-2
            if s_norm == "-" and self.expr[-1] in "*/":
                self.expr += s_norm
            else:
                self.expr = self.expr[:-1] + s_norm
            self.set_display(self.expr)
            return

        # معالجة "0" الافتراضي
        current = self.display.get()
        if current == "0" and s_norm.isdigit() and not self.expr:
            self.expr = s_norm
        else:
            self.expr += s_norm

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
        # رموز العمليات
        s = s.replace("×", "*").replace("÷", "/")

        # π -> pi (اسم ثابت داخل allowed)
        s = s.replace("π", "pi")

        # e ثابت أو 1e-3؟
        # نبدل "e" فقط لو كانت وحدها كرمز ثابت (لا يسبقها رقم)
        s = re.sub(r"(?<![0-9])e(?![A-Za-z0-9_])", "E", s)

        # √( ... ) -> sqrt( ... )
        s = s.replace("√(", "sqrt(")

        # √number أو √pi أو √E -> sqrt(...)
        s = re.sub(r"√\s*([0-9]+(\.[0-9]+)?|pi|E)", r"sqrt(\1)", s)

        # ^ -> ** (أسهل وأصح في بايثون)
        s = s.replace("^", "**")

        # ضرب ضمني:
        # 2(3+4) -> 2*(3+4)
        s = re.sub(r"(\d|\)|pi|E)\s*(?=\()", r"\1*", s)
        # 2pi -> 2*pi ، )pi -> )*pi
        s = re.sub(r"(\d|\))\s*(?=pi|E)", r"\1*", s)
        # pi2 -> pi*2 ، E2 -> E*2 ، )( -> )*(
        s = re.sub(r"(pi|E)\s*(?=\d|\()", r"\1*", s)
        s = re.sub(r"(\))\s*(?=\d)", r"\1*", s)

        # رقم وبعده دالة: 2sin(30) -> 2*sin(30)
        s = re.sub(r"(\d|\)|pi|E)\s*(?=(sin|cos|tan|log|ln|sqrt)\()", r"\1*", s)

        return s

    def eval_expr(self, s: str) -> float:
        s = self.preprocess(s)

        def sin(x): return math.sin(self.to_radians(x))
        def cos(x): return math.cos(self.to_radians(x))
        def tan(x): return math.tan(self.to_radians(x))
        def log(x): return math.log10(x)
        def ln(x): return math.log(x)
        def sqrt(x): return math.sqrt(x)

        allowed = {
            "sin": sin,
            "cos": cos,
            "tan": tan,
            "log": log,
            "ln": ln,
            "sqrt": sqrt,
            "pi": math.pi,
            "E": math.e,
            "__builtins__": {}
        }

        if not re.fullmatch(r"[0-9\.\+\-\*\/\(\),\sA-Za-z_]+", s):
            raise ValueError("Invalid characters")

        return float(eval(s, allowed, {}))

    def calculate(self):
        try:
            if not self.expr:
                return
            result = self.eval_expr(self.expr)
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
        self.btn("%", 4, 4, lambda: self.append("*0.01"), fg="#2b2f36")

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
