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
	_ground_y = vp.y * 0.54
	_arena_w = width * 96.0
	_arena_x0 = maxf(0.0, (vp.x - _arena_w) / 2.0)

	_build_backdrop(seed_value, vp)


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
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(r)
	return r


func _build_backdrop(seed_value: int, vp: Vector2) -> void:
	_rect(Vector2.ZERO, vp, Color(0.039, 0.039, 0.071), -10)

	var floor_tex := _find_tex("tiles", "arena-floor")
	if floor_tex:
		var sp := _sprite(floor_tex, Vector2(vp.x / 2.0, vp.y / 2.0), -8, Color(0.28, 0.25, 0.35))
		_cover(sp, vp, false)

	_rect(Vector2(0, 0), Vector2(vp.x, 64), Color(0.02, 0.02, 0.04, 0.82), -7)

