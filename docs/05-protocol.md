# WS v1 protocol

> Status: **skeleton** — seeded in T1.1; full content lands across the waves (see `specs/tasks.md`). This file is covered by the `docs:check` drift gate.

Message schemas (JSON Schema snippets), sequences (D5a/D5b), error codes, serialization/busy/resume rules

## Diagrams

### D5a — Protocol sequence: normal action + decision + streaming

```mermaid
sequenceDiagram
  participant C as Godot client
  participant S as FastAPI WS handler
  participant G as LangGraph agent
  participant E as Rules engine
  C->>S: hello {token}
  S-->>C: welcome {session_id, resume_token}
  C->>S: action {move / attack / use_item / ...}
  S->>E: engine-first dispatch (never busy)
  E-->>S: state_delta {seq, action_id echo}
  S-->>C: turn_result {action_id}
  C->>S: action {talk}
  S->>G: graph run (busy set)
  G-->>S: decision_request {decision_id, options}
  S-->>C: decision_request
  C->>S: decision {decision_id, option_id}
  G-->>S: narrative_delta* {narrative_id}
  S-->>C: narrative_delta*
  S-->>C: narrative_end {narrative_id} (or error, same id, within 30s)
```

### D5b — Protocol sequence: resume (pinned order)

```mermaid
sequenceDiagram
  participant C as Client
  participant S as Server
  C->>S: resume {resume_token}
  S-->>C: state_sync {seq: N} (full snapshot, FIRST frame)
  S-->>C: state_delta* (queued actions, one at a time, seq > N)
  S-->>C: narrative_replay {narrative_id, offset} (only if stream was cut)
  C->>S: action* (subsequent turns)
```

<!-- content to follow -->