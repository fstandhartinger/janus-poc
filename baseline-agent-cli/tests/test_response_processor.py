"""Tests for response post-processing helpers."""

from __future__ import annotations

from janus_baseline_agent_cli.services.response_processor import (
    process_agent_response,
    resolve_artifact_urls,
)


def test_resolve_artifact_urls_for_markdown_links() -> None:
    content = "Download [report](/artifacts/report.pdf) and ![chart](/artifacts/chart.png)."
    base = "https://sandbox.test/artifacts"
    expected = (
        "Download [report](https://sandbox.test/artifacts/report.pdf) "
        "and ![chart](https://sandbox.test/artifacts/chart.png)."
    )

    assert resolve_artifact_urls(content, base) == expected


def test_process_agent_response_skips_without_sandbox_url() -> None:
    content = "[report](/artifacts/report.pdf)"

    assert process_agent_response(content, None) == content
