extends MainLoop

const Err = preload("res://scripts/error_messages.gd")
const Sync = preload("res://scripts/state_sync.gd")


func _initialize():
	var args = OS.get_cmdline_user_args()
	var output_path = args[0] if args.size() > 0 else "/tmp/sync_out.txt"

	var busy_ok: bool = Err.message_for("busy") == "The dungeon is still thinking…"
	var terminal_ok: bool = Err.message_for("session_terminal") == "Your run is over."
	var unknown_ok: bool = Err.message_for("nope").begins_with("Error: ")

	var frames := [
		{"frame_index": 1, "frame_total": 2, "state": {"partial": 1}},
		{"frame_index": 2, "frame_total": 2, "state": {"final": 42}},
	]
	var assembled := Sync.assemble_frames(frames)
	var sync_ok: bool = assembled == {"final": 42}

	var out := FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string("busy=%s terminal=%s unknown=%s sync=%s\n" % [
		str(busy_ok).to_lower(), str(terminal_ok).to_lower(), str(unknown_ok).to_lower(), str(sync_ok).to_lower(),
	])
	out.close()


func _process(_delta: float) -> bool:
	return true
