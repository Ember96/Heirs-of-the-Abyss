extends MainLoop

const Fight = preload("res://scripts/fight_controller.gd")

const INPUTS = [
	["none", 500, 0], ["none", 500, 0], ["attack", 0, 0],
	["roll", 0, 0], ["attack", 0, 0], ["block", 0, 0],
	["attack", 0, 0], ["none", 500, 0], ["attack", 0, 0],
	["roll", 0, 0], ["attack", 0, 0], ["attack", 0, 0],
]


func _run_fight() -> Dictionary:
	var controller = Fight.new()
	controller.start_fight(42)
	for inp in INPUTS:
		controller.queue_input(inp[0], inp[1], inp[2])
	var ticks := 0
	while not controller.is_fight_over() and ticks < 600:
		controller.tick()
		ticks += 1
	return {
		"hash": controller.submit_payload("1.0.0")["state_hash"],
		"ticks": ticks,
		"php": controller.sim_state["php"],
		"ehp": controller.sim_state["ehp"],
		"log_len": controller.fight_log.size(),
	}


func _initialize():
	var args = OS.get_cmdline_user_args()
	var output_path = args[0] if args.size() > 0 else "/tmp/fight_out.txt"
	var a = _run_fight()
	var b = _run_fight()
	var deterministic = a["hash"] == b["hash"]
	var out = FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string("deterministic=%s hash=%s ticks=%d php=%d ehp=%d log=%d\n" % [
		str(deterministic).to_lower(), a["hash"], a["ticks"], a["php"], a["ehp"], a["log_len"],
	])
	out.close()


func _process(_delta: float) -> bool:
	return true
