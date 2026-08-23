class_name EnemyRenderer
extends AnimatedSprite2D

## Burning-ghoul enemy cycle with hit-flash and stagger feedback.

const FRAMES_DIR := "res://assets/art/gothicvania/church/burning-ghoul/sprites/v1"
const ANIM := "burning-ghoul"


func _ready() -> void:
	sprite_frames = SpriteFramesBuilder.build(FRAMES_DIR, [ANIM], ANIM + "-")
	scale = Vector2(2.0, 2.0)
	if sprite_frames.has_animation(ANIM):
		var ts := sprite_frames.get_frame_texture(ANIM, 0).get_size()
		offset = Vector2(0, -ts.y / 2.0)
		play(ANIM)


func flash() -> void:
	modulate = Color(1.0, 0.4, 0.4)
	var tween := create_tween()
	tween.tween_property(self, "modulate", Color.WHITE, 0.25)


func set_staggered(on: bool) -> void:
	speed_scale = 0.2 if on else 1.0
	modulate = Color(1.0, 0.55, 0.55) if on else Color.WHITE
