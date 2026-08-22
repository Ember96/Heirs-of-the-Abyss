extends MainLoop

const Renderer = preload("res://scripts/floor_renderer.gd")

func _initialize():
	var args = OS.get_cmdline_user_args()
	var output_path = args[0] if args.size() > 0 else "/tmp/floor_render_out.txt"
	var a = Renderer.floor_layout(42, 12, 8)
	var b = Renderer.floor_layout(42, 12, 8)
	var deterministic = a == b
	var walls = 0
	for c in a:
		if c == 1:
			walls += 1
	var out = FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string("deterministic=%s cells=%d walls=%d\n" % [str(deterministic).to_lower(), a.size(), walls])
	out.close()

func _process(_delta: float) -> bool:
	return true
