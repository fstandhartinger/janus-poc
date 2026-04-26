"""Static compatibility guard for the cross-repo Sandy integration map."""

from __future__ import annotations

from pathlib import Path


JANUS_ROOT = Path(__file__).resolve().parents[2]
CHUTES_ROOT = JANUS_ROOT.parent


def read_project_file(*parts: str) -> str:
    path = CHUTES_ROOT.joinpath(*parts)
    assert path.exists(), f"Expected file to exist: {path}"
    return path.read_text(encoding="utf-8")


def test_sandy_server_exposes_documented_sandbox_contract() -> None:
    app_source = read_project_file("sandy", "sandy", "app.py")
    controller_source = read_project_file("sandy", "sandy", "controller.py")

    required_app_routes = [
        '@api_app.post("/api/sandboxes")',
        '@api_app.get("/api/sandboxes/{sandbox_id}")',
        '@api_app.post("/api/sandboxes/{sandbox_id}/exec")',
        '@api_app.post("/api/sandboxes/{sandbox_id}/agent/run")',
        '@api_app.post("/api/sandboxes/{sandbox_id}/agent/cancel")',
        '@api_app.post("/api/sandboxes/{sandbox_id}/files/write")',
        '@api_app.get("/api/sandboxes/{sandbox_id}/files/read")',
        '@api_app.get("/api/sandboxes/{sandbox_id}/files/list")',
        '@api_app.post("/api/sandboxes/{sandbox_id}/preview")',
        '@api_app.post("/api/sandboxes/{sandbox_id}/terminate")',
    ]
    for marker in required_app_routes:
        assert marker in app_source

    required_controller_routes = [
        '@controller_api.post("/api/sandboxes")',
        '@controller_api.post("/api/sandboxes/{sandbox_id}/exec")',
        '@controller_api.post("/api/sandboxes/{sandbox_id}/agent/run")',
        '@controller_api.post("/api/sandboxes/{sandbox_id}/files/write")',
        '@controller_api.get("/api/sandboxes/{sandbox_id}/files/read")',
        '@controller_api.get("/api/sandboxes/{sandbox_id}/files/list")',
        '@controller_api.post("/api/sandboxes/{sandbox_id}/terminate")',
    ]
    for marker in required_controller_routes:
        assert marker in controller_source


def test_downstream_clients_still_use_documented_sandy_entrypoints() -> None:
    checks = {
        ("janus-poc", "baseline-agent-cli", "janus_baseline_agent_cli", "services", "sandy.py"): [
            "SANDY_BASE_URL",
            "SANDY_API_KEY",
            "/api/sandboxes",
            "/api/sandboxes/{sandbox_id}/exec",
            "/api/sandboxes/{sandbox_id}/agent/run",
            "/api/sandboxes/{sandbox_id}/files/write",
            "/api/sandboxes/{sandbox_id}/files/read",
            "/api/sandboxes/{sandbox_id}/terminate",
        ],
        ("chutes-search", "src", "lib", "sandy.ts"): [
            "SANDY_BASE_URL",
            "SANDY_API_KEY",
            "/api/sandboxes",
            "/api/sandboxes/${sandboxId}/exec",
            "/api/sandboxes/${sandboxId}/files/write",
            "/api/sandboxes/${sandboxId}/files/read",
            "/api/sandboxes/${sandboxId}/files/list",
            "/api/sandboxes/${sandboxId}/terminate",
        ],
        ("chutes-bench-runner", "backend", "app", "services", "sandy_service.py"): [
            "settings.sandy_base_url",
            "settings.sandy_api_key",
            "/api/sandboxes",
            "/api/sandboxes/{sandbox_id}/exec",
            "/api/sandboxes/{sandbox_id}/agent/run",
            "/api/sandboxes/{sandbox_id}/files/write",
            "/api/sandboxes/{sandbox_id}/terminate",
        ],
        ("agent-as-a-service-web", "script.js"): [
            "routerBase",
            "/api/sandboxes",
            "/api/sandboxes/${state.sandboxId}/agent/run",
            "/api/sandboxes/${state.sandboxId}/files/list",
            "/api/sandboxes/${state.sandboxId}/files/read",
            "/api/sandboxes/${state.sandboxId}/files/write",
            "/api/sandboxes/${state.sandboxId}/terminate",
        ],
        ("chutes-webcoder", "app", "api", "agent-run", "route.ts"): [
            "SANDY_BASE_URL",
            "SANDY_API_KEY",
            "SANDY_AGENT_API_BASE_URL",
            "/api/sandboxes/${sandboxId}/agent/run",
            "janus-router requires",
        ],
        ("chutes-webcoder", "lib", "server", "sandy-proxy.ts"): [
            "SANDY_BASE_URL",
            "SANDY_HOST_SUFFIX",
            "proxySandyRequest",
        ],
    }

    for parts, markers in checks.items():
        source = read_project_file(*parts)
        for marker in markers:
            assert marker in source, f"{'/'.join(parts)} missing {marker}"


def test_agent_run_router_base_and_prompt_safety_guards_are_present() -> None:
    janus_sandy = read_project_file(
        "janus-poc",
        "baseline-agent-cli",
        "janus_baseline_agent_cli",
        "services",
        "sandy.py",
    )
    start = janus_sandy.index("    async def _run_agent_via_api(")
    end = janus_sandy.index("    async def _run_agent_via_api_with_retry(", start)
    agent_run_body = janus_sandy[start:end]

    assert "public_router_url" in agent_run_body
    assert 'payload["apiBaseUrl"] = api_base_url' in agent_run_body
    assert 'env.pop("JANUS_SYSTEM_PROMPT_PATH", None)' in agent_run_body
    assert 'payload["systemPrompt"]' in agent_run_body
    assert 'payload["systemPromptPath"]' not in agent_run_body

    webcoder_agent_run = read_project_file(
        "chutes-webcoder", "app", "api", "agent-run", "route.ts"
    )
    assert "model === 'janus-router' && !normalizedApiBase" in webcoder_agent_run
    assert "SANDY_AGENT_API_BASE_URL" in webcoder_agent_run

    agent_ops = read_project_file("agent-as-a-service-web", "script.js")
    assert "routerBaseError" in agent_ops
    assert "Model Auto Router requires a router API base URL." in agent_ops
    assert "const { apiBase, routerBase } = getConfig();" in agent_ops


def test_retry_timeout_policies_are_explicit_for_failure_prone_clients() -> None:
    chutes_search_sandy = read_project_file("chutes-search", "src", "lib", "sandy.ts")
    assert "DEFAULT_TIMEOUT_MS" in chutes_search_sandy
    assert "DEFAULT_RETRY_COUNT" in chutes_search_sandy
    assert "shouldRetry" in chutes_search_sandy
    assert "status >= 500" in chutes_search_sandy

    bench_sandy = read_project_file(
        "chutes-bench-runner", "backend", "app", "services", "sandy_service.py"
    )
    assert "httpx.Timeout(90.0, connect=10.0)" in bench_sandy
    assert "for attempt in range(1, 4)" in bench_sandy
    assert "for attempt in range(1, max_attempts + 1)" in bench_sandy
    assert "408, 429, 500, 502, 503, 504" in bench_sandy

    janus_sandy = read_project_file(
        "janus-poc",
        "baseline-agent-cli",
        "janus_baseline_agent_cli",
        "services",
        "sandy.py",
    )
    assert "_run_agent_via_api_with_retry" in janus_sandy
    assert "http_client_timeout" in janus_sandy
    assert "_is_timeout_error" in janus_sandy
