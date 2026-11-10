import unittest

from agent.loop import run_agent
from agent.models import FakeModel
from agent.tools import ToolError, calculator, read_note, run_tool, search_notes, validate


def quiet(_):
    pass


class ToolTests(unittest.TestCase):
    def test_calculator(self):
        self.assertEqual(calculator("(12 + 8) * 3"), "60")
        self.assertEqual(calculator("2400 * 15 / 100"), "360.0")

    def test_calculator_refuses_code(self):
        for bad in ["__import__('os').system('ls')", "open('x')", "2 ** 10000", "1/0", "2 +"]:
            with self.assertRaises(ToolError):
                calculator(bad)

    def test_read_note_stays_in_folder(self):
        self.assertIn("Monday", read_note("meetings.txt"))
        for bad in ["../README.md", "/etc/passwd", "missing.txt"]:
            with self.assertRaises(ToolError):
                read_note(bad)

    def test_search_notes(self):
        self.assertTrue(search_notes("deadline demo").startswith("deadlines.txt"))

    def test_validation(self):
        with self.assertRaises(ToolError):
            validate("shell", {})
        with self.assertRaises(ToolError):
            validate("calculator", {})
        with self.assertRaises(ToolError):
            validate("calculator", {"expression": 5})
        with self.assertRaises(ToolError):
            validate("calculator", {"expression": "1", "extra": 1})
        with self.assertRaises(ToolError):
            validate("calculator", "1+1")
        self.assertEqual(run_tool("calculator", {"expression": "1+1"}), "2")


class LoopTests(unittest.TestCase):
    def test_uses_tool_then_answers(self):
        model = FakeModel([{"tool": "calculator", "args": {"expression": "2400*0.15"}}, {"answer": "360"}])
        self.assertEqual(run_agent("15% of 2400?", model, log=quiet), "360")
        self.assertIn("Tool result from calculator:\n360.0", model.seen[1][-1]["content"])

    def test_bad_call_is_reported_back_not_crashing(self):
        model = FakeModel([{"tool": "delete_everything", "args": {}}, {"answer": "sorry"}])
        self.assertEqual(run_agent("q", model, log=quiet), "sorry")
        self.assertIn("ERROR: unknown tool", model.seen[1][-1]["content"])

    def test_step_limit(self):
        model = FakeModel([{"tool": "search_notes", "args": {"query": "x"}}] * 10)
        reply = run_agent("q", model, max_steps=3, log=quiet)
        self.assertIn("stopped after 3 steps", reply)
        self.assertEqual(len(model.seen), 3)

    def test_multi_tool_question(self):
        model = FakeModel([{"tool": "search_notes", "args": {"query": "demo"}},
                           {"tool": "read_note", "args": {"name": "deadlines.txt"}},
                           {"answer": "The demo is on 18 December."}])
        self.assertIn("18 December", run_agent("When is the demo?", model, log=quiet))


if __name__ == "__main__":
    unittest.main()
