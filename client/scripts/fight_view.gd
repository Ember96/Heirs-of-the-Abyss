class_name FightView
extends Node2D

## Live side-view fight: mirrors the server re-sim locally (same seed/setup),
## drives hero/enemy renderers from sim state, and emits the claim for the
## server's hash verification. Inputs: A/D move · S/L hold guard · X/J attack
## (auto-riposte when riposte window open) · C/K roll · P parry.

signal submit_ready(fight_id: String, payload: Dictionary)
signal finished()

const FightControllerScript := preload("res://scripts/fight_controller.gd")
const HeroRendererScript := preload("res://scripts/hero_renderer.gd")
const EnemyRendererScript := preload("res://scripts/enemy_renderer.gd")
const HudLib := preload("res://scripts/hud.gd")
const Sim := preload("res://scripts/sim_core.gd")

const PX_PER_UNIT := 0.096
const TICK_HZ := 60.0

var controller
var fight_id := ""
var enemy_max_hp := 40
var hero
var enemy
var _floor: Node2D = null
var _running := false
var _accum := 0.0
var _prev: Dictionary = {}
var _held := {"left": false, "right": false, "guard": false}
var bars := {}


func begin(spec: Dictionary, arena) -> void:
	_floor = arena
	fight_id = str(spec.get("fight_id", ""))
	var opp: Dictionary = spec.get("opponent_spec", {}).get("stats", {})
	var pspec: Dictionary = spec.get("player_spec", {})
	var bt: Array = spec.get("opponent_spec", {}).get("behavior_table", [])
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
	var move_x := (int(_held.right) - int(_held.left)) * 500
	var action := "block" if _held.guard else "none"
	controller.queue_input(action, move_x, 0)
	controller.tick()
	var s: Dictionary = controller.sim_state
	_apply_delta_fx(s)
	_update_visuals(s)
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
	var base_x := _arena_origin_x()
	var ground := _ground_line()
	hero.position = Vector2(base_x + s["px"] * PX_PER_UNIT, ground)
	enemy.position = Vector2(base_x + s["ex"] * PX_PER_UNIT, ground)
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
	return _floor.get_ground_y() if _floor != null else 400.0


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
		_rect(d.pos, Vector2(224, 12), Color(0, 0, 0, 0.55), 10)
		bars[key] = _rect(d.pos + Vector2(2, 2), Vector2(220, 8), d.color, 11)


func _update_bars(s: Dictionary) -> void:
	var r: Dictionary = HudLib.bar_ratios(s, enemy_max_hp)
	for key in bars:
		bars[key].size.x = 220.0 * clampf(float(r[key]), 0.0, 1.0)


func _unhandled_input(event: InputEvent) -> void:
	if not _running or controller == null:
		return
	if event is InputEventKey:
		var pressed: bool = event.pressed and not event.echo
		match event.physical_keycode:
			KEY_A:
				_held.left = event.pressed
			KEY_D:
				_held.right = event.pressed
			KEY_S, KEY_L:
				_held.guard = event.pressed
			KEY_X, KEY_J:
				if pressed:
					_press_attack()
			KEY_C, KEY_K:
				if pressed:
					controller.queue_input("roll", 0, 0)
			KEY_P:
				if pressed:
					controller.queue_input("parry", 0, 0)


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
