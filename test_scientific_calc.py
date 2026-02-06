import unittest
import math

# غيّر الاسم هنا حسب اسم ملف الآلة عندك (بدون .py)
from ScientificCalculator import ScientificCalculator


def make_engine(use_degrees=True) -> ScientificCalculator:
    """
    نصنع كائن من ScientificCalculator بدون تشغيل واجهة customtkinter.
    """
    eng = ScientificCalculator.__new__(ScientificCalculator)
    eng.use_degrees = use_degrees
    return eng


class TestScientificCalculator(unittest.TestCase):

    def test_add_sub(self):
        eng = make_engine()
        self.assertAlmostEqual(eng.eval_expr("2+3"), 5.0)
        self.assertAlmostEqual(eng.eval_expr("10-7"), 3.0)

    def test_mul_div(self):
        eng = make_engine()
        self.assertAlmostEqual(eng.eval_expr("6*7"), 42.0)
        self.assertAlmostEqual(eng.eval_expr("8/4"), 2.0)

    def test_parentheses(self):
        eng = make_engine()
        self.assertAlmostEqual(eng.eval_expr("2*(3+4)"), 14.0)

    def test_power_caret(self):
        eng = make_engine()
        self.assertAlmostEqual(eng.eval_expr("2^3"), 8.0)

    def test_sqrt(self):
        eng = make_engine()
        self.assertAlmostEqual(eng.eval_expr("√(9)"), 3.0)
        self.assertAlmostEqual(eng.eval_expr("sqrt(16)"), 4.0)

    def test_pi_constant(self):
        eng = make_engine()
        self.assertAlmostEqual(eng.eval_expr("π"), math.pi)
        self.assertAlmostEqual(eng.eval_expr("2π"), 2 * math.pi)

    def test_trig_degrees(self):
        eng = make_engine(use_degrees=True)
        self.assertAlmostEqual(eng.eval_expr("sin(30)"), 0.5, places=12)

    def test_trig_radians(self):
        eng = make_engine(use_degrees=False)
        self.assertAlmostEqual(eng.eval_expr("sin(pi/2)"), 1.0, places=12)

    def test_invalid_characters(self):
        eng = make_engine()
        with self.assertRaises(ValueError):
            eng.eval_expr("os.system('rm -rf /')")


if __name__ == "__main__":
    unittest.main(verbosity=2)
