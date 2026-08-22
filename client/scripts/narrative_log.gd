class_name NarrativeLog
extends RefCounted


static func escape_bbcode(text: String) -> String:
	return text.replace("[", "[lb]").replace("]", "[rb]")


static func sanitize(text: String) -> String:
	var cleaned := ""
	for i in range(text.length()):
		var c = text[i]
		var code = c.unicode_at(0)
		if code >= 0x20 or c == "\t" or c == "\n":
			cleaned += c
	return escape_bbcode(cleaned)
