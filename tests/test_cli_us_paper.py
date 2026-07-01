import argparse
import io
import unittest

from backtester.cli.us_paper import dispatch_us_paper_command


class UsPaperCliDispatchTests(unittest.TestCase):
    def test_dispatches_known_command_to_handler(self):
        calls = []
        args = argparse.Namespace(command="auto-paper-run")

        result = dispatch_us_paper_command(
            args,
            handlers={"auto-paper-run": lambda received: calls.append(received) or 0},
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [args])

    def test_returns_none_for_non_us_paper_command(self):
        result = dispatch_us_paper_command(argparse.Namespace(command="compare"), handlers={})

        self.assertIsNone(result)

    def test_reports_fail_closed_errors_without_traceback(self):
        stderr = io.StringIO()

        result = dispatch_us_paper_command(
            argparse.Namespace(command="kis-us-paper-plan"),
            handlers={"kis-us-paper-plan": lambda _: (_ for _ in ()).throw(ValueError("bad config"))},
            stderr=stderr,
        )

        self.assertEqual(result, 2)
        self.assertEqual(stderr.getvalue(), "kis_us_paper_plan_error  bad config\n")


if __name__ == "__main__":
    unittest.main()
