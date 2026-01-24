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
