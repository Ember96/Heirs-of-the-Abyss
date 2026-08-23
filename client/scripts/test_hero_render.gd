extends MainLoop

const Builder = preload("res://scripts/sprite_frames_builder.gd")

func _initialize():
	var args = OS.get_cmdline_user_args()
	var output_path = args[0] if args.size() > 0 else "/tmp/hero_out.txt"

	var hero := Builder.build("res://assets/art/hero/adventurer-frames", ["idle", "run", "jump", "fall", "slide"])
	var enemy := Builder.build(
		"res://assets/art/gothicvania/church/burning-ghoul/sprites/v1",
		["cycle"], "burning-ghoul-")

	var hero_ok: bool = hero.has_animation("adventurer-idle") \
		and hero.get_frame_count("adventurer-idle") > 0 \
		and hero.has_animation("adventurer-smrslt") \
		and hero.has_animation("adventurer-die")
	var enemy_ok: bool = enemy.has_animation("burning-ghoul") \
		and enemy.get_frame_count("burning-ghoul") >= 6

	var out := FileAccess.open(output_path, FileAccess.WRITE)
	out.store_string("hero=%s enemy=%s\n" % [str(hero_ok).to_lower(), str(enemy_ok).to_lower()])
	out.close()

func _process(_delta: float) -> bool:
	return true
