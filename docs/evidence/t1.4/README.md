# t1.4 evidence — Godot skeleton + NetworkManager

> [!TIP]
> Acceptance met via test suite (197 green).

- Acceptance: connects to mock_server, auth+HMAC, reconnect+resume
- Covered by: client/scripts/NetworkManager.gd + test_hmac.gd/test_sync.gd/test_sim.gd; server tests/test_e2e_socket.py
- Status: green.
