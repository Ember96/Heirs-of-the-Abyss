class_name SpriteFramesBuilder
extends RefCounted

## Builds a SpriteFrames resource from a flat directory of numbered PNG frames
## named `<prefix>-<INDEX>.png`. Prefix may itself contain dashes; the trailing
## numeric group is treated as the frame index.

const LOOP_DEFAULTS := ["idle", "run", "jump", "fall", "slide", "cycle", "walk"]


static func build(dir_path: String, force_loop: Array = [], only_prefix: String = "") -> SpriteFrames:
	var frames := SpriteFrames.new()
	var groups: Dictionary = {}
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return frames

	dir.list_dir_begin()
	var file := dir.get_next()
	while file != "":
		if file.ends_with(".png") and (only_prefix == "" or file.begins_with(only_prefix)):
			var parsed := _split(file)
			if not parsed.is_empty():
				if not groups.has(parsed[0]):
					groups[parsed[0]] = []
				groups[parsed[0]].append([int(parsed[1]), file])
		file = dir.get_next()
	dir.list_dir_end()

	for anim_name in groups:
		var entries: Array = groups[anim_name]
		entries.sort_custom(func(a, b): return a[0] < b[0])
		frames.add_animation(anim_name)
		frames.set_animation_speed(anim_name, 12.0)
		frames.set_animation_loop(anim_name, _is_loop(anim_name, force_loop))
		for entry in entries:
			frames.add_frame(anim_name, load(dir_path + "/" + entry[1]))

	if frames.has_animation("default"):
		frames.remove_animation("default")
	return frames


static func _split(file: String) -> Array:
	var base := file.trim_suffix(".png")
	var idx := base.rfind("-")
	if idx == -1:
		return []
	var tail := base.substr(idx + 1)
	if not tail.is_valid_int():
		return []
	return [base.substr(0, idx), int(tail)]


static func _is_loop(name: String, force_loop: Array) -> bool:
	for n in force_loop:
		if name.begins_with(n):
			return true
	for n in LOOP_DEFAULTS:
		if name.begins_with(n):
			return true
	return false
