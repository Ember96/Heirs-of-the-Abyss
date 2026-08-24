class_name SimCore

const IDLE := 0
const ROLLING := 1
const GUARDING := 2
const ATTACKING := 3
const STAGGERED := 4
const PARRYING := 5

const STAMINA_MAX := 100
const STAMINA_ROLL := 18
const STAMINA_ATTACK := 22
const STAMINA_BLOCK := 5
const STAMINA_PARRY := 15
const STAMINA_REGEN_PER_SEC := 27
const POSTURE_MAX := 100
const POSTURE_DECAY_PER_SEC := 10
const POSTURE_BREAK_TICKS := 150
const ROLL_TICKS := 13
const ATTACK_TICKS := 10
const ATTACK_RANGE := 1000
const ATTACK_RANGE_SQ := ATTACK_RANGE * ATTACK_RANGE
const STRIKE_RANGE := 700
const STRIKE_RANGE_SQ := STRIKE_RANGE * STRIKE_RANGE
const ENEMY_SPEED := 90
const PARRY_STARTUP_TICKS := 10
const PARRY_ACTIVE_TICKS := 12
const PARRY_TOTAL_TICKS := PARRY_STARTUP_TICKS + PARRY_ACTIVE_TICKS
const ENEMY_ATTACK_BASE := 60
const MASK32 := 0xFFFFFFFF

static func xorshift32(state: int) -> int:
	state = (state ^ ((state << 13) & MASK32)) & MASK32
	state = (state ^ (state >> 17)) & MASK32
	state = (state ^ ((state << 5) & MASK32)) & MASK32
	return state & MASK32

static func new_fight(seed: int, player_atk: int, player_def: int,
		enemy_hp: int, enemy_atk: int, enemy_def: int,
		enemy_posture: int, enemy_x: int, behavior_table: Array = []) -> Dictionary:
	return {
		"tick": 0,
		"px": 0, "py": 0, "php": 100, "pstam": STAMINA_MAX, "ppost": POSTURE_MAX,
		"pstate": IDLE, "pticks": 0, "piframe": 0, "preg": 0, "ppreg": 0,
		"ex": enemy_x, "ey": 0, "ehp": enemy_hp, "epost": enemy_posture,
		"epost_base": enemy_posture, "estate": IDLE, "eticks": 0, "ecooldown": ENEMY_ATTACK_BASE,
		"prip": 0, "eaware": 0, "efx": 0, "efy": 0,
		"patk": player_atk, "pdef": player_def, "eatk": enemy_atk, "edef": enemy_def,
		"bt": behavior_table.duplicate(),
		"rng": seed & MASK32,
	}

