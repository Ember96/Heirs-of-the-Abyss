class_name FloorRenderer
extends Node2D
## Side-view gothic arena renderer (Wave 8, Option A pivot).
##
## Same node/API contract as the previous isometric implementation:
##   render_floor(seed_value, cols, rows)
## `static floor_layout` is preserved byte-for-byte — the headless conformance
## harness (scripts/test_floor_render.gd) asserts its determinism directly.
## Legacy TileMapLayer children from main.tscn are freed on ready.

const ART := "res://assets/art/"

@onready var _legacy_layers := [$FloorLayer, $WallsLayer, $PropsLayer]

var _ground_y := 0.0
var _arena_w := 0.0
var _arena_x0 := 0.0


static func xorshift32(state: int) -> int:
	state = (state ^ ((state << 13) & 0xFFFFFFFF)) & 0xFFFFFFFF
	state = (state ^ (state >> 17)) & 0xFFFFFFFF
	state = (state ^ ((state << 5) & 0xFFFFFFFF)) & 0xFFFFFFFF
	return state & 0xFFFFFFFF


static func floor_layout(seed_value: int, width: int, height: int) -> Array:
	var cells: Array = []
	var state := seed_value & 0xFFFFFFFF
	for x in range(width):
		for y in range(height):
			var is_wall := x == 0 or y == 0 or x == width - 1 or y == height - 1
			state = xorshift32(state)
			if not is_wall and state % 10 == 0:
				is_wall = true
			cells.append(1 if is_wall else 0)
	return cells


func _ready() -> void:
	for layer in _legacy_layers:
		layer.visible = false
		layer.queue_free()


func get_ground_y() -> float:
	return _ground_y


func arena_width() -> float:
	return _arena_w


func arena_x0() -> float:
	return _arena_x0


func render_floor(seed_value: int, width: int, height: int) -> void:
	for child in get_children():
		child.queue_free()

	var vp := get_viewport_rect().size
	_ground_y = vp.y * 0.78
	_arena_w = width * 96.0
	_arena_x0 = maxf(0.0, (vp.x - _arena_w) / 2.0)

	_build_backdrop(seed_value, vp)
	_build_ground(vp)
	_build_room_ticks(vp, width)


func _find_tex(dir_rel: String, prefix: String) -> Texture2D:
	var stack: Array[String] = [ART + dir_rel]
	while not stack.is_empty():
		var dpath: String = stack.pop_back()
		var dir := DirAccess.open(dpath)
		if dir == null:
			continue
		dir.list_dir_begin()
		var file := dir.get_next()
		while file != "":
			var full := dpath + "/" + file
			if dir.current_is_dir():
				if not file.begins_with("."):
					stack.push_back(full)
			elif file.begins_with(prefix) and file.ends_with(".png"):
				return load(full)
			file = dir.get_next()
		dir.list_dir_end()
	return null


func _cover(sprite: Sprite2D, target: Vector2, align_bottom: bool) -> void:
	var ts := sprite.texture.get_size()
	if ts.x <= 0 or ts.y <= 0:
		return
	var s: float = max(target.x / ts.x, target.y / ts.y)
	sprite.scale = Vector2(s, s)
	var size := ts * s
	var cy := target.y - size.y / 2.0 if align_bottom else target.y / 2.0
	sprite.position = Vector2(target.x / 2.0, cy)


func _sprite(tex: Texture2D, pos: Vector2, z: int, tint := Color.WHITE) -> Sprite2D:
	var sp := Sprite2D.new()
	sp.texture = tex
	sp.position = pos
	sp.z_index = z
	sp.modulate = tint
	add_child(sp)
	return sp


func _rect(pos: Vector2, size: Vector2, color: Color, z: int) -> ColorRect:
	var r := ColorRect.new()
	r.position = pos
	r.size = size
	r.color = color
	r.z_index = z
	add_child(r)
	return r


func _build_backdrop(seed_value: int, vp: Vector2) -> void:
	_rect(Vector2.ZERO, vp, Color(0.039, 0.039, 0.071), -10)

	var moon := _find_tex("gothicvania/cemetery", "bg-moon")
	if moon:
		var sp := _sprite(moon, Vector2(vp.x * 0.72, vp.y * 0.22), -9)
		sp.flip_h = seed_value % 2 == 1

	var mountains := _find_tex("gothicvania/cemetery", "bg-mountains")
	if mountains:
		var sp := _sprite(mountains, Vector2.ZERO, -8, Color(0.6, 0.6, 0.68))
		_cover(sp, Vector2(vp.x, vp.y), true)

	var church_bg := _find_tex("gothicvania/church/environment", "backgrounds")
	var yard := _find_tex("gothicvania/cemetery", "bg-graveyard")
	var mid := yard if yard else church_bg
	if mid:
		var sp := _sprite(mid, Vector2.ZERO, -7, Color(0.78, 0.78, 0.82))
		_cover(sp, Vector2(vp.x, _ground_y + 8.0), true)


func _build_ground(vp: Vector2) -> void:
	var band_h := vp.y - _ground_y
	_rect(Vector2(0, _ground_y), Vector2(vp.x, band_h), Color(0.055, 0.055, 0.078), -5)
	_rect(Vector2(0, _ground_y), Vector2(vp.x, 3), Color(0.16, 0.16, 0.20), -4)

	var column := _find_tex("gothicvania/church/environment", "column")
	if column:
		var cs := column.get_size()
		if cs.y > 0:
			var s: float = (band_h * 0.92) / cs.y
			var scaled := cs * s
			var step := scaled.x + 56.0
			var x := 40.0
			while x < vp.x:
				var sp := _sprite(column, Vector2(x, _ground_y + band_h / 2.0), -6, Color(0.85, 0.85, 0.9))
				sp.scale = Vector2(s, s)
				x += step


func _build_room_ticks(vp: Vector2, width: int) -> void:
	var tick_color := Color(0.55, 0.5, 0.65, 0.13)
	var tick_h := vp.y * 0.11
	for i in range(width + 1):
		var x := _arena_x0 + i * (_arena_w / width) - 1.0
		_rect(Vector2(x, _ground_y - tick_h), Vector2(2, tick_h), tick_color, -3)
