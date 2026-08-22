class_name ErrorMessages
extends RefCounted


static func message_for(code: String) -> String:
	match code:
		"busy":
			return "The dungeon is still thinking…"
		"session_terminal":
			return "Your run is over."
		"rate_limited":
			return "Too many actions — slow down."
		"session_not_found":
			return "Session not found. Start a new game?"
		"auth_failed":
			return "Authentication failed."
		"hmac_invalid":
			return "Connection tampered — reconnect."
		"frame_too_large":
			return "Message too large."
		"generation_failed":
			return "The dungeon master stumbled. Retry?"
		_:
			return "Error: %s" % code
