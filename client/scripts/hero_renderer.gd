class_name HeroRenderer
extends AnimatedSprite2D

## Drives the player character's visual state machine from sim states.
## Roll uses `smrslt`; guard/parry reuse crouch frames with stance tints.

const Sim := preload("res://scripts/sim_core.gd")
const FRAMES_DIR := "res://assets/art/hero/adventurer-frames"
const SPRITE_SCALE := 2.0

var _attack_index := 0


func _ready() -> void:
	sprite_frames = SpriteFramesBuilder.build(FRAMES_DIR, ["idle", "run", "jump", "fall", "slide"])
	scale = Vector2(SPRITE_SCALE, SPRITE_SCALE)
	if sprite_frames.has_animation("adventurer-idle"):
		var ts := sprite_frames.get_frame_texture("adventurer-idle", 0).get_size()
		offset = Vector2(0, -ts.y / 2.0)
		play("adventurer-idle")


func set_pstate(pstate: int) -> void:
	match pstate:
		Sim.IDLE:
			_play_loop("adventurer-idle")
		Sim.ROLLING:
			_play_once("adventurer-smrslt")
		Sim.GUARDING:
			_stance("adventurer-crouch", Color(0.7, 0.85, 1.0))
		Sim.ATTACKING:
			_play_once(_next_attack())
		Sim.STAGGERED:
			_play_once("adventurer-hurt")
		Sim.PARRYING:
			_stance("adventurer-crouch", Color(1.0, 0.9, 0.4))
		_:
			_play_loop("adventurer-idle")


func set_dead() -> void:
	modulate = Color.WHITE
	if sprite_frames.has_animation("adventurer-die"):
		play("adventurer-die")


func set_facing(facing_dir: int) -> void:
	flip_h = facing_dir < 0


func _next_attack() -> String:
	_attack_index = (_attack_index % 3) + 1
	return "adventurer-attack%d" % _attack_index


func _play_loop(anim: String) -> void:
	modulate = Color.WHITE
	if sprite_frames.has_animation(anim):
		play(anim)


func _play_once(anim: String) -> void:
	modulate = Color.WHITE
	if sprite_frames.has_animation(anim):
		play(anim)


func _stance(anim: String, tint: Color) -> void:
	modulate = tint
	if sprite_frames.has_animation(anim):
		play(anim)
	else:
		_play_loop("adventurer-idle")
