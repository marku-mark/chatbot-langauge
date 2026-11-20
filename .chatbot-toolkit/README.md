# Battlefront chatbot development toolkit

This toolkit helps trace the guest gateway and prepare offline language evaluations. FastAPI forwards messages to the sibling Laravel app, where routing, language selection, authorization, and the evaluator live.

## Graphify

From the chatbot-language checkout, use Graphify 0.9.102 or a compatible version:

```powershell
graphify update . --no-cluster
graphify cluster-only . --no-label
graphify query 'chatbot test_chatbot_forwards_the_message_and_context_as_a_guest'
graphify query 'ChatbotLanguage EvaluateChatbot' --graph ../battlefront-capstone/graphify-out/graph.json
```

Run the first two commands again after source changes. They build the local code graph and HTML without model labeling. The scan includes `app/`, `tests/`, and the evaluator and its tests in `.chatbot-toolkit/`. Keep the sibling capstone graph separate.

## Offline evaluation

From chatbot-language in PowerShell, with the project virtual environment and a prepared local capstone database:

```powershell
$toolkit = (Resolve-Path .chatbot-toolkit).Path
$python = (Resolve-Path .venv/Scripts/python.exe).Path
$dataset = Join-Path $toolkit 'cases.json'
$report = Join-Path ([System.IO.Path]::GetTempPath()) ("battlefront-chatbot-offline-" + [guid]::NewGuid() + ".json")
& $python "$toolkit/evaluate.py" validate $dataset
if ($LASTEXITCODE -ne 0) { throw "Fix the dataset before evaluating." }

Push-Location ../battlefront-capstone
try {
    php artisan chatbot:evaluate --no-interaction --no-ansi --dataset=$dataset |
        Set-Content -LiteralPath $report -Encoding UTF8
    $evaluationExit = $LASTEXITCODE
} finally {
    Pop-Location
}
& $python "$toolkit/evaluate.py" summarize $report
Write-Output "Laravel exit $evaluationExit. Local report: $report"
```

Laravel can emit a valid report and exit 1 when a case fails. Read the summary and inspect failed checks by case ID. The summary's exit status describes whether it read a valid report. The JSON summary carries the actual case verdicts.

The validator supports `id`, `language`, `messages`, and optional `expected_category`, `expected_clarification`, `family`, and `split`. Write only synthetic public messages and use `en`, `tl`, `ceb`, or `hil` for the expected final reply. Keep paraphrases of one family in a single split. Laravel still validates the imported cases and owns the evaluation results.

For a handoff, record the capstone revision, dataset hash, case ID, expected language or behavior, failed check, and relevant code path. Use Laravel's hash-bound review format for fluent-speaker judgments of naturalness. The starter cases have provisional language labels and no fluent-speaker sign-off.

The local Codex skills, agent roles, and reference index are checkout-specific. If installed, the research notes are under `references/`.

Run the gateway and helper tests together with `uv run pytest tests .chatbot-toolkit/test_evaluate.py`.
