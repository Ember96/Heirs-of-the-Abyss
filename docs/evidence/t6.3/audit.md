# T6.3 evidence — anti-tamper hardening verification

> [!TIP]
> Fuzz green (13 tests), client audit clean, telemetry hook wired, WSS/TLS documented.

## Fuzz + replay + forgery (13 tests, `server/tests/test_anti_tamper.py`)

| Case | Outcome |
|------|---------|
| Non-JSON / list / string / int frames | clean `1007` close, no crash |
| Missing `v` (unsupported version) | `unsupported_version` error + `1008` close |
| Unknown type / empty id / negative seq / non-dict payload | clean `1007`/`1008` close |
| Oversized frame (>64 KB) | `frame_too_large` typed error |
| seq replay (reuse a seen seq) | `1008` close, no error leaked |
| Forged resume token | `session_not_found` typed error |
| Resume token entropy | 100/100 distinct, ≥40 chars (256-bit) |

## Client audit (NFR-5)

- 🔵 Only `randi()` in the client is a message correlation ID (`NetworkManager.gd:88`) — not gameplay, not a sim path (invariant #3 holds).
- 🔵 All `FileAccess` usage is in `test_*.gd` harnesses (read input log / write conformance output) — no client save file (invariant #6 holds).
- 🟢 No `randomize()` / `randf()` outside the seeded PRNG (PCG32).

## Telemetry hook

- `log_security_event(code, detail)` — single structured log point (logger `heirs-of-the-abyss.security`) wired into every rejection path: `frame_too_large`, `bad_json`, `unsupported_version`, `frame_invalid`, `seq_replay`, `auth_failed`, `hmac_invalid`, `rate_limited`.

## WSS/TLS

- Documented in `docs/13-security.md` (§ Transport): production must terminate TLS + `wss://`; HMAC key and resume token are bearer secrets.
