# History

## 2026-01-23
- Implemented 33 specs, then added the history file, no details about 1-33 to be expected for this reason, but see here to understand progress and decide if a certain spec is to be skipped be cause we just tried too hard (too often) and don't want to get stuck on one. If we tried one spec 10 times and still didn't succeed in implementing it, lets split it into simpler subspecs and continue.

## 2026-01-23
- Completed spec 34_janus_streaming_benchmark.md (streaming benchmark metrics/data already implemented in bench runner).

## 2026-01-24
- Completed spec 35_janus_cost_benchmark.md with cost efficiency scoring, dataset, metrics, and tests in the bench runner.
- Completed spec 36_janus_bench_ui_section.md with Janus UI/category metadata, composite score endpoint, and run detail UI updates in chutes-bench-runner.
- Completed spec 37_extended_file_attachments.md with multi-format file handling, previews, backend extraction, and tests.
- Completed spec 38_multimodal_vision_models.md with vision routing, image detection, fallback, LangChain vision support, agent docs, and tests.
- Completed spec 39_speech_to_text_voice_input.md with voice recording UI, transcription proxy, env toggles, and unit tests.
- Completed spec 40_chat_ui_polish_and_media.md with chat layout fixes, simplified sidebar/topbar, rich media rendering, and test updates.
- Completed spec 41_enhanced_agent_system_prompt.md with expanded agent prompt guidance, sandbox env variables, and artifact URL patterns.
- Completed spec 42_sandbox_file_serving.md with CORS-ready artifact server, agent artifact helpers, and URL resolution.
- Completed spec 43_agent_sandbox_management.md with auth pass-through, sandbox management helpers, web app hosting utility, and prompt updates.
- Completed spec 44_deep_research_integration.md with deep research client, gateway proxy streaming, UI progress tracking, and tests.
- Follow-up: mapped baseline model aliases to configured model to restore production chat completions.
- Verified spec 44 deep research integration end-to-end, fixed deep research SSE typing, and marked the spec COMPLETE.
- Completed spec 45_browser_automation_screenshots.md with Playwright browser helper, sandbox screenshot streaming hooks, UI screenshot stream rendering, and SSE formatting helper.
- Restored the DeepResearchProgress component to fix janus-ui production builds.
- Completed spec 46_gui_automation_desktop_control.md with GUI automation tools, sandbox GUI config, and a VNC viewer component.
- Implemented spec 47_text_to_speech_response_playback.md (TTS playback, voice selection, caching, and tests); blocked until CHUTES_API_KEY is configured on Render gateway for /api/tts.
- Completed spec 48_rich_data_visualization.md with rich chart, spreadsheet, diagram rendering, content parsing, and agent documentation.
- Completed spec 49_complexity_detection_improvements.md with conservative LLM routing, URL interaction detection, keyword updates, README diagram fixes, and new tests.
- Completed spec 50_canvas_feature.md with canvas parsing, CodeMirror editor panel, AI shortcuts, version history, persistence, and chat integration.
- Completed spec 51_why_janus_section_clarity.md with split user/builder benefit groups and updated Why Janus messaging on the landing page.
- Completed spec 52_comprehensive_baseline_testing.md with shared smoke suite, baseline unit/integration coverage, test utilities/docs, and CI workflow for baseline tests.
- Completed spec 53_music_generation_diffrhythm.md with DiffRhythm baseline tooling/docs, chat audio playback UI, and additional LangChain tests.
- Completed spec 54_enhanced_audio_output.md with unified audio response UI, audio parsing, expanded Kokoro docs, and baseline TTS tool updates.
- Completed spec 55_baseline_containerization.md with baseline/gateway Dockerfiles, compose workflow, container scripts, Sandy runner scaffold, and documentation updates.
- Re-verified spec 55_baseline_containerization.md artifacts and marked the spec COMPLETE with NR_OF_TRIES tracking.
- Completed spec 56_scoring_service_backend.md with the new scoring-service backend, Neon schema, janus-bench integration, tests, and Render blueprint updates.
- Completed spec 57_scoring_ui_page.md with the scoring run submission page, live run status views, run detail dashboards, and scoring API proxies in the UI.

