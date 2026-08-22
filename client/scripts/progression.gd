class_name BossProgression
extends RefCounted


static func unlock_or_level(skills: Array, skill_id: String) -> Array:
	var result := skills.duplicate()
	for i in range(result.size()):
		if result[i]["id"] == skill_id:
			result[i]["level"] = result[i]["level"] + 1
			return result
	result.append({"id": skill_id, "level": 1})
	return result
