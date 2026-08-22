class_name StateSync
extends RefCounted


static func is_final_frame(frame: Dictionary) -> bool:
	return frame.get("frame_index", -1) == frame.get("frame_total", -2)


static func assemble_frames(frames: Array) -> Dictionary:
	for frame in frames:
		if is_final_frame(frame):
			return frame.get("state", {})
	return {}
