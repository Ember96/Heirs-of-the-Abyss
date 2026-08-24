extends MainLoop

const FightViewScript = preload("res://scripts/fight_view.gd")

var _done := false

func _initialize():
	var args = OS.get_cmdline_user_args()
	var out_path = args[0] if args.size() > 0 else "/tmp/fv.txt"

	var fv = FightViewScript.new()
	var captured = {}
	fv.submit_ready.connect(func(fid, payload):
		captured["fid"] = fid
		captured["payload"] = payload)

	fv.begin({
		"fight_id": "f-t",
		"seed": 7,
		"opponent_spec": {"stats": {"max_hp": 5, "attack": 1, "defense": 0, "posture": 10}, "behavior_table": []},
		"player_spec": {"attack": 99, "defense": 50},
	}, null)
	for i in range(5):  # close the gap — player 500/t + enemy approach 90/t converge by tick ~4
		fv.controller.queue_input("none", 500, 0)
	fv.controller.queue_input("attack", 0, 0)

	for i in range(300):
		fv._tick()
		if not fv._running:
			break
	fv.free()

	var ok: bool = captured.has("fid") \
		and int(captured["payload"]["claimed_result"]["ehp"]) <= 0 \
		and str(captured["payload"]["sim_version"]) == "1"

	var out := FileAccess.open(out_path, FileAccess.WRITE)
	out.store_string("submitted=%s ehp=%s\n" % [str(ok).to_lower(), str(captured["payload"]["claimed_result"]["ehp"])])
	out.close()
	print("harness: submitted=%s" % str(ok).to_lower())

func _process(_delta: float) -> bool:
	return true