## 2026-01-25
- Began spec 58_baseline_performance_optimization.md with benchmark analysis tooling, robust streaming SSE output, and smoke-test coverage updates for the baselines.
- Ran full Janus intelligence suite for both baselines using Hermes-4-14B + Qwen2.5-VL-32B and captured metrics; tool-use benchmarks still lag while research/streaming/multimodal improved.
- Completed spec 59_composite_model_router.md with the local router service, LLM-based classification, fallback routing, metrics endpoint, and updated baseline packaging/tests.
- Completed spec 67_code_review_ui.md with UI a11y fixes (main landmarks, heading hierarchy, contrast), API client retries/timeouts, and updated tests.
- Completed spec 68_code_review_bench.md with TTFT timeout enforcement, tool-call success handling, SSE parsing robustness, research metadata merging, config weight validation, and new tests.
- Completed spec 69_comprehensive_testing_suite.md with test runner refinements, gateway smoke/integration skip guards, and logging middleware typing updates.
- Completed spec 70_hero_video_redesign.md with in-place autoplay hero video, scroll-scrubbing canvas frames, watermark masking, and new Playwright coverage.
- Completed spec 71_competition_page_improvements.md with clickable Mermaid modals, updated leaderboard/prize pool data, collapsible sections, accessible contributor copy, and FAQ accordions.
- Completed spec 72_memory_service_backend.md with the FastAPI memory service, LLM extraction/relevance flow, Postgres-backed storage, tests, and Render deployment setup.
- Completed spec 73_memory_integration_baselines.md with memory-aware request fields, prompt injection, background extraction, and baseline test coverage.
- Completed spec 74_memory_feature_ui.md with client-side user ID storage, memory toggle UI, chat request flags, and unit coverage.
- Re-verified spec 74_memory_feature_ui.md status formatting and refreshed NR_OF_TRIES after validation pass.
- Completed spec 75_sign_in_with_chutes.md with OAuth sign-in, free chat gating, IP rate limiting proxy, auth-aware chat requests, baseline token support, and updated UI/docs.
- Re-verified spec 75_sign_in_with_chutes.md status formatting and refreshed NR_OF_TRIES after validation pass.
- Completed spec 76_memory_investigation_tool.md with investigate_memory tools for baselines, conditional tool registration, sandbox env wiring, and tests.
- Re-verified spec 03_components.md against docs/architecture.md + README testing matrix; refreshed NR_OF_TRIES after validation pass.
- Completed spec 77_memory_management_ui.md with memory management UI, memory CRUD hooks, gateway proxy routes, and memory service update/clear endpoints/tests.
- Re-verified spec 77_memory_management_ui.md status formatting for Ralph loop detection.
- Completed spec 78_plus_menu_generation_tags.md with the plus menu UI, generation flag wiring, baseline routing/prompt updates, and new tests.
- Completed spec 79_baseline_langchain_feature_parity.md with complexity routing, deep research/video/audio/file tools, artifact streaming, auth passthrough, and updated LangChain baseline tests/docs.
- Verified spec 80_debug_mode_flow_visualization.md implementation, updated status/NR_OF_TRIES, and recorded completion.
- Re-validated spec 55_baseline_containerization.md, fixing LangChain auth fallback + docker-compose defaults, confirming container health/chat completions, and resetting gateway timeout defaults to satisfy guardrails tests.

