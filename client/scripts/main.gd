extends Node2D

const DEV_TOKEN = "dev-secret-change-me"
const SERVER_URL = "ws://127.0.0.1:8000/game"
const DEMO_SEED := 42

@onready var status_label: Label = $UI/StatusLabel
@onready var start_button: Button = $UI/StartButton
@onready var floor_node: FloorRenderer = $FloorRenderer

var _seed := DEMO_SEED
var fight_view: FightView

func _ready() -> void:
	NetworkManager.session_ready.connect(_on_session_ready)
	NetworkManager.message_received.connect(_on_message)
	NetworkManager.disconnected.connect(_on_disconnected)
	start_button.pressed.connect(_on_start_pressed)
	status_label.text = "Ready"
	floor_node.render_floor(_seed, 12, 8)

func _on_start_pressed() -> void:
	if NetworkManager.is_authenticated():
		start_button.disabled = true
		status_label.text = "Summoning…"
		NetworkManager.send_action("attack", {"room_index": 0})
		return
	_seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
	floor_node.render_floor(_seed, 12, 8)
	status_label.text = "Connecting..."
	start_button.disabled = true
	NetworkManager.connect_to(SERVER_URL, DEV_TOKEN)

func _on_session_ready(session_id: String) -> void:
	status_label.text = "Session: %s" % session_id
	start_button.text = "Fight"
	start_button.disabled = false

func _on_message(msg: Dictionary) -> void:
	var type := str(msg.get("type", ""))
	match type:
		"fight_begin":
			_start_fight(msg)
		"decision_request":
			var payload: Dictionary = msg.get("payload", {})
			NetworkManager.send_decision(str(payload.get("decision_id", "")), "fallback")
			status_label.text = "The rite falters — a lesser foe answers."
		"game_over":
			status_label.text = "YOU DIED"
		_:
			status_label.text = "Received: %s" % type

func _start_fight(msg: Dictionary) -> void:
	if fight_view != null:
		fight_view.queue_free()
	fight_view = FightView.new()
	fight_view.submit_ready.connect(_on_submit_ready)
	fight_view.finished.connect(_on_fight_finished)
	add_child(fight_view)
	fight_view.begin(msg.get("payload", {}), floor_node)
	start_button.visible = false
	status_label.text = "Fight!"

func _on_fight_finished() -> void:
	if not NetworkManager.is_authenticated():
		return
	status_label.text = "Victory — press Fight for the next room."
	start_button.text = "Fight"
	start_button.disabled = false
	start_button.visible = true

func _on_submit_ready(fid: String, payload: Dictionary) -> void:
	NetworkManager.send_json("fight_submit", fid, payload)
	status_label.text = "Verifying..."

func _on_disconnected() -> void:
	status_label.text = "Disconnected — reconnecting..."
