class_name EnemyRenderer
extends AnimatedSprite2D

## Enemy sprite with hit-flash and stagger feedback.
## Configure `frames_dir` / `anim_name` / `sprite_scale` before adding to the
## tree to swap skins (e.g. necromancer boss vs burning-ghoul regular).

var frames_dir := "res://assets/art/gothicvania/church/burning-ghoul/sprites/v1"
var anim_name := "burning-ghoul"
var sprite_scale := 2.0


func _ready() -> void:
	sprite_frames = SpriteFramesBuilder.build(frames_dir, [anim_name], anim_name + "-")
	scale = Vector2(sprite_scale, sprite_scale)
	if sprite_frames.has_animation(anim_name):
		var ts := sprite_frames.get_frame_texture(anim_name, 0).get_size()
		offset = Vector2(0, -ts.y / 2.0)
		play(anim_name)


func flash() -> void:
	modulate = Color(1.0, 0.4, 0.4)
	if not is_inside_tree():
		return
	var tween := create_tween()
	tween.tween_property(self, "modulate", Color.WHITE, 0.25)


func set_staggered(on: bool) -> void:
	speed_scale = 0.2 if on else 1.0
	modulate = Color(1.0, 0.55, 0.55) if on else Color.WHITE
