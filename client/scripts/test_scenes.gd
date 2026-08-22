extends MainLoop

const Log = preload("res://scripts/narrative_log.gd")
const Hud = preload("res://scripts/hud.gd")
const Prog = preload("res://scripts/progression.gd")


func _initialize():
	var args = OS.get_cmdline_user_args()
	var output_path = args[0] if args.size() > 0 else "/tmp/scenes_out.txt"

	var evil := "[color=red]evil[/color]"
	var escaped := Log.escape_bbcode(evil)
	var escape_ok: bool = "[color" not in escaped and "[/color]" not in escaped

	var ratios := Hud.bar_ratios({"php": 50, "pstam": 100, "ppost": 0, "ehp": 20})
	var hud_ok: bool = ratios["hp"] == 0.5 and ratios["stamina"] == 1.0 and ratios["enemy_hp"] == 0.5

	var skills: Array = []
	skills = Prog.unlock_or_level(skills, "dash")
	var level1: bool = skills[0]["level"] == 1
	skills = Prog.unlock_or_level(skills, "dash")
	var level2: bool = skills[0]["level"] == 2

	var out := FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string("escape=%s hud=%s unlock=%s level=%s\n" % [
		str(escape_ok).to_lower(), str(hud_ok).to_lower(), str(level1).to_lower(), str(level2).to_lower(),
	])
	out.close()


func _process(_delta: float) -> bool:
	return true
