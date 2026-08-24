class_name FightController
extends RefCounted

const Sim = preload("res://scripts/sim_core.gd")
const Hmac = preload("res://scripts/hmac_utils.gd")


var sim_state: Dictionary
var fight_log: Array = []
var _buffer: Array = []


static func state_hash(state: Dictionary) -> String:
	var canonical := Hmac.canonical_json(state)
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(canonical.to_utf8_buffer())
	var hex := ""
	for b in ctx.finish():
		hex += "%02x" % b
	return hex


func start_fight(seed: int, player_atk: int = 10, player_def: int = 5,
		enemy_hp: int = 40, enemy_atk: int = 8, enemy_def: int = 2,
		enemy_posture: int = 80, enemy_x: int = 3000, behavior_table: Array = []) -> void:
	sim_state = Sim.new_fight(seed, player_atk, player_def, enemy_hp, enemy_atk, enemy_def, enemy_posture, enemy_x, behavior_table)
	fight_log = []
	_buffer = []


func queue_input(action: String, move_x: int = 0, move_y: int = 0) -> void:
	_buffer.append({"action": action, "move_x": move_x, "move_y": move_y})


func tick() -> Dictionary:
	var input := {"action": "none", "move_x": 0, "move_y": 0}
	if _buffer.size() > 0:
		input = _buffer.pop_front()
	sim_state = Sim.step(sim_state, input["move_x"], input["move_y"], input["action"])
	fight_log.append({
		"tick": sim_state["tick"],
		"action": input["action"],
		"params": {"move": [input["move_x"], input["move_y"]]},
	})
	return sim_state


func is_fight_over() -> bool:
	return sim_state["php"] <= 0 or sim_state["ehp"] <= 0


func submit_payload(sim_version: String) -> Dictionary:
	return {
		"fight_id": "f1",
		"claimed_result": {"php": sim_state["php"], "ehp": sim_state["ehp"]},
		"state_hash": state_hash(sim_state),
		"sim_version": sim_version,
	}