static func step(state: Dictionary, move_x: int, move_y: int, action: String) -> Dictionary:
	var s := state.duplicate(true)
	s["tick"] = s["tick"] + 1

	if s["piframe"] > 0:
		s["piframe"] = s["piframe"] - 1
	if s["pticks"] > 0:
		s["pticks"] = s["pticks"] - 1
		if s["pticks"] == 0:
			s["pstate"] = IDLE
	if s["eticks"] > 0:
		s["eticks"] = s["eticks"] - 1
		if s["eticks"] == 0:
			s["estate"] = IDLE
			s["prip"] = 0

	s["px"] = s["px"] + move_x
	s["py"] = s["py"] + move_y

	if action != "block" and s["pstate"] == GUARDING:
		s["pstate"] = IDLE

	if action == "roll" and s["pstate"] == IDLE and s["pstam"] >= STAMINA_ROLL:
		s["pstam"] = s["pstam"] - STAMINA_ROLL
		s["pstate"] = ROLLING
		s["pticks"] = ROLL_TICKS
		s["piframe"] = ROLL_TICKS
	elif action == "attack" and s["pstate"] == IDLE and s["pstam"] >= STAMINA_ATTACK:
		s["pstam"] = s["pstam"] - STAMINA_ATTACK
		s["pstate"] = ATTACKING
		s["pticks"] = ATTACK_TICKS
		var ddx := int(s["px"]) - int(s["ex"])
		var ddy := int(s["py"]) - int(s["ey"])
		if ddx * ddx + ddy * ddy <= ATTACK_RANGE_SQ:
			var dmg := maxi(1, s["patk"] - s["edef"])
			if s["prip"] == 1:
				dmg = dmg * 2
				s["prip"] = 0
			elif s["estate"] == STAGGERED:
				dmg = (dmg * 3 + 1) >> 1
			elif s["efx"] * ddx + s["efy"] * ddy < 0:
				dmg = (dmg * 3 + 1) >> 1
			s["ehp"] = s["ehp"] - dmg
			s["epost"] = s["epost"] - dmg
			s["eaware"] = 1
			if s["epost"] <= 0:
				s["estate"] = STAGGERED
				s["eticks"] = POSTURE_BREAK_TICKS
				s["epost"] = s["epost_base"]
	elif action == "parry" and s["pstate"] == IDLE and s["pstam"] >= STAMINA_PARRY:
		s["pstam"] = s["pstam"] - STAMINA_PARRY
		s["pstate"] = PARRYING
		s["pticks"] = PARRY_TOTAL_TICKS
	elif action == "block":
		s["pstate"] = GUARDING

	if s["estate"] == IDLE:
		var ddx := int(s["px"]) - int(s["ex"])
		var ddy := int(s["py"]) - int(s["ey"])
		if ddx * ddx + ddy * ddy > STRIKE_RANGE_SQ:
			if ddx != 0:
				var step_x := mini(ENEMY_SPEED, absi(ddx))
				s["ex"] = s["ex"] + (step_x if ddx > 0 else -step_x)
				s["efx"] = 1 if ddx > 0 else -1
			if ddy != 0:
				var step_y := mini(ENEMY_SPEED, absi(ddy))
				s["ey"] = s["ey"] + (step_y if ddy > 0 else -step_y)
				s["efy"] = 1 if ddy > 0 else -1
		else:
			s["ecooldown"] = s["ecooldown"] - 1
			if s["ecooldown"] <= 0:
				s["rng"] = xorshift32(s["rng"])
				s["ecooldown"] = ENEMY_ATTACK_BASE + (s["rng"] % 60)
				s["eaware"] = 1
				s["efx"] = 1 if ddx > 0 else -1
				s["efy"] = 1 if ddy > 0 else -1
				var edmg := int(s["eatk"])
				var bt: Array = s.get("bt", [])
				if bt.size() > 0:
					s["rng"] = xorshift32(s["rng"])
					var total := 0
					for b in bt:
						total += int(b["weight"])
					var pick := int(s["rng"] % total)
					var acc := 0
					for b in bt:
						acc += int(b["weight"])
						if pick < acc:
							edmg = int(b["damage"])
							break
				var dmg := maxi(1, edmg - s["pdef"])
				if s["piframe"] > 0:
					pass
				elif s["pstate"] == PARRYING and s["pticks"] <= PARRY_ACTIVE_TICKS:
					s["estate"] = STAGGERED
					s["eticks"] = POSTURE_BREAK_TICKS
					s["epost"] = s["epost_base"]
					s["prip"] = 1
				elif s["pstate"] == GUARDING:
					var reduced := maxi(1, dmg >> 1)
					s["php"] = s["php"] - reduced
					s["pstam"] = maxi(0, s["pstam"] - STAMINA_BLOCK)
				else:
					s["php"] = s["php"] - dmg

	if s["pstate"] == IDLE:
		s["preg"] = s["preg"] + STAMINA_REGEN_PER_SEC
		while s["preg"] >= 60:
			s["preg"] = s["preg"] - 60
			if s["pstam"] < STAMINA_MAX:
				s["pstam"] = s["pstam"] + 1

	s["ppreg"] = s["ppreg"] + POSTURE_DECAY_PER_SEC
	while s["ppreg"] >= 60:
		s["ppreg"] = s["ppreg"] - 60
		if s["ppost"] < POSTURE_MAX:
			s["ppost"] = s["ppost"] + 1

	return s
