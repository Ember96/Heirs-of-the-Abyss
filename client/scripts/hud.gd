class_name CombatHud
extends RefCounted


static func bar_ratios(sim_state: Dictionary, enemy_max_hp: int = 40) -> Dictionary:
	return {
		"hp": float(sim_state["php"]) / 100.0,
		"stamina": float(sim_state["pstam"]) / 100.0,
		"posture": float(sim_state["ppost"]) / 100.0,
		"enemy_hp": float(sim_state["ehp"]) / float(max(enemy_max_hp, 1)),
	}
