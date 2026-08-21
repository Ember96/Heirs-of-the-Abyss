extends Node2D

const DEV_TOKEN = "dev-secret-change-me"
const SERVER_URL = "ws://127.0.0.1:8000/game"

@onready var status_label: Label = $UI/StatusLabel
@onready var start_button: Button = $UI/StartButton

func _ready() -> void:
	NetworkManager.session_ready.connect(_on_session_ready)
	NetworkManager.message_received.connect(_on_message)
	NetworkManager.disconnected.connect(_on_disconnected)
	status_label.text = "Ready"

func _on_start_pressed() -> void:
	status_label.text = "Connecting..."
	start_button.disabled = true
	NetworkManager.connect_to(SERVER_URL)

func _on_session_ready(session_id: String) -> void:
	status_label.text = "Session: %s" % session_id
	start_button.text = "Resume"

func _on_message(msg: Dictionary) -> void:
	status_label.text = "Received: %s" % msg.get("type", "?")

func _on_disconnected() -> void:
	status_label.text = "Disconnected — reconnecting..."
