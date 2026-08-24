class_name FightView
extends Node2D

## Live side-view fight: mirrors the server re-sim locally (same seed/setup),
## drives hero/enemy renderers from sim state, and emits the claim for the
## server's hash verification. Inputs: WASD move · Shift/L hold guard · X/J attack
## (auto-riposte when riposte window open) · Space/C/K roll · P parry.

signal submit_ready(fight_id: String, payload: Dictionary)
signal finished()

const FightControllerScript := preload("res://scripts/fight_controller.gd")
const HeroRendererScript := preload("res://scripts/hero_renderer.gd")
const EnemyRendererScript := preload("res://scripts/enemy_renderer.gd")
const HudLib := preload("res://scripts/hud.gd")
const Sim := preload("res://scripts/sim_core.gd")

const PX_PER_UNIT := 0.096
const DEPTH_SCALE := 0.12
const TICK_HZ := 60.0
const WALK_SPEED := 150

var controller
var fight_id := ""
var enemy_max_hp := 40
var hero
var enemy
var _floor: Node2D = null
var _running := false
var _accum := 0.0
var _prev: Dictionary = {}
var bars := {}
var bar_bgs := {}
var _is_boss := false
var _prev_attack := false
var _prev_roll := false
var _prev_parry := false


func begin(spec: Dictionary, arena) -> void:
	_floor = arena
	fight_id = str(spec.get("fight_id", ""))
	var opp: Dictionary = spec.get("opponent_spec", {}).get("stats", {})
	var pspec: Dictionary = spec.get("player_spec", {})
	var bt: Array = spec.get("opponent_spec", {}).get("behavior_table", [])
	_is_boss = spec.get("opponent_spec", {}).get("is_boss", false)
	controller = FightControllerScript.new()
	controller.start_fight(
		int(spec.get("seed", 0)),
		int(pspec.get("attack", 10)), int(pspec.get("defense", 5)),
		int(opp.get("max_hp", 40)), int(opp.get("attack", 8)),
		int(opp.get("defense", 2)), int(opp.get("posture", 80)),
		3000, bt)
	enemy_max_hp = int(opp.get("max_hp", 40))
	hero = HeroRendererScript.new()
	add_child(hero)
	enemy = EnemyRendererScript.new()
	if _is_boss:
		enemy.frames_dir = "res://assets/art/gothicvania/church/wizard/idle-sprites"
		enemy.anim_name = "wizard-idle"
		enemy.sprite_scale = 2.5
	add_child(enemy)
	_build_bars()
	_running = true
	_prev = controller.sim_state.duplicate(true)


func _process(delta: float) -> void:
	if not _running:
		return
	_accum += delta
	while _accum >= 1.0 / TICK_HZ:
		_accum -= 1.0 / TICK_HZ
		_tick()


func _tick() -> void:
	if not _running or controller == null:
		return

	var move_x := (int(Input.is_key_pressed(KEY_D)) - int(Input.is_key_pressed(KEY_A))) * WALK_SPEED
	var move_y := (int(Input.is_key_pressed(KEY_S)) - int(Input.is_key_pressed(KEY_W))) * WALK_SPEED
	var guarding := Input.is_key_pressed(KEY_L) or Input.is_key_pressed(KEY_SHIFT)
	var action := "block" if guarding else "none"

	var attack_now := Input.is_key_pressed(KEY_X) or Input.is_key_pressed(KEY_J)
	if attack_now and not _prev_attack:
		_press_attack()
	_prev_attack = attack_now

	var roll_now := Input.is_key_pressed(KEY_SPACE) or Input.is_key_pressed(KEY_C) or Input.is_key_pressed(KEY_K)
	if roll_now and not _prev_roll:
		controller.queue_input("roll", 0, 0)
	_prev_roll = roll_now

	var parry_now := Input.is_key_pressed(KEY_P)
	if parry_now and not _prev_parry:
		controller.queue_input("parry", 0, 0)
	_prev_parry = parry_now

	controller.queue_input(action, move_x, move_y)
	controller.tick()
	var s: Dictionary = controller.sim_state
	_apply_delta_fx(s)
	_update_visuals(s)
	if guarding:
		hero.set_block_visual(true)
	_update_bars(s)
	_prev = s.duplicate(true)
	if controller.is_fight_over():
		_finish(s)


