"""The published safety numbers (evals/results/SAFETY.md) must stay true: every planted
mistake caught, every correct draft let through, no unsafe draft reaching a person."""

from evals.eval_safety import main


def test_safety_evals_all_pass():
    assert main() == 0
