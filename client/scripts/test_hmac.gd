extends MainLoop

func _initialize():
	var args = OS.get_cmdline_user_args()
	if args.size() < 2:
		printerr("Usage: godot --headless --path project -- test_hmac.gd -- input.json output.txt")
		return
	var input_path = args[0]
	var output_path = args[1]
	var f = FileAccess.open(input_path, FileAccess.READ)
	var input = JSON.parse_string(f.get_as_text())
	f.close()
	var key = HmacUtils.hex_to_bytes(input["key_hex"])
	var canonical = HmacUtils.canonical_json(input["payload"])
	var msg = "%s|%s|%d|%s" % [input["type"], input["id"], input["seq"], canonical]
	var sig = HmacUtils.hmac_sha256_hex(key, msg.to_utf8_buffer())
	var out = FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string(sig)
	out.close()

func _process(_delta: float) -> bool:
	return true
