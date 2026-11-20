import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLKIT = Path(__file__).resolve().parent


def run_helper(command: str, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLKIT / "evaluate.py"), command, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_starter_cases_validate() -> None:
    result = run_helper("validate", TOOLKIT / "cases.json")

    assert result.returncode == 0
    assert json.loads(result.stdout)["valid_cases"] >= 6


@pytest.mark.parametrize(
    ("changes", "error"),
    [({}, "duplicate ID"), ({"id": "second", "language": "war"}, "unsupported language")],
)
def test_invalid_cases_are_rejected(tmp_path: Path, changes: dict[str, str], error: str) -> None:
    case = {"id": "first", "language": "en", "messages": ["Where is the store?"]}
    dataset = tmp_path / "cases.json"
    dataset.write_text(json.dumps([case, case | changes]), encoding="utf-8")

    result = run_helper("validate", dataset)

    assert result.returncode == 2
    assert error in result.stderr


def test_offline_summary_retains_failed_checks_and_review_counts(tmp_path: Path) -> None:
    first = {"id": "case", "run": 1, "language": "hil", "passed": True, "human_reviewed": True}
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "mode": "offline",
                "results": [
                    first | {"checks": {"language": True}},
                    first | {"run": 2, "passed": False, "human_reviewed": False, "checks": {"language": False}},
                ],
            }
        ),
        encoding="utf-8-sig",
    )

    result = run_helper("summarize", report)

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "mode": "offline",
        "languages": {"hil": {"runs": 2, "passed": 1, "human_reviewed": 1}},
        "failures": [{"id": "case", "run": 2, "language": "hil", "checks": ["language"]}],
    }


@pytest.mark.parametrize(
    "payload",
    ['{"mode":"offline","results":[{}]}', '{"mode":"live","results":[]}', "not JSON"],
)
def test_malformed_or_live_report_is_rejected(tmp_path: Path, payload: str) -> None:
    report = tmp_path / "report.json"
    report.write_text(payload, encoding="utf-8")

    result = run_helper("summarize", report)

    assert result.returncode == 2
    assert not result.stdout
