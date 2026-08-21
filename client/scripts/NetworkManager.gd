extends Node

signal session_ready(session_id: String)
signal message_received(msg: Dictionary)
signal disconnected

const HEARTBEAT_INTERVAL := 15.0
const MAX_RECONNECT_ATTEMPTS := 10
const BASE_BACKOFF := 1.0

var _peer := WebSocketPeer.new()
var _url: String
var _hmac_key := PackedByteArray()
var _session_id := ""
var _resume_token := ""
var _authenticated := false
var _in_seq := -1
var _out_seq := 0
var _heartbeat_timer := 0.0
var _reconnect_attempts := 0
var _connected_ever := false

func connect_to(url: String) -> void:
	_url = url
	_reconnect_attempts = 0
	_connected_ever = false
	_do_connect()

func _do_connect() -> void:
	_peer = WebSocketPeer.new()
	_peer.connect_to_url(_url)
	_peer.set_no_delay(true)

func _process(delta: float) -> void:
	if _peer.get_ready_state() == WebSocketPeer.STATE_OPEN:
		_peer.poll()
		while _peer.get_available_packet_count() > 0:
			var raw = _peer.get_packet()
			if _peer.was_string_packet():
				_handle_frame(raw.get_string_from_utf8())
		_heartbeat_timer += delta
		if _heartbeat_timer >= HEARTBEAT_INTERVAL:
			_heartbeat_timer = 0.0
			_send_raw("ping", "hb-%d" % Time.get_ticks_msec(), {})
	elif _peer.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		if _authenticated or _connected_ever:
			_authenticated = false
			_hmac_key = PackedByteArray()
			disconnected.emit()
		_reconnect_attempts += 1
		if _reconnect_attempts <= MAX_RECONNECT_ATTEMPTS:
			var delay = BASE_BACKOFF * pow(2, _reconnect_attempts - 1)
			get_tree().create_timer(delay).timeout.connect(_do_connect)
	elif _peer.get_ready_state() == WebSocketPeer.STATE_CONNECTING:
		pass

func _handle_frame(raw: String) -> void:
	_connected_ever = true
	var frame = JSON.parse_string(raw)
	if frame == null or not frame is Dictionary:
		return
	var seq = frame.get("seq", -1)
	if seq <= _in_seq and _in_seq >= 0:
		return
	_in_seq = seq
	var type = frame.get("type", "")
	var payload = frame.get("payload", {})
	match type:
		"welcome": _on_welcome(payload)
		"pong": pass
		"error":
			if not payload.get("recoverable", true):
				push_error("NetworkManager: fatal error %s" % payload.get("code"))
			message_received.emit(frame)
		_: message_received.emit(frame)

func _on_welcome(p: Dictionary) -> void:
	_session_id = p.get("session_id", "")
	_resume_token = p.get("resume_token", "")
	_hmac_key = HmacUtils.hex_to_bytes(p.get("hmac_key", ""))
	_authenticated = true
	session_ready.emit(_session_id)

func send_hello(token: String) -> void:
	_send_raw("hello", "hello-%d" % Time.get_ticks_msec(), {"token": token})

func send_action(action: String, params: Dictionary = {}) -> void:
	_send_raw("action", "a-%d-%d" % [Time.get_ticks_msec(), randi()], {"action": action, "params": params})

func send_decision(decision_id: String, option_id: String) -> void:
	_send_raw("decision", decision_id, {"decision_id": decision_id, "option_id": option_id})

func send_resume() -> void:
	_send_raw("resume", "resume-%d" % Time.get_ticks_msec(), {"resume_token": _resume_token})

func send_json(type: String, id: String, payload: Dictionary) -> void:
	_send_raw(type, id, payload)

func _send_raw(type: String, id: String, payload: Dictionary) -> void:
	if not _authenticated and type != "hello":
		return
	var seq = _out_seq
	_out_seq += 1
	var frame = {"v": 1, "type": type, "id": id, "seq": seq, "payload": payload}
	if _hmac_key.size() > 0:
		var canonical = HmacUtils.canonical_json(payload)
		var msg = "%s|%s|%d|%s" % [type, id, seq, canonical]
		frame["hmac"] = HmacUtils.hmac_sha256_hex(_hmac_key, msg.to_utf8_buffer())
	_peer.send_text(JSON.stringify(frame, "", false))

func get_session_id() -> String: return _session_id
func get_resume_token() -> String: return _resume_token
func is_authenticated() -> bool: return _authenticated
