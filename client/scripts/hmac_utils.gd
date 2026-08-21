class_name HmacUtils

static func canonical_json(v: Variant) -> String:
	match typeof(v):
		TYPE_NIL: return "null"
		TYPE_BOOL: return "true" if v else "false"
		TYPE_INT, TYPE_FLOAT: return str(v)
		TYPE_STRING: return _escape_string(v)
		TYPE_DICTIONARY:
			var keys = v.keys()
			keys.sort()
			var parts = PackedStringArray()
			for k in keys:
				parts.append("\"%s\":%s" % [str(k), canonical_json(v[k])])
			return "{%s}" % ",".join(parts)
		TYPE_ARRAY:
			var parts = PackedStringArray()
			for item in v:
				parts.append(canonical_json(item))
			return "[%s]" % ",".join(parts)
		_: return str(v)

static func _escape_string(s: String) -> String:
	var out = ""
	for i in range(s.length()):
		var code = s[i].unicode_at(0)
		match code:
			0x22: out += '\\"'
			0x5c: out += '\\\\'
			0x08: out += '\\b'
			0x09: out += '\\t'
			0x0a: out += '\\n'
			0x0c: out += '\\f'
			0x0d: out += '\\r'
			_:
				if code < 0x20: out += "\\u%04x" % code
				elif code <= 0x7f: out += s[i]
				else: out += "\\u%04x" % code
	return "\"%s\"" % out

static func hmac_sha256_hex(key: PackedByteArray, msg: PackedByteArray) -> String:
	var bsz = 64
	var k = key.duplicate()
	if k.size() > bsz: k = _sha256(k)
	k.resize(bsz)
	var ipad = PackedByteArray()
	var opad = PackedByteArray()
	ipad.resize(bsz)
	opad.resize(bsz)
	for i in bsz:
		ipad[i] = k[i] ^ 0x36
		opad[i] = k[i] ^ 0x5c
	return _bytes_to_hex(_sha256(opad + _sha256(ipad + msg)))

static func _sha256(data: PackedByteArray) -> PackedByteArray:
	var ctx = HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(data)
	return ctx.finish()

static func _bytes_to_hex(b: PackedByteArray) -> String:
	var hex = ""
	for byte in b:
		hex += "%02x" % byte
	return hex

static func hex_to_bytes(hex: String) -> PackedByteArray:
	var out = PackedByteArray()
	for i in range(0, hex.length(), 2):
		out.append(hex.substr(i, 2).hex_to_int())
	return out