## 2026-01-26
- Completed spec 81_baseline_documentation_pages.md with a new baselines section on the competition page plus dedicated CLI agent and LangChain documentation pages.
- Completed spec 82_chat_ui_polish.md with streaming message indicators, reasoning filtering, TTS icon update, and input layout fixes.
- Completed spec 83_fix_transcription_api.md with JSON base64 transcription payloads (omitting null language), list-response parsing for Chutes segments, refreshed UI/tests/error logging, and verified the whisper endpoint behavior.
- Completed spec 84_baseline_smoke_tests.md with gateway baseline smoke scripts, pytest marker coverage, and gateway-routed baseline smoke tests.
- Completed spec 85_pwa_mobile_install.md with PWA manifest/service worker auto-update, mobile install/update toast, share-target handling, and read-to-me TTS auto-play wiring.
- Re-verified spec 83_fix_transcription_api.md status formatting for Ralph detection and bumped NR_OF_TRIES after validation.
- Completed spec 86_generative_ui_responses.md with html-gen-ui rendering, sandboxed iframe UI blocks, markdown renderer integration, prompt updates, and unit coverage.
- Completed spec 87_api_documentation_page.md with a new API docs page, gateway Swagger/OpenAPI endpoints, and multi-language examples/parameter docs.
- Completed spec 88_chat_ui_improvements.md with sidebar/topbar cleanup, smart scrolling, message actions/share, and citation-aware markdown rendering.
- Completed spec 89_fix_deep_research.md with Firecrawl search fallback, UI deep research streaming, progress stages, and source attribution.
- Completed spec 90_complexity_detection_improvements.md with multilingual/git keyword routing, separable verb matching, Sandy unavailability messaging, health sandbox status, and UI availability indicator.
- Completed spec 91_fix_sign_in_with_chutes.md with OAuth config error handling, optional client secrets, refreshed IDP app credentials, Render env updates, and verified production login/logout + authenticated chat flow.
- Completed spec 92_baseline_agent_cli_e2e_verification.md with comprehensive E2E tests for agent selection (Claude Code, Codex, Aider), complex tasks (git clone, web search, coding, image gen, TTS), model compatibility tests, SSE streaming verification, and yolo mode validation. Added retry logic for transient 5xx errors and flexible assertions for task engagement detection.

## 2026-01-27
- Added pre-release password gate wiring (Render env + constitution guidance) for UI + gateway access.
- Updated baseline agent system prompt with explicit media API instructions and removed bootstrap duplication.
- Hardened Sandy streaming output handling (filter noisy preflight warnings) and ensured Claude-compatible model selection for claude-code agent-run.
- Refined Claude Code agent-run invocation (append system prompt file, run from /workspace, avoid conflicting flags) and router usage notes in spec 115.
- De-duplicated Claude Code streamed content so final results are not repeated.
- Implemented artifact delivery pipeline updates: cache sandbox artifacts server-side, avoid inline image data URLs, added artifact grace period, and refreshed prompts/docs + cross-project READMEs.
- Completed spec 117_sandy_artifact_proxy_port.md by aligning artifact serving with Sandy runtime port (5173), updating prompts/docs, improving artifact caching streaming, and fixing Playwright pre-release state.
- Added baseline agent docs UI components (CodeBlock/ConfigTable/MermaidDiagram) to keep `/docs/baseline-agent-cli` buildable after the doc page update.

## 2026-01-28
- Completed spec 94_baseline_langchain_e2e_verification.md with resilient LangChain E2E coverage (artifact-aware streaming assertions, error/timeout skips) and refreshed Playwright storage defaults for chat tests.

