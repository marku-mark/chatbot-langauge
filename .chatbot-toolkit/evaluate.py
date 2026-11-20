"""Validate synthetic Battlefront cases and summarize offline Laravel reports."""

import argparse
import json
from pathlib import Path

LANGUAGES = {"en", "tl", "ceb", "hil"}
SPLITS = {"development", "held_out"}
CATEGORIES = {"product", "store", "order", "faq", "unsupported"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text_within(value, limit):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def validate(cases):
    require(isinstance(cases, list) and 1 <= len(cases) <= 1000, "Expected an array of 1 to 1000 cases.")
    ids = set()
    family_splits = {}
    fields = {"id", "language", "messages", "expected_category", "expected_clarification", "family", "split"}
    for index, case in enumerate(cases, 1):
        label = f"Case {index}"
        require(isinstance(case, dict) and case.keys() <= fields, f"{label}: unsupported case fields.")
        case_id = case.get("id")
        require(text_within(case_id, 100) and case_id not in ids, f"{label}: missing, invalid, or duplicate ID.")
        ids.add(case_id)
        language = case.get("language")
        require(isinstance(language, str) and language in LANGUAGES, f"{label}: unsupported language.")
        messages = case.get("messages")
        require(
            isinstance(messages, list) and 1 <= len(messages) <= 10 and all(text_within(m, 1000) for m in messages),
            f"{label}: expected 1 to 10 nonblank messages, each at most 1000 characters.",
        )
        if "expected_category" in case:
            category = case["expected_category"]
            require(isinstance(category, str) and category in CATEGORIES, f"{label}: unsupported category.")
        if "expected_clarification" in case:
            require(isinstance(case["expected_clarification"], bool), f"{label}: clarification label must be boolean.")
        if "split" in case:
            split = case["split"]
            require(isinstance(split, str) and split in SPLITS, f"{label}: unsupported split.")
        if "family" in case:
            family = case["family"]
            require(
                text_within(family, 100)
                and family.isascii()
                and all(char.isalnum() or char in "_.-" for char in family),
                f"{label}: invalid family.",
            )
            if "split" in case:
                require(
                    family_splits.setdefault(family, case["split"]) == case["split"],
                    f"{label}: conversation family crosses splits.",
                )
    return len(cases)


def summarize(report):
    require(isinstance(report, dict) and report.get("mode") == "offline", "Expected an offline evaluator report.")
    results = report.get("results")
    require(isinstance(results, list) and bool(results), "Expected a nonempty results array.")
    counts = {}
    failures = []
    seen = set()
    for index, result in enumerate(results, 1):
        error = f"Result {index}: malformed evaluator result."
        require(isinstance(result, dict), error)
        case_id, run, language = (result.get(key) for key in ("id", "run", "language"))
        require(text_within(case_id, 100) and type(run) is int and 1 <= run <= 3, error)
        require(isinstance(language, str) and language in LANGUAGES, error)
        require((case_id, run) not in seen, f"Result {index}: duplicate case and run.")
        seen.add((case_id, run))
        passed, reviewed, checks = (result.get(key) for key in ("passed", "human_reviewed", "checks"))
        require(
            isinstance(passed, bool)
            and isinstance(reviewed, bool)
            and isinstance(checks, dict)
            and bool(checks)
            and all(check is None or isinstance(check, bool) for check in checks.values()),
            error,
        )
        failed_checks = [name for name, check in checks.items() if check is False]
        require(passed == (not failed_checks), f"Result {index}: case verdict disagrees with checks.")
        row = counts.setdefault(language, {"runs": 0, "passed": 0, "human_reviewed": 0})
        row["runs"] += 1
        row["passed"] += passed
        row["human_reviewed"] += reviewed
        if failed_checks:
            failures.append({"id": case_id, "run": run, "language": language, "checks": failed_checks})
    return {"mode": "offline", "languages": counts, "failures": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "summarize"])
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = {"valid_cases": validate(payload)} if args.command == "validate" else summarize(payload)
    except json.JSONDecodeError as error:
        parser.exit(2, f"Invalid JSON at line {error.lineno}, column {error.colno}.\n")
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
