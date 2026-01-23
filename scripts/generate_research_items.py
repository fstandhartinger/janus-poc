#!/usr/bin/env python3
"""Generate Janus research benchmark items."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_PATH = Path("bench/janus_bench/datasets/data/janus/research_items.json")


FACT_ITEMS = [
    (
        "fact_001",
        "The current CEO of OpenAI is Sam Altman.",
        ["Sam Altman", "OpenAI", "CEO"],
        30,
    ),
    (
        "fact_002",
        "The current CEO of Microsoft is Satya Nadella.",
        ["Satya Nadella", "Microsoft", "CEO"],
        30,
    ),
    (
        "fact_003",
        "The current CEO of Apple is Tim Cook.",
        ["Tim Cook", "Apple", "CEO"],
        30,
    ),
    (
        "fact_004",
        "The current CEO of Alphabet (Google) is Sundar Pichai.",
        ["Sundar Pichai", "Alphabet", "Google", "CEO"],
        30,
    ),
    (
        "fact_005",
        "The European Union's GDPR went into effect in May 2018.",
        ["GDPR", "May 2018"],
        3650,
    ),
    (
        "fact_006",
        "The World Health Organization declared COVID-19 a pandemic in March 2020.",
        ["WHO", "pandemic", "March 2020"],
        3650,
    ),
    (
        "fact_007",
        "The 2024 Summer Olympics are scheduled to be held in Paris.",
        ["2024", "Paris", "Olympics"],
        365,
    ),
    (
        "fact_008",
        "NASA's Artemis I mission launched in November 2022.",
        ["Artemis I", "November 2022"],
        3650,
    ),
    (
        "fact_009",
        "The James Webb Space Telescope was launched in December 2021.",
        ["James Webb", "December 2021"],
        3650,
    ),
    (
        "fact_010",
        "The Inflation Reduction Act was signed into law in August 2022.",
        ["Inflation Reduction Act", "August 2022"],
        3650,
    ),
    (
        "fact_011",
        "The EU AI Act was approved by the European Parliament in 2024.",
        ["EU AI Act", "European Parliament", "2024"],
        365,
    ),
    (
        "fact_012",
        "The United Kingdom left the European Union in January 2020.",
        ["United Kingdom", "European Union", "January 2020"],
        3650,
    ),
    (
        "fact_013",
        "Bitcoin's creator is known by the pseudonym Satoshi Nakamoto.",
        ["Satoshi Nakamoto", "Bitcoin"],
        3650,
    ),
    (
        "fact_014",
        "Meta Platforms, Inc. was formerly named Facebook, Inc.",
        ["Meta Platforms", "Facebook"],
        3650,
    ),
    (
        "fact_015",
        "The IPCC released its Sixth Assessment Report synthesis in 2023.",
        ["IPCC", "Sixth Assessment Report", "2023"],
        3650,
    ),
    (
        "fact_016",
        "The World Bank's headquarters are in Washington, D.C.",
        ["World Bank", "Washington"],
        3650,
    ),
    (
        "fact_017",
        "The United Nations was founded in 1945.",
        ["United Nations", "1945"],
        3650,
    ),
    (
        "fact_018",
        "The Hubble Space Telescope was launched in 1990.",
        ["Hubble", "1990"],
        3650,
    ),
    (
        "fact_019",
        "The Paris Agreement on climate change was adopted in 2015.",
        ["Paris Agreement", "2015"],
        3650,
    ),
    (
        "fact_020",
        "OpenAI announced GPT-4 in March 2023.",
        ["GPT-4", "March 2023", "OpenAI"],
        3650,
    ),
]


CURRENT_EVENTS_ITEMS = [
    (
        "current_001",
        "What were the main announcements at the most recent Apple WWDC?",
        ["iOS", "macOS", "visionOS", "AI"],
        30,
    ),
    (
        "current_002",
        "What was the most recent US Federal Reserve interest rate decision and rationale?",
        ["interest rate", "inflation", "policy statement", "economic outlook"],
        30,
    ),
    (
        "current_003",
        "What are the headline updates in the latest EU AI Act legislative timeline?",
        ["AI Act", "compliance timeline", "risk categories", "implementation"],
        90,
    ),
    (
        "current_004",
        "What were the key outcomes of the most recent UN climate conference (COP)?",
        ["emissions", "finance", "adaptation", "loss and damage"],
        90,
    ),
    (
        "current_005",
        "What were the major product or policy announcements from the latest Google I/O?",
        ["Android", "AI", "Search", "developer tools"],
        30,
    ),
    (
        "current_006",
        "What were the notable changes in the most recent Linux kernel release?",
        ["scheduler", "drivers", "filesystem", "security"],
        90,
    ),
    (
        "current_007",
        "What happened in the latest NVIDIA GTC keynote related to AI hardware?",
        ["GPU", "CUDA", "data center", "AI accelerators"],
        90,
    ),
    (
        "current_008",
        "What were the key results of the most recent OpenAI or Anthropic model release?",
        ["model capabilities", "safety", "benchmarks", "availability"],
        30,
    ),
    (
        "current_009",
        "What were the main points from the latest US Executive Order on AI?",
        ["safety", "transparency", "procurement", "standards"],
        90,
    ),
    (
        "current_010",
        "What were the major developments in the most recent UK AI Safety Summit?",
        ["safety commitments", "frontier models", "testing", "international cooperation"],
        90,
    ),
    (
        "current_011",
        "What were the latest developments in U.S. SEC crypto regulation guidance?",
        ["enforcement", "exchange rules", "disclosure", "compliance"],
        90,
    ),
    (
        "current_012",
        "What were the headline changes in the most recent ISO/IEC AI standards update?",
        ["risk management", "governance", "testing", "documentation"],
        180,
    ),
    (
        "current_013",
        "What were the major announcements from the latest Microsoft Build conference?",
        ["Azure", "Copilot", "Windows", "developer tools"],
        30,
    ),
    (
        "current_014",
        "What were the key findings from the most recent IPCC report release?",
        ["climate impacts", "mitigation", "adaptation", "scenarios"],
        180,
    ),
    (
        "current_015",
        "What were the major updates in the most recent Tesla earnings report?",
        ["deliveries", "margins", "guidance", "AI/robotics"],
        90,
    ),
    (
        "current_016",
        "What were the main outcomes of the latest WTO ministerial meeting?",
        ["trade facilitation", "dispute settlement", "development", "agriculture"],
        180,
    ),
    (
        "current_017",
        "What are the latest changes announced for the Android platform (most recent release)?",
        ["API changes", "UI", "security", "performance"],
        90,
    ),
    (
        "current_018",
        "What were the most recent updates to the Python language (latest release highlights)?",
        ["language features", "performance", "typing", "stdlib"],
        180,
    ),
    (
        "current_019",
        "What were the latest developments in the EU's Digital Markets Act enforcement?",
        ["DMA", "gatekeepers", "enforcement actions", "remedies"],
        90,
    ),
    (
        "current_020",
        "What are the most recent changes in the US Department of Energy clean energy funding programs?",
        ["grants", "tax credits", "grid", "renewables"],
        180,
    ),
]


COMPARATIVE_ITEMS = [
    (
        "compare_001",
        "Compare the AI regulation approaches of the EU and China.",
        ["EU AI Act", "China AI regulation", "key differences", "similarities"],
    ),
    (
        "compare_002",
        "Compare GDPR and CCPA privacy laws.",
        ["GDPR", "CCPA", "scope", "user rights"],
    ),
    (
        "compare_003",
        "Compare electric vehicle incentives in the US and EU.",
        ["US incentives", "EU incentives", "eligibility", "policy goals"],
    ),
    (
        "compare_004",
        "Compare open-source and proprietary LLM licensing models.",
        ["open-source licenses", "proprietary terms", "usage restrictions", "tradeoffs"],
    ),
    (
        "compare_005",
        "Compare lithium-ion and sodium-ion batteries for grid storage.",
        ["energy density", "cost", "supply chain", "safety"],
    ),
    (
        "compare_006",
        "Compare Kubernetes and Nomad for container orchestration.",
        ["orchestration model", "scheduling", "ecosystem", "operational complexity"],
    ),
    (
        "compare_007",
        "Compare PostgreSQL and MySQL for OLTP workloads.",
        ["transaction model", "performance", "replication", "extensions"],
    ),
    (
        "compare_008",
        "Compare AWS and Azure for managed AI services.",
        ["model offerings", "managed services", "pricing", "integration"],
    ),
    (
        "compare_009",
        "Compare OAuth2 and OpenID Connect.",
        ["authentication vs authorization", "tokens", "ID token", "use cases"],
    ),
    (
        "compare_010",
        "Compare retrieval-augmented generation and fine-tuning for domain adaptation.",
        ["data requirements", "latency", "update cadence", "accuracy tradeoffs"],
    ),
    (
        "compare_011",
        "Compare transformers and RNNs for NLP tasks.",
        ["architecture", "parallelism", "long-range dependencies", "training efficiency"],
    ),
    (
        "compare_012",
        "Compare REST and GraphQL for API design.",
        ["schema/typing", "over/under-fetching", "caching", "client flexibility"],
    ),
    (
        "compare_013",
        "Compare OpenAI and Anthropic safety approaches.",
        ["safety policies", "red teaming", "governance", "release process"],
    ),
    (
        "compare_014",
        "Compare the NIST AI Risk Management Framework and ISO/IEC AI standards.",
        ["framework scope", "risk management", "compliance", "documentation"],
    ),
    (
        "compare_015",
        "Compare public cloud and on-prem deployments for regulated workloads.",
        ["security controls", "compliance", "cost", "operational overhead"],
    ),
    (
        "compare_016",
        "Compare FPGAs and GPUs for inference workloads.",
        ["latency", "throughput", "power efficiency", "flexibility"],
    ),
    (
        "compare_017",
        "Compare LoRA and full fine-tuning for adapting LLMs.",
        ["parameter efficiency", "training cost", "quality", "deployment"],
    ),
    (
        "compare_018",
        "Compare the EU Digital Markets Act and US antitrust enforcement approaches.",
        ["legal basis", "enforcement tools", "scope", "remedies"],
    ),
    (
        "compare_019",
        "Compare zero trust security and perimeter-based security models.",
        ["trust assumptions", "segmentation", "identity", "implementation challenges"],
    ),
    (
        "compare_020",
        "Compare centralized and decentralized identity systems.",
        ["control model", "privacy", "interoperability", "adoption barriers"],
    ),
]


SYNTHESIS_ITEMS = [
    (
        "synthesis_001",
        "What are the current best practices for fine-tuning large language models?",
        ["LoRA", "QLoRA", "dataset preparation", "evaluation"],
    ),
    (
        "synthesis_002",
        "What are best practices for defending against prompt injection?",
        ["input sanitization", "tool gating", "policy enforcement", "testing"],
    ),
    (
        "synthesis_003",
        "What are best practices for data privacy in AI systems?",
        ["PII handling", "data minimization", "encryption", "access controls"],
    ),
    (
        "synthesis_004",
        "What are best practices for evaluating LLM outputs?",
        ["golden tests", "human review", "automatic metrics", "failure analysis"],
    ),
    (
        "synthesis_005",
        "What are best practices for building retrieval-augmented generation pipelines?",
        ["embedding model selection", "retrieval strategy", "reranking", "citation handling"],
    ),
    (
        "synthesis_006",
        "What are best practices for safe agent tool use?",
        ["permissioning", "sandboxing", "rate limits", "logging"],
    ),
    (
        "synthesis_007",
        "What are best practices for MLOps monitoring of LLM applications?",
        ["drift detection", "latency monitoring", "cost tracking", "feedback loops"],
    ),
    (
        "synthesis_008",
        "What are best practices for secure API key management?",
        ["secret storage", "rotation", "least privilege", "audit logging"],
    ),
    (
        "synthesis_009",
        "What are best practices for incident response in cloud environments?",
        ["detection", "containment", "communication", "postmortem"],
    ),
    (
        "synthesis_010",
        "What are best practices for model quantization and deployment?",
        ["quantization method", "accuracy tradeoff", "hardware targets", "benchmarking"],
    ),
    (
        "synthesis_011",
        "What are best practices for dataset documentation in ML?",
        ["datasheets", "provenance", "labeling process", "bias analysis"],
    ),
    (
        "synthesis_012",
        "What are best practices for accessibility in web applications?",
        ["keyboard navigation", "contrast", "ARIA", "screen reader testing"],
    ),
    (
        "synthesis_013",
        "What are best practices for Kubernetes cluster security?",
        ["RBAC", "network policies", "image scanning", "secrets management"],
    ),
    (
        "synthesis_014",
        "What are best practices for supply chain risk management?",
        ["vendor assessment", "monitoring", "diversification", "contingency planning"],
    ),
    (
        "synthesis_015",
        "What are best practices for energy-efficient ML training?",
        ["mixed precision", "hardware selection", "schedule optimization", "carbon tracking"],
    ),
    (
        "synthesis_016",
        "What are best practices for multimodal model evaluation?",
        ["modality coverage", "bias checks", "benchmark suites", "human eval"],
    ),
    (
        "synthesis_017",
        "What are best practices for human-in-the-loop review of AI outputs?",
        ["review criteria", "workflow tooling", "escalation", "sampling strategy"],
    ),
    (
        "synthesis_018",
        "What are best practices for A/B testing ML models?",
        ["experiment design", "metrics", "traffic allocation", "statistical significance"],
    ),
    (
        "synthesis_019",
        "What are best practices for privacy-preserving machine learning?",
        ["federated learning", "differential privacy", "secure aggregation", "threat modeling"],
    ),
    (
        "synthesis_020",
        "What are best practices for AI governance and compliance programs?",
        ["policy framework", "risk assessments", "auditability", "stakeholder oversight"],
    ),
]


DEEP_DIVE_ITEMS = [
    (
        "deep_001",
        "Explain how Bittensor's incentive mechanism works, including the role of validators and miners.",
        ["subnet", "validator", "miner", "emission", "consensus"],
    ),
    (
        "deep_002",
        "Explain how Ethereum proof-of-stake works, including staking and slashing.",
        ["validator", "staking", "slashing", "epochs", "finality"],
    ),
    (
        "deep_003",
        "Explain how Bitcoin mining and difficulty adjustment work.",
        ["mining", "hash rate", "difficulty adjustment", "blocks", "proof of work"],
    ),
    (
        "deep_004",
        "Explain how DNS resolution works from a client to an authoritative server.",
        ["recursive resolver", "root servers", "TLD", "authoritative", "caching"],
    ),
    (
        "deep_005",
        "Explain how the TLS handshake establishes a secure connection.",
        ["certificates", "key exchange", "session keys", "cipher suites", "verification"],
    ),
    (
        "deep_006",
        "Explain how Kubernetes scheduling works, including placement decisions.",
        ["scheduler", "nodes", "pods", "affinity", "taints"],
    ),
    (
        "deep_007",
        "Explain how PostgreSQL MVCC handles concurrent transactions.",
        ["transactions", "snapshots", "visibility", "vacuum", "locking"],
    ),
    (
        "deep_008",
        "Explain how OpenTelemetry tracing works end-to-end.",
        ["spans", "traces", "context propagation", "exporters", "sampling"],
    ),
    (
        "deep_009",
        "Explain how Kafka handles partitions and replication.",
        ["partition", "leader", "replica", "ISR", "offsets"],
    ),
    (
        "deep_010",
        "Explain how WebRTC establishes peer connections across NATs.",
        ["ICE", "STUN", "TURN", "SDP", "NAT traversal"],
    ),
    (
        "deep_011",
        "Explain the OAuth2 authorization code flow with PKCE.",
        ["client", "authorization server", "authorization code", "access token", "redirect URI"],
    ),
    (
        "deep_012",
        "Explain how retrieval-augmented generation pipelines retrieve and rank context.",
        ["embeddings", "vector store", "retriever", "reranker", "context window"],
    ),
    (
        "deep_013",
        "Explain how diffusion models generate images from noise.",
        ["noise schedule", "denoising", "U-Net", "latent space", "sampling"],
    ),
    (
        "deep_014",
        "Explain how RLHF is used to align large language models.",
        ["reward model", "preference data", "PPO", "policy model", "safety alignment"],
    ),
    (
        "deep_015",
        "Explain how secure enclaves (TEE/SGX) provide isolation and attestation.",
        ["attestation", "isolation", "trusted code", "memory encryption", "threat model"],
    ),
    (
        "deep_016",
        "Explain how the Raft consensus algorithm achieves consistency.",
        ["leader election", "log replication", "commit index", "term", "heartbeat"],
    ),
    (
        "deep_017",
        "Explain how container images are built and layered.",
        ["layers", "registry", "union filesystem", "image manifest", "build cache"],
    ),
    (
        "deep_018",
        "Explain how HTTP/3 and QUIC improve web transport.",
        ["UDP", "streams", "handshake", "multiplexing", "connection migration"],
    ),
    (
        "deep_019",
        "Explain how vector databases index embeddings for similarity search.",
        ["HNSW", "ANN search", "index build", "distance metrics", "recall"],
    ),
    (
        "deep_020",
        "Explain how feature stores support ML training and serving.",
        ["offline store", "online store", "feature pipelines", "consistency", "serving latency"],
    ),
]


def build_fact_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for item_id, claim, expected_facts, max_age_days in FACT_ITEMS:
        items.append(
            {
                "id": item_id,
                "suite": "janus/intelligence",
                "task_type": "fact_verification",
                "claim": claim,
                "prompt": (
                    "Verify the following claim using current sources and cite them: "
                    + claim
                ),
                "requires_search": True,
                "max_age_days": max_age_days,
                "expected_facts": expected_facts,
                "evaluation": {
                    "type": "boolean_with_evidence",
                    "requires": ["search_performed", "source_cited", "correct_conclusion"],
                },
            }
        )
    return items


def build_current_events_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for item_id, query, expected_topics, max_age_days in CURRENT_EVENTS_ITEMS:
        items.append(
            {
                "id": item_id,
                "suite": "janus/intelligence",
                "task_type": "current_events",
                "query": query,
                "prompt": f"Use web research to answer: {query} Provide citations.",
                "requires_search": True,
                "max_age_days": max_age_days,
                "expected_facts": expected_topics,
                "evaluation": {
                    "type": "key_facts",
                    "expected_topics": expected_topics,
                    "min_topics": 3,
                },
            }
        )
    return items


def build_comparative_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for item_id, query, required_aspects in COMPARATIVE_ITEMS:
        items.append(
            {
                "id": item_id,
                "suite": "janus/intelligence",
                "task_type": "comparative",
                "query": query,
                "prompt": f"Use web research to answer: {query} Provide citations.",
                "requires_search": True,
                "expected_facts": required_aspects,
                "evaluation": {
                    "type": "balanced_comparison",
                    "required_aspects": required_aspects,
                    "min_sources": 2,
                },
            }
        )
    return items


def build_synthesis_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for item_id, query, required_elements in SYNTHESIS_ITEMS:
        items.append(
            {
                "id": item_id,
                "suite": "janus/intelligence",
                "task_type": "synthesis",
                "query": query,
                "prompt": f"Use web research to answer: {query} Provide citations.",
                "requires_search": True,
                "expected_facts": required_elements,
                "evaluation": {
                    "type": "comprehensive_answer",
                    "required_elements": required_elements,
                    "quality_criteria": [
                        "technical_accuracy",
                        "practical_advice",
                        "source_diversity",
                    ],
                },
            }
        )
    return items


def build_deep_dive_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for item_id, query, required_concepts in DEEP_DIVE_ITEMS:
        items.append(
            {
                "id": item_id,
                "suite": "janus/intelligence",
                "task_type": "deep_dive",
                "query": query,
                "prompt": f"Use web research to answer: {query} Provide citations.",
                "requires_search": True,
                "expected_facts": required_concepts,
                "evaluation": {
                    "type": "expert_level",
                    "required_concepts": required_concepts,
                    "depth_indicators": ["technical_details", "examples", "tradeoffs"],
                },
            }
        )
    return items


def main() -> None:
    items = (
        build_fact_items()
        + build_current_events_items()
        + build_comparative_items()
        + build_synthesis_items()
        + build_deep_dive_items()
    )

    if len(items) != 100:
        raise ValueError(f"Expected 100 items, got {len(items)}")

    payload = {
        "metadata": {
            "benchmark": "janus_research",
            "version": "1.1.0",
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_items": len(items),
            "categories": {
                "fact_verification": len(FACT_ITEMS),
                "current_events": len(CURRENT_EVENTS_ITEMS),
                "comparative": len(COMPARATIVE_ITEMS),
                "synthesis": len(SYNTHESIS_ITEMS),
                "deep_dive": len(DEEP_DIVE_ITEMS),
            },
        },
        "items": items,
    }

    output_path = OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} items to {output_path}")


if __name__ == "__main__":
    main()
