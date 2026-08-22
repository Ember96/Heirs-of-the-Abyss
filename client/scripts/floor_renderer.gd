class_name FloorRenderer
extends Node2D

const TILE_SIZE := Vector2i(64, 32)
const FLOOR_TILE := Vector2i(0, 0)
const WALL_TILE := Vector2i(1, 0)

@onready var floor_layer: TileMapLayer = $FloorLayer
@onready var walls_layer: TileMapLayer = $WallsLayer
@onready var props_layer: TileMapLayer = $PropsLayer


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
	_setup_tilesets()


func _setup_tilesets() -> void:
	var ts := _make_tileset()
	floor_layer.tile_set = ts
	walls_layer.tile_set = ts
	props_layer.tile_set = ts
	floor_layer.y_sort_enabled = false
	walls_layer.y_sort_enabled = false
	props_layer.y_sort_enabled = true


func _make_tileset() -> TileSet:
	var ts := TileSet.new()
	ts.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	ts.tile_size = TILE_SIZE
	var src := TileSetAtlasSource.new()
	src.texture = _make_atlas_texture()
	src.texture_region_size = TILE_SIZE
	src.create_tile(FLOOR_TILE)
	src.create_tile(WALL_TILE)
	ts.add_source(src)
	return ts


func _make_atlas_texture() -> ImageTexture:
	var img := Image.create(TILE_SIZE.x * 2, TILE_SIZE.y, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	_draw_diamond(img, 0, 0, Color(0.18, 0.18, 0.22, 1.0))
	_draw_diamond(img, TILE_SIZE.x, 0, Color(0.45, 0.18, 0.18, 1.0))
	return ImageTexture.create_from_image(img)


func _draw_diamond(img: Image, ox: int, oy: int, color: Color) -> void:
	for y in range(TILE_SIZE.y):
		var half: int = y if y < TILE_SIZE.y / 2 else TILE_SIZE.y - 1 - y
		for x in range(TILE_SIZE.x / 2 - half, TILE_SIZE.x / 2 + half):
			img.set_pixel(ox + x, oy + y, color)


func render_floor(seed_value: int, width: int, height: int) -> void:
	floor_layer.clear()
	walls_layer.clear()
	var cells := floor_layout(seed_value, width, height)
	var i := 0
	for x in range(width):
		for y in range(height):
			if cells[i] == 1:
				walls_layer.set_cell(Vector2i(x, y), 0, WALL_TILE)
			else:
				floor_layer.set_cell(Vector2i(x, y), 0, FLOOR_TILE)
			i += 1