func _apply_delta_fx(s: Dictionary) -> void:
	if s["ehp"] < _prev.get("ehp", s["ehp"]) and enemy != null:
		enemy.flash()
	if s["php"] < _prev.get("php", s["php"]):
		flash_hero()
	if enemy != null:
		enemy.set_staggered(s["estate"] == Sim.STAGGERED)


func flash_hero() -> void:
	if hero == null or not is_inside_tree():
		return
	hero.modulate = Color(1.0, 0.45, 0.45)
	var timer := get_tree().create_timer(0.18)
	timer.timeout.connect(func():
		if is_instance_valid(hero):
			hero.modulate = Color.WHITE)


func _update_visuals(s: Dictionary) -> void:
	var vp := get_viewport_rect().size
	var base_x := _arena_origin_x()
	var mid_y := _ground_line()

	var hx: float = base_x + float(s["px"]) * PX_PER_UNIT
	var hy: float = clampf(mid_y + float(s["py"]) * DEPTH_SCALE, 80.0, vp.y - 16.0)
	hero.position = Vector2(hx, hy)
	hero.z_index = int(hy)

	var ex: float = base_x + float(s["ex"]) * PX_PER_UNIT
	var ey: float = clampf(mid_y + float(s["ey"]) * DEPTH_SCALE, 80.0, vp.y - 16.0)
	enemy.position = Vector2(ex, ey)
	enemy.z_index = int(ey)

	hero.set_facing(int(signf(float(s["ex"] - s["px"]))))
	enemy.flip_h = s["px"] > s["ex"]
	if s["php"] <= 0:
		hero.set_dead()
	else:
		hero.set_pstate(int(s["pstate"]))
	enemy.set_staggered(s["estate"] == Sim.STAGGERED)


func _arena_origin_x() -> float:
	return _floor.arena_x0() if _floor != null else 0.0


func _ground_line() -> float:
	return _floor.get_ground_y() if _floor != null else 364.0


func _finish(s: Dictionary) -> void:
	_running = false
	submit_ready.emit(fight_id, {
		"claimed_result": {"php": s["php"], "ehp": s["ehp"]},
		"state_hash": FightControllerScript.state_hash(s),
		"sim_version": "1",
	})
	finished.emit()


func _build_bars() -> void:
	var vp := Vector2(1152, 648)
	if is_inside_tree():
		vp = get_viewport_rect().size
	var defs := {
		"hp": {"pos": Vector2(16, 14), "color": Color(0.75, 0.15, 0.15)},
		"stamina": {"pos": Vector2(16, 36), "color": Color(0.20, 0.60, 0.90)},
		"posture": {"pos": Vector2(16, 58), "color": Color(0.85, 0.70, 0.20)},
		"enemy_hp": {"pos": Vector2(vp.x - 240, 14), "color": Color(0.50, 0.10, 0.10)},
	}
	for key in defs:
		var d: Dictionary = defs[key]
		var bg := _rect(d.pos, Vector2(224, 12), Color(0, 0, 0, 0.55), 10)
		bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bar_bgs[key] = bg
		bars[key] = _rect(d.pos + Vector2(2, 2), Vector2(220, 8), d.color, 11)


func _update_bars(s: Dictionary) -> void:
	var r: Dictionary = HudLib.bar_ratios(s, enemy_max_hp)
	for key in bars:
		bars[key].size.x = 220.0 * clampf(float(r[key]), 0.0, 1.0)


func _press_attack() -> void:
	if controller.sim_state.get("prip", 0) == 1:
		controller.queue_input("riposte", 0, 0)
	else:
		controller.queue_input("attack", 0, 0)


func _rect(pos: Vector2, size: Vector2, color: Color, z: int) -> ColorRect:
	var rect := ColorRect.new()
	rect.position = pos
	rect.size = size
	rect.color = color
	rect.z_index = z
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(rect)
	return rect
