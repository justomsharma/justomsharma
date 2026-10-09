"""What the card says. Edit the copy here; layout and rendering live elsewhere."""

from __future__ import annotations

from datetime import date

from generator.layout import (
    Line,
    blank,
    fmt_int,
    leader,
    leader_rich,
    pair,
    rule,
    section,
    uptime,
)
from generator.stats import Stats

LOGIN = "justomsharma"
HANDLE = "om@sharma"
# First day shipping AI to production (VDOIT Technologies).
CAREER_START = date(2024, 1, 1)
# Stars/followers only earn a slot once they say something.
SOCIAL_MIN = 10

ABOUT = [
    ("Role", "AI Engineer, real-time voice & LLM systems"),
    ("Host", "Jobtwine, Bangalore"),
    ("Uptime", "{uptime} in prod"),
    ("Kernel", "Python, TypeScript, C++"),
    ("IDE", "Claude Code, Cursor, VS Code"),
    ("Pipeline", "mic → VAD → STT → LLM → TTS → you"),
    ("Latency.p50", "< 2s a turn, 300+ interviews a day"),
]

STACK = [
    ("Stack.Agents", "LangGraph, MCP, Pydantic AI, tool calling"),
    ("Stack.Voice", "LiveKit, Twilio, Deepgram, WebRTC, SIP"),
    ("Stack.Serving", "vLLM, llama.cpp, Ollama, quantization"),
    ("Stack.Retrieval", "Pinecone, Qdrant, FAISS, Postgres, Redis"),
    ("Stack.Evals", "LangSmith, Langfuse, W&B, OpenTelemetry"),
    ("Stack.Infra", "AWS, GCP, Docker, Kubernetes, Actions"),
]

# Systems actually shipped (Jobtwine, Darwix AI, VDOIT, side projects).
SHIPPED = [
    ("VoiceAgent", "AI interviewer, LiveKit + Twilio, WebRTC/SIP"),
    ("LLMRouter", "queued dispatch with multi-LLM failover"),
    ("Agents", "deterministic tool calls, schema-checked output"),
    ("RAG", "Pinecone + Postgres ingest, +40% chunk accuracy"),
    ("FineTuning", "domain LLMs with LoRA / QLoRA"),
    ("MCPServer", "resume advice grounded in real GitHub activity"),
    ("CallAnalytics", "live diarization, transcription, scoring"),
    ("Observability", "per-stage latency traces, anomaly alerts"),
]

CONTACT = [
    ("Web", "omsharma.dev"),
    ("Email", "justomsharma@gmail.com"),
    ("LinkedIn", "in/omsharmaofficial"),
    ("Medium", "@OmsharmaOfficial"),
]


def stats_lines(s: Stats) -> list[Line]:
    commits = ("Commits", fmt_int(s.commits))
    repos = fmt_int(s.repos)
    if s.contributed:
        try:
            first = pair(("Repos", f"{repos} {{Contributed: {s.contributed}}}"), commits)
        except ValueError:  # big numbers: drop the label, keep the count
            first = pair(("Repos", f"{repos} {{+{s.contributed}}}"), commits)
    else:
        first = pair(("Repos", repos), commits)
    lines = [first]
    contributions = ("Contributions.1y", fmt_int(s.contributions_1y))
    if s.stars >= SOCIAL_MIN:
        lines.append(pair(contributions, ("Stars", fmt_int(s.stars))))
    elif s.followers >= SOCIAL_MIN:
        lines.append(pair(contributions, ("Followers", fmt_int(s.followers))))
    else:
        lines.append(leader(*contributions))
    loc = [
        (fmt_int(s.loc), "v"),
        (" ( ", "d"),
        (fmt_int(s.additions) + "++", "add"),
        (", ", "d"),
        (fmt_int(s.deletions) + "--", "del"),
        (" )", "d"),
    ]
    try:
        lines.append(leader_rich("Lines of Code on GitHub", loc))
    except ValueError:  # millions of lines: shorter key
        lines.append(leader_rich("LOC", loc))
    return lines


def card_lines(stats: Stats, today: date) -> list[Line]:
    up = uptime(CAREER_START, today)
    lines: list[Line] = [rule(HANDLE)]
    lines += [leader(k, v.format(uptime=up)) for k, v in ABOUT]
    lines += [blank()] + [leader(k, v) for k, v in STACK]
    lines += [blank(), section("Shipped")] + [leader(k, v) for k, v in SHIPPED]
    lines += [blank(), section("Contact")] + [leader(k, v) for k, v in CONTACT]
    lines += [blank(), section("GitHub Stats")] + stats_lines(stats)
    lines += [blank(), [(HANDLE, "h"), (":~$ ", "d"), ("", "cursor")]]
    return lines