## 2026-01-29
- Completed spec 97_cli_agent_warm_pool.md with warm pool lifecycle management, agent API sandbox reuse, health reporting, config wiring, and refill/recycle test coverage.
- Completed spec 98_real_benchmark_dataset.md with public train/dev JSONL datasets, evaluator suite, loader updates, private dataset scaffolding, and benchmark scoring integration.
- Completed spec 99_arena_style_comparison.md with arena mode UI toggle, paired responses, vote collection + ELO leaderboard, and scoring-service integrations.
- Completed spec 100_long_agentic_task_reliability.md with SSE keepalives, retry/progress indicators for long operations, UI timeout messaging, and long-task integration tests.
- Completed spec 101_baseline_langchain_full_parity.md with git repo tools, create-directory support, parity-focused E2E coverage, and LangChain baseline docs comparison updates.
- Completed spec 102_core_demo_use_cases.md with demo E2E coverage, web search result filtering + fallback checks, repo clone error messaging, and image response validation. Core demo tests ran locally but skipped due to unavailable services (pytest-timeout plugin missing for --timeout).
- Completed spec 104_request_tracing_observability.md with request ID propagation, structured tracing middleware, log search endpoints/CLI, and UI debug request metadata display.
- Completed spec 103_demo_prompts_in_chat_ui.md with demo prompt data, empty-state grid, quick suggestions, full prompt modal, and Playwright coverage.
- Completed spec 105_fix_mermaid_modal.md with chat mermaid fullscreen modal support, hover hint styling, and keyboard-accessible interactions.
- Note: `npm run lint` currently fails due to existing `react-hooks/set-state-in-effect` errors in chat/share/pre-release/TTS components; not addressed in this spec.
- Completed spec 107_e2e_browser_automation_testing.md with Playwright helpers, expanded UI E2E coverage (auth, file upload, memory, debug, voice), debug panel wiring, fingerprint auth fallback, and CI workflow wiring.
- Completed spec 108_visual_regression_testing.md with Playwright visual config, visual test suites (pages, components, themes, responsive, states, a11y, animations), stabilized UI fixtures, baseline snapshots, and CI workflow.
- Completed spec 110_mermaid_edge_label_clipping_fix.md with updated Mermaid sizing/overflow CSS, diagram wrapper + config tweaks, and new visual tests for edge label rendering.
- UI Playwright `npm test` still reports pre-existing failures: chat CORS/401 console errors, chat streaming indicator visibility, competition leaderboard selector + horizontal scroll check, and memory toggle blocked by memory sheet overlay.
- Production gateway check: /health and /v1/models OK; /v1/chat/completions returned an error response message for baseline-cli-agent.
- Completed spec 111_claude_code_system_prompt.md with Claude router base normalization and stable Sandy agent-run prompt injection.
- Stabilized Playwright chat/competition/memory E2E flows with gateway stubs and chat readiness helpers; full UI + gateway test suites now pass.
- Completed spec 111_other_cli_agents_integration.md with CLI agent command updates (OpenCode/Codex), Roo Code + Cline installs, CLI agent selection UI + header wiring, and updated agent capability docs.

## 2026-01-30
- Completed spec 112_comprehensive_unit_testing_suite.md with gateway SSE/model unit coverage, baseline CLI complexity/vision/sandy unit tests, LangChain agent/tool unit checks, UI useChat + SSE parsing tests, and a run-unit-tests script.
- Completed spec 114_chat_ui_mobile_responsive.md with ChatOverflowMenu component, responsive topbar for mobile (< 640px), free chats indicator above input on mobile, 44px touch targets, and smooth animations. Verified on iPhone SE/14 viewports.
- Verified and marked complete spec 116_artifact_delivery_pipeline.md - all artifact delivery infrastructure was already implemented: SandyService artifact collection, SSE artifacts events, tool-result recovery, grace period for sandbox termination, UI artifact caching at /api/artifacts/cache and serving at /api/artifacts/[...path], and MediaRenderer integration.
- Verified and marked complete spec 116_media_auth_and_agent_router_e2e.md - authorization headers and CHUTES_API_KEY are properly documented in all prompts (system.md, text-to-image.md, etc.), bootstrap.sh exports the key, and the claude wrapper sources the env file for agent-run processes.
- Completed spec 117_claude_code_streaming_env_fix.md - added max_tokens clamping to OpenAI router endpoint (mirrors Anthropic path), verified existing env persistence in bootstrap.sh/.janus_env, Claude settings.json injection, claude wrapper with partial messages, image API docs using num_inference_steps, and tool-result recovery with data URL materialization.
- Completed spec 118_browser_session_research.md - comprehensive browser session management research including: deployed mock login page on Render, tested Playwright storageState capture/injection via MCP, validated Vercel agent-browser persistent profiles (session survives restart), tested cookie JSON import, compared 3 Browser MCPs (Playwright, Puppeteer, agent-browser), tested Neon database storage for sessions, wrote detailed research report to docs/browser-session-research-results.md, created 4 follow-up implementation specs (119-122) for session store, agent-ready warm pool, capture UI, and injection API.
- Completed spec 119_browser_session_store.md - implemented secure browser session storage microservice: FastAPI REST API with session CRUD endpoints, AES-256-GCM encryption with per-user key derivation via HKDF, JWT authentication with Chutes IDP, Playwright-compatible storage state format, SQLAlchemy async database with lazy initialization, 35 unit tests (crypto + API), deployed to Render at https://janus-browser-session-service.onrender.com.
