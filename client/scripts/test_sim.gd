extends MainLoop

const Sim = preload("res://scripts/sim_core.gd")

func _initialize():
	var args = OS.get_cmdline_user_args()
	if args.size() < 2:
		printerr("Usage: godot --headless --path project -- test_sim.gd -- input.json output.json")
		return
	var input_path = args[0]
	var output_path = args[1]
	var f = FileAccess.open(input_path, FileAccess.READ)
	var cases = JSON.parse_string(f.get_as_text())
	f.close()
	var results = []
	for c in cases:
		var state = Sim.new_fight(c["seed"], c["patk"], c["pdef"], c["ehp"], c["eatk"], c["edef"], c["epost"], c["ex"])
		for m in c["moves"]:
			state = Sim.step(state, m[0], m[1], m[2])
		results.append(state)
	var out = FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string(JSON.stringify(results))
	out.close()

func _process(_delta: float) -> bool:
	return true
