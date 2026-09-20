import os

import pytest

requires_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set — skipping live-model test"
)


@requires_key
def test_task_extraction_finds_a_task():
    from app.agent.extraction import extract_tasks

    text = "Please send the Q3 report to john@example.com by this Friday, it's urgent."
    tasks = extract_tasks(text)

    assert len(tasks) >= 1
    assert tasks[0]["confidence"] > 0.5
    assert tasks[0]["priority"] in {"high", "medium", "low"}


@requires_key
def test_task_extraction_empty_on_non_actionable_text():
    from app.agent.extraction import extract_tasks

    text = "The sky was a deep shade of blue that afternoon."
    tasks = extract_tasks(text)

    assert tasks == []
